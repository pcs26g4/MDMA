from app_models import Ticket, SubTicket, ComplaintImage
import uuid


# ---------- Ticket ----------
def get_or_create_ticket(db, lat, lon):
    """
    ALWAYS create a new ticket.
    Previously this reused an open ticket at the same lat/lon, which caused
    new complaints to show the same ticket_id. The product requirement is to
    generate a fresh ticket ID for each submission.
    """
    ticket = Ticket(
        ticket_id=f"MDMS-{uuid.uuid4().hex[:8].upper()}",
        latitude=lat,
        longitude=lon
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


# ---------- Sub Ticket ----------
def get_or_create_sub_ticket(db, ticket_id, issue_type, authority):
    """
    ALWAYS create a new sub-ticket.
    Previously this reused an existing sub_ticket for the same ticket_id +
    issue_type, which made multiple complaints share the same sub_id.
    """
    sub_ticket = SubTicket(
        sub_id=f"SUB-{uuid.uuid4().hex[:6].upper()}",
        ticket_id=ticket_id,
        issue_type=issue_type,
        authority=authority
    )
    db.add(sub_ticket)
    db.commit()
    db.refresh(sub_ticket)
    return sub_ticket


# ---------- Image ----------
def save_image(
    db, 
    sub_id, 
    image_bytes, 
    content_type, 
    gps_extracted, 
    media_type="image",
    file_name=None,
    latitude=None,
    longitude=None
):
    # Calculate image hash for deduplication
    from app_utils.image_hash import calculate_image_hash
    image_hash = calculate_image_hash(image_bytes, use_perceptual=True)
    
    image = ComplaintImage(
        sub_id=sub_id,
        image_data=image_bytes,
        content_type=content_type,
        media_type=media_type,
        file_name=file_name,
        gps_extracted=gps_extracted,
        image_hash=image_hash,
        latitude=latitude,
        longitude=longitude
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image
