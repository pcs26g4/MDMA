from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.complaints import router as complaints_router
from routers.yolo import router as yolo_router
from database import engine, Base
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="MDMS API",
    description="Municipal Data Management System with YOLOv5 Object Detection",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    """Create database tables on startup"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        logger.warning("Application will continue, but database operations may fail")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(complaints_router)
app.include_router(yolo_router)

@app.get("/")
async def root():
    return {
        "message": "MDMS API",
        "endpoints": {
            "complaints": "/api/complaints",
            "yolo_image_detection": "/api/yolo/detect-image",
            "yolo_video_detection": "/api/yolo/detect-video",
            "yolo_health": "/api/yolo/health"
        }
    }
