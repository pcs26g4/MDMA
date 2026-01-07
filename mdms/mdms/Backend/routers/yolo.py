from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import cv2
import uuid
import sys
import time

from schemas import DetectionResponse, Detection, BoundingBox, VideoDetectionResponse
from yolo_service import get_yolo_service

router = APIRouter(prefix="/api/yolo", tags=["YOLO Detection"])

# Image directories
IMAGE_ORIGINAL_DIR = Path("uploads/ai/images/original")
IMAGE_RESULTS_DIR = Path("uploads/ai/images/results")

# Video directories
VIDEO_ORIGINAL_DIR = Path("uploads/ai/videos/original")
VIDEO_RESULTS_DIR = Path("uploads/ai/videos/results")

# Create all directories
IMAGE_ORIGINAL_DIR.mkdir(parents=True, exist_ok=True)
IMAGE_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_ORIGINAL_DIR.mkdir(parents=True, exist_ok=True)
VIDEO_RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# =================================================


# ================= IMAGE DETECTION =================
@router.post("/detect-image", response_model=DetectionResponse)
async def detect_image(file: UploadFile = File(...)):

    if file.content_type not in {
        "image/jpeg", "image/jpg", "image/png", "image/bmp", "image/webp"
    }:
        raise HTTPException(status_code=400, detail="Unsupported image format")

    try:
        suffix = Path(file.filename).suffix or ".jpg"
        filename = f"{uuid.uuid4().hex}{suffix}"
        
        # Read file bytes
        file_bytes = await file.read()
        
        # Save original image
        original_path = (IMAGE_ORIGINAL_DIR / filename).resolve()
        with open(original_path, "wb") as f:
            f.write(file_bytes)

        # Get YOLO service and run detection
        yolo_service = get_yolo_service()
        detections_list, annotated_img = yolo_service.detect_from_bytes(file_bytes, save_annotated=True)

        # Convert detections to response format
        detections = []
        for det in detections_list:
            detections.append(
                Detection(
                    class_name=det["class_name"],
                    confidence=det["confidence"],
                    bbox=BoundingBox(
                        x1=det["bbox"]["x1"],
                        y1=det["bbox"]["y1"],
                        x2=det["bbox"]["x2"],
                        y2=det["bbox"]["y2"],
                    )
                )
            )

        # Save annotated image
        result_image_path = IMAGE_RESULTS_DIR / filename
        if annotated_img is not None:
            cv2.imwrite(str(result_image_path), annotated_img)

        return DetectionResponse(
            status="success",
            detections=detections,
            total_detections=len(detections),
            annotated_image_url=f"/api/yolo/annotated/{filename}",
            original_image_url=f"/api/yolo/original/{filename}",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")


# ================= VIDEO DETECTION =================
@router.post("/detect-video", response_model=VideoDetectionResponse)
async def detect_video(file: UploadFile = File(...)):

    allowed_ext = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
    suffix = Path(file.filename).suffix.lower()

    if suffix not in allowed_ext:
        raise HTTPException(status_code=400, detail="Unsupported video format")

    try:
        start = time.time()

        filename = f"{uuid.uuid4().hex}{suffix}"
        
        # Save original video
        original_path = (VIDEO_ORIGINAL_DIR / filename).resolve()
        video_bytes = await file.read()
        with open(original_path, "wb") as f:
            f.write(video_bytes)

        # Get YOLO service and run detection
        yolo_service = get_yolo_service()
        result_video_path = VIDEO_RESULTS_DIR / filename
        
        # Run video detection
        output_path, total_detections, frames_processed = yolo_service.detect_video(
            video_path=original_path,
            output_path=result_video_path
        )

        processing_time = round(time.time() - start, 2)

        return VideoDetectionResponse(
            status="success",
            total_detections=total_detections,
            frames_processed=frames_processed,
            annotated_video_url=f"/api/yolo/video/annotated/{filename}",
            original_video_url=f"/api/yolo/video/original/{filename}",
            processing_time_seconds=processing_time
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video detection failed: {str(e)}")


# ================= FILE SERVING =================
@router.get("/annotated/{filename}")
async def get_annotated_image(filename: str):
    """Get annotated image with bounding boxes"""
    path = IMAGE_RESULTS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Annotated image not found")
    return FileResponse(path)


@router.get("/original/{filename}")
async def get_original_image(filename: str):
    """Get original uploaded image"""
    path = IMAGE_ORIGINAL_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Original image not found")
    return FileResponse(path)


@router.get("/video/annotated/{filename}")
async def get_annotated_video(filename: str):
    """Get annotated video with bounding boxes"""
    path = VIDEO_RESULTS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Annotated video not found")
    return FileResponse(path, media_type="video/mp4")


@router.get("/video/original/{filename}")
async def get_original_video(filename: str):
    """Get original uploaded video"""
    path = VIDEO_ORIGINAL_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Original video not found")
    return FileResponse(path, media_type="video/mp4")


@router.get("/health")
async def health():
    try:
        yolo_service = get_yolo_service()
        return {
            "status": "healthy",
            "python_used": sys.executable,
            "model_loaded": True,
            "device": str(yolo_service.device),
            "model_classes": len(yolo_service.names)
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "python_used": sys.executable
        }
