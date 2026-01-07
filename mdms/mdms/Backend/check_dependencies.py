"""
Dependency Checker Script
Run this to check if all required dependencies are installed
"""
import sys

def check_import(module_name, package_name=None):
    """Check if a module can be imported"""
    if package_name is None:
        package_name = module_name
    try:
        __import__(module_name)
        print(f"[OK] {package_name} is installed")
        return True
    except ImportError:
        print(f"[MISSING] {package_name} is NOT installed - run: pip install {package_name}")
        return False

def main():
    print("Checking dependencies...\n")
    
    # Core FastAPI dependencies
    print("=== Core Dependencies ===")
    fastapi_ok = check_import("fastapi", "fastapi")
    uvicorn_ok = check_import("uvicorn", "uvicorn")
    pydantic_ok = check_import("pydantic", "pydantic")
    
    # Image processing
    print("\n=== Image Processing ===")
    pillow_ok = check_import("PIL", "Pillow")
    cv2_ok = check_import("cv2", "opencv-python")
    numpy_ok = check_import("numpy", "numpy")
    
    # Deep Learning
    print("\n=== Deep Learning ===")
    torch_ok = check_import("torch", "torch")
    torchvision_ok = check_import("torchvision", "torchvision")
    
    # YOLOv5 specific
    print("\n=== YOLOv5 Dependencies ===")
    ultralytics_ok = check_import("ultralytics", "ultralytics")
    
    # Check YOLOv5 path
    print("\n=== YOLOv5 Path Check ===")
    from pathlib import Path
    yolo_root = Path(__file__).parent.parent.parent / "yolov_5" / "yolov5"
    if yolo_root.exists():
        print(f"[OK] YOLOv5 directory found at: {yolo_root}")
        
        # Check for weights
        weights_path = yolo_root / "weights" / "last.pt"
        if weights_path.exists():
            print(f"[OK] Model weights found at: {weights_path}")
        else:
            default_weights = yolo_root / "yolov5s.pt"
            if default_weights.exists():
                print(f"[OK] Default model weights found at: {default_weights}")
            else:
                print(f"[WARNING] No model weights found. You may need to download them.")
    else:
        print(f"[MISSING] YOLOv5 directory NOT found at: {yolo_root}")
    
    # Summary
    print("\n=== Summary ===")
    all_core = fastapi_ok and uvicorn_ok and pydantic_ok
    all_image = pillow_ok and cv2_ok and numpy_ok
    all_dl = torch_ok and torchvision_ok
    
    if all_core and all_image and all_dl and ultralytics_ok:
        print("[SUCCESS] All dependencies are installed!")
        print("\nYou can start the server with:")
        print("  uvicorn main:app --reload")
    else:
        print("[WARNING] Some dependencies are missing.")
        print("\nInstall missing dependencies with:")
        print("  pip install -r requirements.txt")
        if not torch_ok:
            print("\nFor PyTorch, you may need to install separately:")
            print("  pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu")

if __name__ == "__main__":
    main()

