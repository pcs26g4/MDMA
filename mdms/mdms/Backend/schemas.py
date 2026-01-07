from pydantic import BaseModel
from typing import List, Optional

class ComplaintCreate(BaseModel):
    title: str                # ✅ REQUIRED
    category: str
    latitude: float | None = None
    longitude: float | None = None
    address: str | None = None


class ComplaintResponse(BaseModel):
    ticket_id: str
    category: str
    image_url: str


# YOLOv5 Detection Schemas
class BoundingBox(BaseModel):
    x1: float  # x coordinate of top-left corner
    y1: float  # y coordinate of top-left corner
    x2: float  # x coordinate of bottom-right corner
    y2: float  # y coordinate of bottom-right corner


class Detection(BaseModel):
    class_name: str
    confidence: float
    bbox: BoundingBox


class DetectionResponse(BaseModel):
    status: str
    detections: List[Detection]
    total_detections: int
    annotated_image_url: str
    original_image_url: Optional[str] = None


class VideoDetectionResponse(BaseModel):
    status: str
    total_detections: int
    frames_processed: int
    annotated_video_url: str
    original_video_url: Optional[str] = None
    processing_time_seconds: Optional[float] = None
