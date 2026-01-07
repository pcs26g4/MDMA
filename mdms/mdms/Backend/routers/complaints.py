from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from database import get_db
from app_utils.exif import extract_gps_from_image_bytes
from app_utils.geo import group_by_location
from app_utils.deduplication import check_duplicate_image
from yolo_service import get_yolo_service
from app_models import Ticket, SubTicket, ComplaintImage

from crud import (
    get_or_create_ticket,
    get_or_create_sub_ticket,
    save_image
)

router = APIRouter(prefix="/api/complaints", tags=["Complaints"])

# ---------------- Authority Mapping ----------------
AUTHORITY_MAP = {
    "pathholes": "Roads Department",
    "pothole": "Roads Department",  # alias for compatibility
    "garbage": "Sanitation Department",
    "streetdebris": "Municipal Corporation",
    "street_debris": "Municipal Corporation",  # alias for compatibility
}

DEFAULT_LAT = 0.0
DEFAULT_LON = 0.0


# ==================================================
# SINGLE IMAGE COMPLAINT UPLOAD (REFERENCE-STYLE)
# ==================================================
@router.post("/")
async def upload_complaint_image(
    issue_type: str = Form(..., description="Issue type, e.g., pathholes, garbage, street_debris"),
    latitude: Optional[float] = Form(None, description="Optional manual latitude"),
    longitude: Optional[float] = Form(None, description="Optional manual longitude"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a single complaint image.
    - Detects GPS from EXIF if available.
    - Falls back to manual latitude/longitude if provided.
    - Creates/gets a Ticket (by location) and SubTicket (by issue type).
    - Saves the image and returns ticket + sub_ticket info.
    - Uses existing deduplication rules (same image + same location => duplicate).
    """
    # Validate file type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    # Normalize issue type to match AUTHORITY_MAP keys
    normalized_issue = issue_type.strip().lower().replace(" ", "").replace("-", "").replace("_", "")
    # Map common variants to our keys
    if normalized_issue in {"pothole"}:
        normalized_issue = "pathholes"
    if normalized_issue in {"streetdebris", "streetdebris"}:
        normalized_issue = "streetdebris"

    # Find matching key in AUTHORITY_MAP (since some keys have underscores)
    if normalized_issue not in AUTHORITY_MAP:
        raise HTTPException(status_code=400, detail=f"Invalid issue type: {issue_type}")

    authority = AUTHORITY_MAP[normalized_issue]

    # Read image bytes
    image_bytes = await file.read()

    # 🔍 Try EXIF GPS first
    gps_data = extract_gps_from_image_bytes(image_bytes)

    # ✅ FINAL LOCATION LOGIC
    if gps_data:
        lat = gps_data["latitude"]
        lon = gps_data["longitude"]
        gps_extracted = True
        gps_source = "exif"
    elif latitude is not None and longitude is not None:
        lat = latitude
        lon = longitude
        gps_extracted = True
        gps_source = "manual"
    else:
        # Fallback to default location (0,0) when nothing available
        lat = DEFAULT_LAT
        lon = DEFAULT_LON
        gps_extracted = False
        gps_source = "unknown"

    # Duplicate check (even without reliable GPS we check similarity)
    check_lat = lat if gps_extracted and lat != DEFAULT_LAT else None
    check_lon = lon if gps_extracted and lon != DEFAULT_LON else None

    is_duplicate, reason, existing_info = check_duplicate_image(
        db=db,
        image_bytes=image_bytes,
        latitude=check_lat,
        longitude=check_lon,
        distance_threshold=50,  # 50 meters for location-aware matching
    )

    if is_duplicate:
        # Don't save duplicate image, just return friendly message
        return {
            "status": "duplicate",
            "message": reason or "This complaint is already registered. Thanks for your concern.",
            "existing_complaint": existing_info,
        }

    # 1️⃣ MAIN TICKET (LOCATION BASED)
    ticket = get_or_create_ticket(db, lat, lon)

    # 2️⃣ SUB TICKET (ISSUE BASED)
    sub_ticket = get_or_create_sub_ticket(
        db,
        ticket.ticket_id,
        normalized_issue,
        authority,
    )

    # 3️⃣ SAVE IMAGE
    image = save_image(
        db=db,
        sub_id=sub_ticket.sub_id,
        image_bytes=image_bytes,
        content_type=file.content_type,
        gps_extracted=gps_extracted,
        media_type="image",
        file_name=file.filename,
        latitude=lat if gps_extracted else None,
        longitude=lon if gps_extracted else None,
    )

    return {
        "status": "success",
        "ticket_id": ticket.ticket_id,
        "sub_id": sub_ticket.sub_id,
        "issue_type": normalized_issue,
        "authority": authority,
        "gps": {
            "latitude": lat if gps_extracted else None,
            "longitude": lon if gps_extracted else None,
            "source": gps_source,
        },
        "image_id": image.id,
    }


# ==================================================
# BATCH COMPLAINT UPLOAD (IMAGES + VIDEOS)
# ==================================================
@router.post("/batch")
async def upload_batch_complaints(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    if not files:
        raise HTTPException(400, "No files uploaded")

    yolo_service = get_yolo_service()
    processed_items = []

    # ---------------- PROCESS EACH FILE ----------------
    for file in files:
        content_type = file.content_type
        file_bytes = await file.read()

        lat, lon = DEFAULT_LAT, DEFAULT_LON
        gps_extracted = False

        # ---------- IMAGE GPS ----------
        if content_type.startswith("image/"):
            gps_data = extract_gps_from_image_bytes(file_bytes)
            if gps_data:
                lat = gps_data["latitude"]
                lon = gps_data["longitude"]
                gps_extracted = True

        # ---------- YOLO DETECTION ----------
        detections = []
        if content_type.startswith("image/"):
            try:
                detections, _ = yolo_service.detect_from_bytes(file_bytes)
            except Exception as e:
                # If YOLO detection fails, mark as no detection and skip saving
                print(f"YOLO detection failed for {file.filename}: {e}")
                detections = []

        # Find the primary issue type for this image
        # Priority: Find the issue type with highest confidence detection
        issue_type = None
        max_confidence = 0.0
        
        # Check all detections and find the best matching issue type
        for det in detections:
            class_name = det["class_name"].lower().replace("_", "").replace(" ", "")
            if class_name in AUTHORITY_MAP:
                confidence = det["confidence"]
                if confidence > max_confidence:
                    max_confidence = confidence
                    issue_type = class_name
        
        # If no detection found, skip saving this file and mark rejected
        if content_type.startswith("image/") and not issue_type:
            processed_items.append({
                "file_bytes": file_bytes,
                "content_type": content_type,
                "file_name": file.filename,
                "media_type": "image",
                "latitude": lat,
                "longitude": lon,
                "issue_type": None,
                "gps_extracted": gps_extracted,
                "detection_confidence": None,
                "no_detection": True,
            })
            continue

        # ---------- STORE TEMP RECORD ----------
        # Each image/file goes to ONE issue type (primary detected issue)
        processed_items.append({
            "file_bytes": file_bytes,
            "content_type": content_type,
            "file_name": file.filename,
            "media_type": "video" if content_type.startswith("video/") else "image",
            "latitude": lat,
            "longitude": lon,
            "issue_type": issue_type,
            "gps_extracted": gps_extracted,
            "detection_confidence": max_confidence if max_confidence > 0 else None,
            "no_detection": False,
        })

    if not processed_items:
        raise HTTPException(400, "No valid complaints detected")

    # ---------------- GROUP BY LOCATION ----------------
    location_groups = group_by_location(
        processed_items,
        distance_threshold=20  # meters
    )

    results = []

    # ---------------- PROCESS EACH LOCATION GROUP ----------------
    for group in location_groups:
        rep = group[0]

        # 1️⃣ MAIN TICKET (LOCATION)
        ticket = get_or_create_ticket(
            db,
            rep["latitude"],
            rep["longitude"]
        )

        ticket_result = {
            "ticket_id": ticket.ticket_id,
            "latitude": ticket.latitude,
            "longitude": ticket.longitude,
            "sub_tickets": []
        }

        # ---------------- GROUP BY ISSUE TYPE ----------------
        # Group items by issue type within this location
        # This ensures:
        # - Multiple images of same issue type → same sub_ticket
        # - Different issue types → different sub_tickets (different authorities)
        issue_groups = {}
        for item in group:
            issue_groups.setdefault(item["issue_type"], []).append(item)

        # Create one sub_ticket per issue type (one per authority)
        for issue_type, items in issue_groups.items():
            authority = AUTHORITY_MAP[issue_type]

            # 2️⃣ SUB TICKET
            sub_ticket = get_or_create_sub_ticket(
                db,
                ticket.ticket_id,
                issue_type,
                authority
            )

            # 3️⃣ SAVE MEDIA (with deduplication check)
            saved_count = 0
            rejected_count = 0
            rejected_items = []
            
            for item in items:
                # Skip items with no detection
                if item.get("no_detection"):
                    rejected_count += 1
                    rejected_items.append({
                        "file_name": item["file_name"],
                        "message": "No detection found in the image.",
                        "latitude": item.get("latitude"),
                        "longitude": item.get("longitude"),
                        "gps_extracted": item.get("gps_extracted"),
                    })
                    continue

                # Check duplicates for all images; use GPS when available
                is_image = item["media_type"] == "image" and item["content_type"].startswith("image/")
                has_gps = item["gps_extracted"] and item["latitude"] != DEFAULT_LAT and item["longitude"] != DEFAULT_LON
                
                if is_image:
                    check_lat = item["latitude"] if has_gps else None
                    check_lon = item["longitude"] if has_gps else None

                    # Check for duplicate image (similarity + optional location)
                    is_duplicate, reason, existing_info = check_duplicate_image(
                        db=db,
                        image_bytes=item["file_bytes"],
                        latitude=check_lat,
                        longitude=check_lon,
                        distance_threshold=50  # 50 meters as per requirements
                    )
                    
                    if is_duplicate:
                        # Reject duplicate image with user-friendly message
                        rejected_count += 1
                        rejected_items.append({
                            "file_name": item["file_name"],
                            "message": reason or "This complaint is already registered. Thanks for your concern.",
                            "latitude": item["latitude"] if has_gps else None,
                            "longitude": item["longitude"] if has_gps else None,
                            "gps_extracted": item["gps_extracted"],
                            "existing_complaint": existing_info.get("ticket_info") if existing_info else None,
                            "details": {
                                "distance_meters": existing_info.get("distance_meters") if existing_info else None,
                                "existing_image_id": existing_info.get("id") if existing_info else None,
                                "ticket_id": existing_info.get("ticket_info", {}).get("ticket_id") if existing_info else None
                            }
                        })
                        continue  # Skip saving this image
                
                # Save the image (not a duplicate or no GPS to check)
                save_image(
                    db=db,
                    sub_id=sub_ticket.sub_id,
                    image_bytes=item["file_bytes"],
                    content_type=item["content_type"],
                    gps_extracted=item["gps_extracted"],
                    media_type=item["media_type"],
                    file_name=item["file_name"],
                    latitude=item["latitude"] if has_gps else None,
                    longitude=item["longitude"] if has_gps else None
                )
                saved_count += 1
            
            # Get GPS coordinates from the first item in this issue group
            # (all items in same location group have similar GPS)
            first_item = items[0] if items else None
            sub_latitude = first_item["latitude"] if first_item and first_item.get("latitude") != DEFAULT_LAT else None
            sub_longitude = first_item["longitude"] if first_item and first_item.get("longitude") != DEFAULT_LON else None
            
            # Update media count to reflect actually saved items
            ticket_result["sub_tickets"].append({
                "sub_id": sub_ticket.sub_id,
                "issue_type": issue_type,
                "authority": authority,
                "latitude": sub_latitude,
                "longitude": sub_longitude,
                "media_count": saved_count,
                "rejected_count": rejected_count,
                "rejected_items": rejected_items if rejected_items else None
            })


        results.append(ticket_result)

    # Calculate total rejected count for summary
    total_rejected = sum(
        sub_ticket.get("rejected_count", 0)
        for result in results
        for sub_ticket in result.get("sub_tickets", [])
    )
    
    response = {
        "status": "success",
        "tickets_created": results
    }
    
    # Add summary message if duplicates were detected
    if total_rejected > 0:
        response["message"] = f"{total_rejected} image(s) were not uploaded because the complaints are already registered. Thanks for your concern!"
        response["duplicates_found"] = total_rejected
        response["warning"] = "Some images were rejected as duplicates"
    
    return response


# ==================================================
# GET ALL TICKETS
# ==================================================
@router.get("/tickets")
async def get_tickets(
    status: Optional[str] = Query(None, description="Filter by status"),
    issue_type: Optional[str] = Query(None, description="Filter by issue type"),
    db: Session = Depends(get_db)
):
    """
    Get all tickets with optional filtering
    """
    query = db.query(Ticket)
    
    if status:
        query = query.filter(Ticket.status == status)
    
    tickets = query.all()
    
    results = []
    for ticket in tickets:
        # Get sub-tickets for this ticket
        sub_tickets = db.query(SubTicket).filter(
            SubTicket.ticket_id == ticket.ticket_id
        ).all()
        
        # Filter by issue_type if provided
        if issue_type:
            sub_tickets = [st for st in sub_tickets if st.issue_type == issue_type]
        
        if issue_type and not sub_tickets:
            continue  # Skip ticket if no matching sub-tickets
        
        # Get images for each sub-ticket
        ticket_data = {
            "ticket_id": ticket.ticket_id,
            "latitude": ticket.latitude,
            "longitude": ticket.longitude,
            "status": ticket.status,
            "address": ticket.address,
            "sub_tickets": []
        }
        
        for sub_ticket in sub_tickets:
            # Get first image for preview
            first_image = db.query(ComplaintImage).filter(
                ComplaintImage.sub_id == sub_ticket.sub_id,
                ComplaintImage.media_type == "image"
            ).first()
            
            # Get earliest image timestamp for this sub_ticket
            earliest_image = db.query(ComplaintImage).filter(
                ComplaintImage.sub_id == sub_ticket.sub_id
            ).order_by(ComplaintImage.created_at.asc()).first()
            
            # Get GPS coordinates from first image with GPS in this sub_ticket
            gps_image = db.query(ComplaintImage).filter(
                ComplaintImage.sub_id == sub_ticket.sub_id,
                ComplaintImage.latitude.isnot(None),
                ComplaintImage.longitude.isnot(None)
            ).first()
            
            sub_ticket_data = {
                "sub_id": sub_ticket.sub_id,
                "issue_type": sub_ticket.issue_type,
                "authority": sub_ticket.authority,
                "status": sub_ticket.status,
                "latitude": gps_image.latitude if gps_image else None,
                "longitude": gps_image.longitude if gps_image else None,
                "image_count": db.query(ComplaintImage).filter(
                    ComplaintImage.sub_id == sub_ticket.sub_id
                ).count(),
                "has_image": first_image is not None,
                "image_id": first_image.id if first_image else None,
                "created_at": earliest_image.created_at.isoformat() if earliest_image and earliest_image.created_at else None
            }
            
            ticket_data["sub_tickets"].append(sub_ticket_data)
        
        if ticket_data["sub_tickets"]:  # Only add if has sub_tickets
            results.append(ticket_data)
    
    return {
        "status": "success",
        "count": len(results),
        "tickets": results
    }


# ==================================================
# GET TICKET BY ID
# ==================================================
@router.get("/tickets/{ticket_id}")
async def get_ticket_by_id(
    ticket_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific ticket by ID
    """
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    sub_tickets = db.query(SubTicket).filter(
        SubTicket.ticket_id == ticket_id
    ).all()
    
    sub_tickets_data = []
    for sub_ticket in sub_tickets:
        images = db.query(ComplaintImage).filter(
            ComplaintImage.sub_id == sub_ticket.sub_id
        ).all()
        
        # Get GPS coordinates from first image with GPS in this sub_ticket
        gps_image = db.query(ComplaintImage).filter(
            ComplaintImage.sub_id == sub_ticket.sub_id,
            ComplaintImage.latitude.isnot(None),
            ComplaintImage.longitude.isnot(None)
        ).first()
        
        sub_tickets_data.append({
            "sub_id": sub_ticket.sub_id,
            "issue_type": sub_ticket.issue_type,
            "authority": sub_ticket.authority,
            "status": sub_ticket.status,
            "latitude": gps_image.latitude if gps_image else None,
            "longitude": gps_image.longitude if gps_image else None,
            "images": [
                {
                    "id": img.id,
                    "file_name": img.file_name,
                    "content_type": img.content_type,
                    "media_type": img.media_type,
                    "gps_extracted": img.gps_extracted,
                    "latitude": img.latitude,
                    "longitude": img.longitude
                }
                for img in images
            ]
        })
    
    return {
        "status": "success",
        "ticket": {
            "ticket_id": ticket.ticket_id,
            "latitude": ticket.latitude,
            "longitude": ticket.longitude,
            "status": ticket.status,
            "address": ticket.address,
            "sub_tickets": sub_tickets_data
        }
    }


# ==================================================
# GET IMAGE BY ID
# ==================================================
@router.get("/images/{image_id}")
async def get_image(
    image_id: int,
    db: Session = Depends(get_db)
):
    """
    Get image data by ID
    """
    from fastapi.responses import Response
    
    image = db.query(ComplaintImage).filter(ComplaintImage.id == image_id).first()
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    return Response(
        content=image.image_data,
        media_type=image.content_type,
        headers={
            "Content-Disposition": f'inline; filename="{image.file_name or "image"}"'
        }
    )