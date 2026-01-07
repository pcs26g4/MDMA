"""
YOLOv5 Detection Service
Handles model loading and inference for object detection
"""
import sys
from pathlib import Path
from typing import List, Tuple, Optional

# Add YOLOv5 to path
YOLO_ROOT = Path(__file__).parent.parent.parent / "yolov_5" / "yolov5"
YOLO_ROOT = YOLO_ROOT.resolve()

# Lazy imports - only import when actually needed
def _import_dependencies():
    """Import all required dependencies"""
    try:
        import torch
        import cv2
        import numpy as np
        
        # Use importlib to import from YOLOv5 directory, avoiding conflicts with local models.py
        import importlib
        import importlib.util
        
        # Add YOLOv5 root to path if not already there (must be first to take precedence)
        yolo_path = str(YOLO_ROOT)
        if yolo_path not in sys.path:
            sys.path.insert(0, yolo_path)
        
        # Temporarily remove Backend directory from path to avoid local models.py conflict
        backend_path = str(Path(__file__).parent)
        backend_in_path = backend_path in sys.path
        if backend_in_path:
            sys.path.remove(backend_path)
        
        # Aggressively clear cached modules that conflict with YOLOv5
        # This prevents importing from Backend/utils or Backend/models
        modules_to_remove = []
        for mod_name in list(sys.modules.keys()):
            # Remove any modules from Backend that conflict
            if mod_name in ['models', 'utils'] or mod_name.startswith(('models.', 'utils.')):
                mod = sys.modules.get(mod_name)
                if mod:
                    # Check if it's from Backend directory
                    if hasattr(mod, '__file__') and mod.__file__:
                        if backend_path in str(mod.__file__):
                            modules_to_remove.append(mod_name)
                    # Also check if it's a namespace package pointing to wrong location
                    elif backend_in_path and mod_name in ['models', 'utils']:
                        # Check if any submodule is from backend
                        has_backend_submod = any(
                            backend_path in str(getattr(sys.modules.get(k), '__file__', ''))
                            for k in sys.modules.keys()
                            if k.startswith(f'{mod_name}.')
                        )
                        if has_backend_submod:
                            modules_to_remove.append(mod_name)
        
        # Remove in reverse order (submodules first)
        for mod_name in sorted(modules_to_remove, reverse=True):
            if mod_name in sys.modules:
                del sys.modules[mod_name]
        
        try:
            # Clear utils module if it exists and is from wrong location
            # This ensures we import from YOLOv5/utils, not Backend/utils
            if 'utils' in sys.modules:
                utils_mod = sys.modules['utils']
                if hasattr(utils_mod, '__file__') and utils_mod.__file__:
                    if backend_path in str(utils_mod.__file__):
                        # Remove utils and all its submodules
                        utils_keys = [k for k in list(sys.modules.keys()) if k == 'utils' or k.startswith('utils.')]
                        for k in utils_keys:
                            if k in sys.modules:
                                del sys.modules[k]
            
            # Now do regular imports - they should find YOLOv5's modules
            # YOLOv5 path is first, Backend is removed, so imports will work correctly
            from models.common import DetectMultiBackend
            from utils.general import (
                check_img_size,
                non_max_suppression,
                scale_boxes,
                LOGGER,
            )
            from utils.augmentations import letterbox
            from utils.torch_utils import select_device
            from utils.dataloaders import LoadImages
        finally:
            # Restore Backend path if it was there
            if backend_in_path:
                sys.path.insert(0, backend_path)
        return {
            'torch': torch,
            'cv2': cv2,
            'np': np,
            'DetectMultiBackend': DetectMultiBackend,
            'check_img_size': check_img_size,
            'non_max_suppression': non_max_suppression,
            'scale_boxes': scale_boxes,
            'LOGGER': LOGGER,
            'letterbox': letterbox,
            'select_device': select_device,
            'LoadImages': LoadImages,
        }
    except ImportError as e:
        raise ImportError(
            f"Failed to import YOLOv5 dependencies. "
            f"Please install: pip install torch torchvision opencv-python numpy ultralytics. "
            f"Error: {e}"
        )


