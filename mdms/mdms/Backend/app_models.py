from sqlalchemy import Column, Integer, String, Float, Boolean, LargeBinary, ForeignKey, DateTime
from sqlalchemy.sql import func
from database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    ticket_id = Column(String, unique=True, index=True, nullable=False)

    latitude = Column(Float, index=True)
    longitude = Column(Float, index=True)
    address = Column(String)

    status = Column(String, default="open")


class SubTicket(Base):
    __tablename__ = "sub_tickets"

    id = Column(Integer, primary_key=True)
    sub_id = Column(String, unique=True, index=True, nullable=False)

    ticket_id = Column(String, ForeignKey("tickets.ticket_id"), nullable=False)
    issue_type = Column(String, nullable=False)
    authority = Column(String, nullable=False)

    status = Column(String, default="open")


class ComplaintImage(Base):
    __tablename__ = "complaint_images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sub_id = Column(String, ForeignKey("sub_tickets.sub_id"), nullable=False)

    image_data = Column(LargeBinary, nullable=False)
    content_type = Column(String, nullable=False)
    media_type = Column(String, nullable=False, default="image")
    file_name = Column(String, nullable=True)
    gps_extracted = Column(Boolean, default=False)
    
    # Image deduplication fields
    image_hash = Column(String, index=True, nullable=True)  # Perceptual hash for similarity detection
    latitude = Column(Float, index=True, nullable=True)  # GPS latitude for geospatial queries
    longitude = Column(Float, index=True, nullable=True)  # GPS longitude for geospatial queries
    
    # Timestamp - when image was uploaded
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)