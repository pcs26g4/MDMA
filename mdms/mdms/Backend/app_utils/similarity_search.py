"""
Similarity Search Utilities
Provides functions for searching similar images and complaints based on:
- Image similarity (perceptual hash)
- Geographic proximity
- Issue type matching
"""
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Tuple
from app_models import ComplaintImage, SubTicket, Ticket
from app_utils.image_hash import calculate_image_hash, compare_image_hashes
from app_utils.geo import calculate_distance


def search_similar_images(
    db: Session,
    query_image_hash: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    max_distance: Optional[float] = None,
    hash_threshold: int = 10,
    limit: int = 20,
    exclude_image_id: Optional[int] = None
) -> List[Dict]:
    """
    Search for images similar to a query image hash.
    
    Args:
        db: Database session
        query_image_hash: Perceptual hash of the query image
        latitude: Optional GPS latitude for location-based filtering
        longitude: Optional GPS longitude for location-based filtering
        max_distance: Optional maximum distance in meters for location filtering
        hash_threshold: Maximum Hamming distance for similarity (default: 10)
        limit: Maximum number of results to return
        exclude_image_id: Optional image ID to exclude from results
        
    Returns:
        List of dictionaries containing similar image information
    """
    # Base query for images with hashes
    query = db.query(ComplaintImage).filter(
        ComplaintImage.image_hash.isnot(None)
    )
    
    # Exclude specific image if provided
    if exclude_image_id:
        query = query.filter(ComplaintImage.id != exclude_image_id)
    
    # If location is provided, filter by bounding box first for performance
    if latitude is not None and longitude is not None and max_distance:
        lat_delta = max_distance / 111000.0
        lon_delta = max_distance / (111000.0 * abs(latitude / 90.0) if latitude != 0 else 111000.0)
        
        query = query.filter(
            ComplaintImage.latitude.isnot(None),
            ComplaintImage.longitude.isnot(None),
            ComplaintImage.latitude >= latitude - lat_delta,
            ComplaintImage.latitude <= latitude + lat_delta,
            ComplaintImage.longitude >= longitude - lon_delta,
            ComplaintImage.longitude <= longitude + lon_delta
        )
    
    all_images = query.all()
    
    # Calculate similarity scores
    similar_images = []
    for image in all_images:
        if not image.image_hash:
            continue
        
        # Calculate hash similarity
        is_similar = compare_image_hashes(
            query_image_hash,
            image.image_hash,
            threshold=hash_threshold
        )
        
        if not is_similar:
            continue
        
        # Calculate Hamming distance for ranking
        try:
            from app_utils.image_hash import IMAGEHASH_AVAILABLE
            if IMAGEHASH_AVAILABLE:
                import imagehash
                h1 = imagehash.hex_to_hash(query_image_hash)
                h2 = imagehash.hex_to_hash(image.image_hash)
                hamming_distance = h1 - h2
            else:
                # Fallback: exact match = 0, otherwise high distance
                hamming_distance = 0 if query_image_hash == image.image_hash else 100
        except:
            hamming_distance = 0 if query_image_hash == image.image_hash else 100
        
        # Calculate distance if location is provided
        distance_meters = None
        if latitude is not None and longitude is not None and image.latitude and image.longitude:
            distance_meters = calculate_distance(
                latitude, longitude,
                image.latitude, image.longitude
            )
            
            # Skip if beyond max_distance
            if max_distance and distance_meters > max_distance:
                continue
        
        # Get ticket and sub_ticket information
        sub_ticket = db.query(SubTicket).filter(
            SubTicket.sub_id == image.sub_id
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
        
        similar_images.append({
            "image_id": image.id,
            "sub_id": image.sub_id,
            "file_name": image.file_name,
            "content_type": image.content_type,
            "latitude": image.latitude,
            "longitude": image.longitude,
            "distance_meters": round(distance_meters, 2) if distance_meters else None,
            "hamming_distance": hamming_distance,
            "similarity_score": max(0, 100 - (hamming_distance * 10)),  # Convert to percentage
            "created_at": image.created_at.isoformat() if image.created_at else None,
            "ticket_info": ticket_info
        })
    
    # Sort by similarity (lower Hamming distance = more similar)
    # If location is provided, also consider distance
    if latitude is not None and longitude is not None:
        similar_images.sort(key=lambda x: (
            x["hamming_distance"],
            x["distance_meters"] if x["distance_meters"] else float('inf')
        ))
    else:
        similar_images.sort(key=lambda x: x["hamming_distance"])
    
    return similar_images[:limit]


def search_similar_by_location(
    db: Session,
    latitude: float,
    longitude: float,
    max_distance: float = 1000.0,  # 1km default
    issue_type: Optional[str] = None,
    limit: int = 50
) -> List[Dict]:
    """
    Search for complaints/images near a specific location.
    
    Args:
        db: Database session
        latitude: GPS latitude
        longitude: GPS longitude
        max_distance: Maximum distance in meters (default: 1000m)
        issue_type: Optional filter by issue type
        limit: Maximum number of results
        
    Returns:
        List of dictionaries containing nearby complaints
    """
    # Calculate bounding box
    lat_delta = max_distance / 111000.0
    lon_delta = max_distance / (111000.0 * abs(latitude / 90.0) if latitude != 0 else 111000.0)
    
    # Query images within bounding box
    query = db.query(ComplaintImage).filter(
        ComplaintImage.latitude.isnot(None),
        ComplaintImage.longitude.isnot(None),
        ComplaintImage.latitude >= latitude - lat_delta,
        ComplaintImage.latitude <= latitude + lat_delta,
        ComplaintImage.longitude >= longitude - lon_delta,
        ComplaintImage.longitude <= longitude + lon_delta
    )
    
    images = query.all()
    
    # Filter by exact distance and issue type
    results = []
    for image in images:
        distance = calculate_distance(
            latitude, longitude,
            image.latitude, image.longitude
        )
        
        if distance > max_distance:
            continue
        
        # Get sub_ticket and ticket info
        sub_ticket = db.query(SubTicket).filter(
            SubTicket.sub_id == image.sub_id
        ).first()
        
        if not sub_ticket:
            continue
        
        # Filter by issue type if provided
        if issue_type and sub_ticket.issue_type != issue_type:
            continue
        
        ticket = db.query(Ticket).filter(
            Ticket.ticket_id == sub_ticket.ticket_id
        ).first()
        
        if not ticket:
            continue
        
        results.append({
            "image_id": image.id,
            "ticket_id": ticket.ticket_id,
            "sub_id": sub_ticket.sub_id,
            "issue_type": sub_ticket.issue_type,
            "authority": sub_ticket.authority,
            "status": sub_ticket.status,
            "latitude": image.latitude,
            "longitude": image.longitude,
            "distance_meters": round(distance, 2),
            "file_name": image.file_name,
            "created_at": image.created_at.isoformat() if image.created_at else None
        })
    
    # Sort by distance
    results.sort(key=lambda x: x["distance_meters"])
    
    return results[:limit]


def search_similar_by_issue_type(
    db: Session,
    issue_type: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    max_distance: Optional[float] = None,
    limit: int = 50
) -> List[Dict]:
    """
    Search for complaints by issue type, optionally filtered by location.
    
    Args:
        db: Database session
        issue_type: Issue type to search for
        latitude: Optional GPS latitude
        longitude: Optional GPS longitude
        max_distance: Optional maximum distance in meters
        limit: Maximum number of results
        
    Returns:
        List of dictionaries containing matching complaints
    """
    # Query sub_tickets by issue type
    query = db.query(SubTicket).filter(
        SubTicket.issue_type == issue_type
    )
    
    sub_tickets = query.all()
    
    results = []
    for sub_ticket in sub_tickets:
        # Get images for this sub_ticket
        images = db.query(ComplaintImage).filter(
            ComplaintImage.sub_id == sub_ticket.sub_id
        ).all()
        
        # Get ticket info
        ticket = db.query(Ticket).filter(
            Ticket.ticket_id == sub_ticket.ticket_id
        ).first()
        
        if not ticket:
            continue
        
        # If location filter is provided, check if any image matches
        if latitude is not None and longitude is not None and max_distance:
            matching_images = []
            for image in images:
                if image.latitude and image.longitude:
                    distance = calculate_distance(
                        latitude, longitude,
                        image.latitude, image.longitude
                    )
                    if distance <= max_distance:
                        matching_images.append({
                            "image_id": image.id,
                            "distance_meters": round(distance, 2)
                        })
            
            if not matching_images:
                continue  # Skip if no images match location filter
            
            # Use the closest image
            closest = min(matching_images, key=lambda x: x["distance_meters"])
            distance_meters = closest["distance_meters"]
        else:
            # Get first image with GPS or any image
            gps_image = next(
                (img for img in images if img.latitude and img.longitude),
                images[0] if images else None
            )
            distance_meters = None
            if gps_image and latitude and longitude:
                distance_meters = round(calculate_distance(
                    latitude, longitude,
                    gps_image.latitude, gps_image.longitude
                ), 2)
        
        results.append({
            "ticket_id": ticket.ticket_id,
            "sub_id": sub_ticket.sub_id,
            "issue_type": sub_ticket.issue_type,
            "authority": sub_ticket.authority,
            "status": sub_ticket.status,
            "latitude": ticket.latitude,
            "longitude": ticket.longitude,
            "distance_meters": distance_meters,
            "image_count": len(images)
        })
    
    # Sort by distance if location provided, otherwise by ticket_id
    if latitude is not None and longitude is not None:
        results.sort(key=lambda x: x["distance_meters"] if x["distance_meters"] else float('inf'))
    else:
        results.sort(key=lambda x: x["ticket_id"])
    
    return results[:limit]