class YOLOv5Service:
    """Service for YOLOv5 object detection"""
    
    def __init__(
        self,
        weights_path: Optional[str] = None,
        device: str = "",
        img_size: int = 640,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
    ):
        """
        Initialize YOLOv5 service
        
        Args:
            weights_path: Path to model weights file (.pt)
            device: Device to run inference on ('cpu', 'cuda', '0', etc.)
            img_size: Input image size for inference
            conf_threshold: Confidence threshold for detections
            iou_threshold: IoU threshold for NMS
        """
        # Import dependencies
        deps = _import_dependencies()
        self.torch = deps['torch']
        self.cv2 = deps['cv2']
        self.np = deps['np']
        self.DetectMultiBackend = deps['DetectMultiBackend']
        self.check_img_size = deps['check_img_size']
        self.non_max_suppression = deps['non_max_suppression']
        self.scale_boxes = deps['scale_boxes']
        self.LOGGER = deps['LOGGER']
        self.letterbox = deps['letterbox']
        self.select_device = deps['select_device']
        self.LoadImages = deps['LoadImages']
        
        self.device = self.select_device(device)
        self.img_size = img_size
        self.conf_threshold = conf_threshold
        self.iou_threshold = iou_threshold
        
        # Default weights path
        if weights_path is None:
            weights_path = YOLO_ROOT / "weights" / "last.pt"
            if not weights_path.exists():
                # Try .onnx if .pt is not found
                weights_path = YOLO_ROOT / "weights" / "last.onnx"
            if not weights_path.exists():
                # Try default yolov5s.pt in root as a last resort
                weights_path = YOLO_ROOT / "yolov5s.pt"
        
        weights_path = Path(weights_path)
        if not weights_path.exists():
            raise FileNotFoundError(f"Model weights not found at {weights_path}")
        
        # Load model
        self.model = self.DetectMultiBackend(
            str(weights_path),
            device=self.device,
            dnn=False,
            data=None,
            fp16=False
        )
        
        # Get model info
        self.stride = self.model.stride
        self.names = self.model.names
        self.pt = self.model.pt
        
        # Check image size
        self.img_size = self.check_img_size(self.img_size, s=self.stride)
        
        # Warmup model
        imgsz = (1, 3, self.img_size, self.img_size) if isinstance(self.img_size, int) else (1, 3, *self.img_size)
        self.model.warmup(imgsz=imgsz)
        
        self.LOGGER.info(f"YOLOv5 model loaded from {weights_path}")
        self.LOGGER.info(f"Using device: {self.device}")
        self.LOGGER.info(f"Model classes: {len(self.names)}")
    
    def detect(
        self,
        image_path: str | Path,
        save_annotated: bool = True,
        output_dir: Optional[str | Path] = None,
    ) -> Tuple[List[dict], any]:
        """
        Run detection on an image
        
        Args:
            image_path: Path to input image
            save_annotated: Whether to save annotated image
            output_dir: Directory to save annotated image
            
        Returns:
            Tuple of (detections list, annotated image array)
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        # Load image
        dataset = self.LoadImages(
            str(image_path),
            img_size=self.img_size,
            stride=self.stride,
            auto=self.pt
        )
        
        detections = []
        annotated_img = None
        
        for path, im, im0s, vid_cap, s in dataset:
            # Preprocess
            im = self.torch.from_numpy(im).to(self.device)
            im = im.half() if self.model.fp16 else im.float()
            im /= 255.0
            if len(im.shape) == 3:
                im = im[None]  # Add batch dimension
            
            # Inference
            pred = self.model(im, augment=False, visualize=False)
            
            # NMS
            pred = self.non_max_suppression(
                pred,
                self.conf_threshold,
                self.iou_threshold,
                classes=None,
                agnostic=False,
                max_det=1000
            )
            
            # Process predictions
            im0 = im0s.copy()
            gn = self.torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
            
            for i, det in enumerate(pred):
                if len(det):
                    # Rescale boxes from img_size to im0 size
                    det[:, :4] = self.scale_boxes(im.shape[2:], det[:, :4], im0.shape).round()
                    
                    # Extract detections
                    for *xyxy, conf, cls in reversed(det):
                        x1, y1, x2, y2 = [float(x.item()) for x in xyxy]
                        confidence = float(conf.item())
                        class_id = int(cls.item())
                        class_name = self.names[class_id]
                        
                        detections.append({
                            "class_name": class_name,
                            "confidence": confidence,
                            "bbox": {
                                "x1": x1,
                                "y1": y1,
                                "x2": x2,
                                "y2": y2,
                            }
                        })
                        
                        # Draw bounding box on image
                        if save_annotated:
                            label = f"{class_name} {confidence:.2f}"
                            self.cv2.rectangle(im0, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                            self.cv2.putText(
                                im0,
                                label,
                                (int(x1), int(y1) - 10),
                                self.cv2.FONT_HERSHEY_SIMPLEX,
                                0.5,
                                (0, 255, 0),
                                2
                            )
            
            annotated_img = im0
        
        return detections, annotated_img
    
    def detect_from_bytes(
        self,
        image_bytes: bytes,
        save_annotated: bool = True,
    ) -> Tuple[List[dict], any]:
        """
        Run detection on image bytes
        
        Args:
            image_bytes: Image file bytes
            save_annotated: Whether to return annotated image
            
        Returns:
            Tuple of (detections list, annotated image array)
        """
        # Convert bytes to numpy array
        nparr = self.np.frombuffer(image_bytes, self.np.uint8)
        im0 = self.cv2.imdecode(nparr, self.cv2.IMREAD_COLOR)
        
        if im0 is None:
            raise ValueError("Failed to decode image from bytes")
        
        # Use YOLOv5 preprocessing (same as LoadImages)
        # Letterbox resize (maintain aspect ratio)
        im = self.letterbox(im0, self.img_size, stride=self.stride, auto=self.pt)[0]  # padded resize
        im = im.transpose((2, 0, 1))[::-1]  # HWC to CHW, BGR to RGB
        im = self.np.ascontiguousarray(im)  # contiguous
        
        # Convert to tensor
        im = self.torch.from_numpy(im).to(self.device)
        im = im.half() if self.model.fp16 else im.float()  # uint8 to fp16/32
        im /= 255.0  # 0 - 255 to 0.0 - 1.0
        if len(im.shape) == 3:
            im = im[None]  # expand for batch dim
        
        # Inference
        pred = self.model(im, augment=False, visualize=False)
        
        # NMS
        pred = self.non_max_suppression(
            pred,
            self.conf_threshold,
            self.iou_threshold,
            classes=None,
            agnostic=False,
            max_det=1000
        )
        
        # Process predictions
        detections = []
        annotated_img = im0.copy()
        
        # Debug: Check if we have any predictions
        self.LOGGER.info(f"Number of prediction batches: {len(pred)}")
        total_detections = 0
        for i, det in enumerate(pred):
            det_count = len(det) if det is not None and len(det) > 0 else 0
            total_detections += det_count
            self.LOGGER.info(f"Batch {i}: {det_count} detections after NMS")
            if det is not None and len(det) > 0:
                # Rescale boxes from img_size to im0 size
                det[:, :4] = self.scale_boxes(im.shape[2:], det[:, :4], im0.shape).round()
                
                # Extract detections
                for *xyxy, conf, cls in reversed(det):
                    x1, y1, x2, y2 = [float(x.item()) for x in xyxy]
                    confidence = float(conf.item())
                    class_id = int(cls.item())
                    class_name = self.names[class_id]
                    
                    detections.append({
                        "class_name": class_name,
                        "confidence": confidence,
                        "bbox": {
                            "x1": x1,
                            "y1": y1,
                            "x2": x2,
                            "y2": y2,
                        }
                    })
                    
                    # Draw bounding box on image
                    if save_annotated:
                        label = f"{class_name} {confidence:.2f}"
                        self.cv2.rectangle(annotated_img, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                        self.cv2.putText(
                            annotated_img,
                            label,
                            (int(x1), int(y1) - 10),
                            self.cv2.FONT_HERSHEY_SIMPLEX,
                            0.5,
                            (0, 255, 0),
                            2
                        )
        
        self.LOGGER.info(f"Total detections found: {len(detections)}")
        if len(detections) == 0:
            self.LOGGER.warning(f"No detections found. Confidence threshold: {self.conf_threshold}, Image shape: {im0.shape}")
        
        return detections, annotated_img
    
    def detect_video(
        self,
        video_path: str | Path,
        output_path: Optional[str | Path] = None,
        conf_threshold: Optional[float] = None,
    ) -> Tuple[str, int, int]:
        """
        Run detection on a video file
        
        Args:
            video_path: Path to input video file
            output_path: Path to save annotated video (optional)
            conf_threshold: Confidence threshold (uses instance default if None)
            
        Returns:
            Tuple of (output_video_path, total_detections, frames_processed)
        """
        import time
        start_time = time.time()
        
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")
        
        # Use instance threshold or provided one
        conf_thresh = conf_threshold if conf_threshold is not None else self.conf_threshold
        
        # Set output path
        if output_path is None:
            output_path = video_path.parent / f"annotated_{video_path.name}"
        else:
            output_path = Path(output_path)
        
        # Load video
        cap = self.cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise ValueError(f"Failed to open video: {video_path}")
        
        # Get video properties
        fps = int(cap.get(self.cv2.CAP_PROP_FPS))
        width = int(cap.get(self.cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(self.cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(self.cv2.CAP_PROP_FRAME_COUNT))
        
        self.LOGGER.info(f"Processing video: {width}x{height}, {fps} FPS, {total_frames} frames")
        
        # Create video writer
        fourcc = self.cv2.VideoWriter_fourcc(*'mp4v')
        out = self.cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))
        
        frames_processed = 0
        total_detections = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Preprocess frame
                im = self.letterbox(frame, self.img_size, stride=self.stride, auto=self.pt)[0]
                im = im.transpose((2, 0, 1))[::-1]  # HWC to CHW, BGR to RGB
                im = self.np.ascontiguousarray(im)
                
                # Convert to tensor
                im_tensor = self.torch.from_numpy(im).to(self.device)
                im_tensor = im_tensor.half() if self.model.fp16 else im_tensor.float()
                im_tensor /= 255.0
                if len(im_tensor.shape) == 3:
                    im_tensor = im_tensor[None]
                
                # Inference
                pred = self.model(im_tensor, augment=False, visualize=False)
                
                # NMS
                pred = self.non_max_suppression(
                    pred,
                    conf_thresh,
                    self.iou_threshold,
                    classes=None,
                    agnostic=False,
                    max_det=1000
                )
                
                # Process detections
                frame_detections = 0
                for det in pred:
                    if det is not None and len(det) > 0:
                        # Rescale boxes
                        det[:, :4] = self.scale_boxes(im_tensor.shape[2:], det[:, :4], frame.shape).round()
                        
                        # Draw bounding boxes
                        for *xyxy, conf, cls in reversed(det):
                            x1, y1, x2, y2 = [int(x.item()) for x in xyxy]
                            confidence = float(conf.item())
                            class_id = int(cls.item())
                            class_name = self.names[class_id]
                            
                            # Draw box
                            label = f"{class_name} {confidence:.2f}"
                            self.cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            self.cv2.putText(
                                frame,
                                label,
                                (x1, y1 - 10),
                                self.cv2.FONT_HERSHEY_SIMPLEX,
                                0.5,
                                (0, 255, 0),
                                2
                            )
                            frame_detections += 1
                
                total_detections += frame_detections
                frames_processed += 1
                
                # Write frame
                out.write(frame)
                
                # Progress logging every 30 frames
                if frames_processed % 30 == 0:
                    progress = (frames_processed / total_frames) * 100 if total_frames > 0 else 0
                    self.LOGGER.info(f"Processed {frames_processed}/{total_frames} frames ({progress:.1f}%), {frame_detections} detections in this frame")
        
        finally:
            cap.release()
            out.release()
        
        processing_time = time.time() - start_time
        self.LOGGER.info(f"Video processing complete: {frames_processed} frames, {total_detections} total detections, {processing_time:.2f}s")
        
        return str(output_path), total_detections, frames_processed


# Global service instance (lazy loading)
_yolo_service: Optional[YOLOv5Service] = None


def get_yolo_service() -> YOLOv5Service:
    """Get or create YOLOv5 service instance"""
    global _yolo_service
    if _yolo_service is None:
        _yolo_service = YOLOv5Service()
    return _yolo_service

