"""
Image Deduplication Service
Checks for duplicate or similar images within a geospatial radius.
Implements the business logic:
- Same image + same location (≤50m) → Reject
- Different image + same location (≤50m) → Accept
- Any image + different location (>50m) → Accept
"""
from sqlalchemy.orm import Session
from typing import Optional, Tuple
from app_models import ComplaintImage, SubTicket, Ticket
from app_utils.geo import calculate_distance
from app_utils.image_hash import calculate_image_hash, compare_image_hashes


# Default thresholds
DEFAULT_DISTANCE_THRESHOLD = 50  # meters
# Hamming distance for perceptual hash
# Lower = stricter (more likely to treat as different)
# Higher = more lenient (more likely to treat as duplicates)
DEFAULT_HASH_THRESHOLD = 5


def check_duplicate_image(
    db: Session,
    image_bytes: bytes,
    latitude: float,
    longitude: float,
    distance_threshold: float = DEFAULT_DISTANCE_THRESHOLD,
    hash_threshold: int = DEFAULT_HASH_THRESHOLD
) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Check if an image is a duplicate based on image similarity, and optionally location.
    
    Args:
        db: Database session
        image_bytes: Image file bytes to check
        latitude: GPS latitude of the image
        longitude: GPS longitude of the image
        distance_threshold: Maximum distance in meters to consider same location (default: 50m)
        hash_threshold: Maximum Hamming distance for image similarity (default: 5)
        
    Returns:
        Tuple of (is_duplicate: bool, reason: Optional[str], existing_image: Optional[dict])
        - is_duplicate: True if image should be rejected, False if it should be accepted
        - reason: Human-readable reason for rejection (if duplicate)
        - existing_image: Info about the existing duplicate image (if found)
    """
    # Calculate perceptual hash for the new image so visually similar images
    # (not just bit-identical) can be detected.
    new_image_hash = calculate_image_hash(image_bytes, use_perceptual=True)
    
    # Determine if we have a meaningful location
    has_location = latitude is not None and longitude is not None and not (
        latitude == 0.0 and longitude == 0.0
    )

    if has_location:
        # Query images with GPS coordinates near this location
        # We'll check images within a reasonable bounding box first for performance
        # (rough approximation: 1 degree ≈ 111km, so 50m ≈ 0.00045 degrees)
        lat_delta = distance_threshold / 111000.0  # Rough conversion
        lon_delta = distance_threshold / (111000.0 * abs(latitude / 90.0) if latitude != 0 else 111000.0)
        
        nearby_images = (
            db.query(ComplaintImage)
            .filter(
                ComplaintImage.latitude.isnot(None),
                ComplaintImage.longitude.isnot(None),
                ComplaintImage.image_hash.isnot(None),
                ComplaintImage.latitude >= latitude - lat_delta,
                ComplaintImage.latitude <= latitude + lat_delta,
                ComplaintImage.longitude >= longitude - lon_delta,
                ComplaintImage.longitude <= longitude + lon_delta,
            )
            .all()
        )
    else:
        # No reliable location: compare against ALL images using hash only
        nearby_images = (
            db.query(ComplaintImage)
            .filter(ComplaintImage.image_hash.isnot(None))
            .all()
        )
    
    # Check each nearby image
    for existing_image in nearby_images:
        # Calculate exact distance using Haversine formula when we have location
        distance = None
        if has_location and existing_image.latitude is not None and existing_image.longitude is not None:
            distance = calculate_distance(
                latitude,
                longitude,
                existing_image.latitude,
                existing_image.longitude,
            )
            # Only check images within distance threshold
            if distance > distance_threshold:
                continue
        
        # Check if images are similar
        if existing_image.image_hash and compare_image_hashes(
            new_image_hash,
            existing_image.image_hash,
            threshold=hash_threshold,
        ):
            # Similar image (and, when available, same location) → REJECT
            # Fetch ticket and sub_ticket information for user-friendly message
            sub_ticket = db.query(SubTicket).filter(
                SubTicket.sub_id == existing_image.sub_id
            ).first()
            
            ticket_info = None
            if sub_ticket:
                ticket = db.query(Ticket).filter(
                    Ticket.ticket_id == sub_ticket.ticket_id
                ).first()
                
                if ticket:
                    ticket_info = {
                        "ticket_id": ticket.ticket_id,
                        "sub_id": sub_ticket.sub_id,
                        "issue_type": sub_ticket.issue_type,
                        "authority": sub_ticket.authority,
                        "status": sub_ticket.status
                    }
            
            # User-friendly message
            user_message = "This complaint is already registered. Thanks for your concern."
            if ticket_info:
                user_message += f" Ticket ID: {ticket_info['ticket_id']}"
            
            return (
                True,
                user_message,
                {
                    "id": existing_image.id,
                    "sub_id": existing_image.sub_id,
                    "latitude": existing_image.latitude,
                    "longitude": existing_image.longitude,
                    "distance_meters": round(distance, 2) if distance is not None else None,
                    "ticket_info": ticket_info,
                    "message": user_message
                }
            )
    
    # No duplicate found → ACCEPT
    return False, None, None


def should_accept_image(
    db: Session,
    image_bytes: bytes,
    latitude: float,
    longitude: float,
    distance_threshold: float = DEFAULT_DISTANCE_THRESHOLD
) -> Tuple[bool, Optional[str]]:
    """
    Simplified function to determine if an image should be accepted.
    
    Args:
        db: Database session
        image_bytes: Image file bytes
        latitude: GPS latitude
        longitude: GPS longitude
        distance_threshold: Distance threshold in meters (default: 50m)
        
    Returns:
        Tuple of (should_accept: bool, rejection_reason: Optional[str])
    """
    is_duplicate, reason, _ = check_duplicate_image(
        db, image_bytes, latitude, longitude, distance_threshold
    )
    
    # If duplicate, reject; otherwise accept
    return (not is_duplicate, reason)

