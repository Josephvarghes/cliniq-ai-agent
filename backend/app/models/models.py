import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    Date,
    Time,
    DateTime,
    ForeignKey,
    Text,
    Enum as SQLEnum,
    UniqueConstraint
)
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum

class AppointmentStatus(str, enum.Enum):
    BOOKED = "booked"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"
    COMPLETED = "completed"

class NotificationChannel(str, enum.Enum):
    EMAIL = "email"

class NotificationType(str, enum.Enum):
    BOOKING_CONFIRMATION = "booking_confirmation"
    CANCELLATION = "cancellation"
    RESCHEDULE = "reschedule"
    REMINDER = "reminder"
    EMERGENCY_NOTICE = "emergency_notice"

class NotificationStatus(str, enum.Enum):
    SENT = "sent"
    FAILED = "failed"

class Patient(Base):
    __tablename__ = "patients"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = Column(String(120), nullable=False)
    phone_number = Column(String(20), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    appointments = relationship("Appointment", back_populates="patient")
    enquiries = relationship("Enquiry", back_populates="patient")

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    full_name = Column(String(120), nullable=False)
    phone_number = Column(String(20), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    specialization = Column(String(120), default="General Practice")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    availabilities = relationship("DoctorAvailability", back_populates="doctor")
    appointments = relationship("Appointment", back_populates="doctor")

class DoctorAvailability(Base):
    __tablename__ = "doctor_availability"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    doctor_id = Column(String(36), ForeignKey("doctors.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    slot_duration_minutes = Column(Integer, default=30)
    is_blocked = Column(Boolean, default=False)

    doctor = relationship("Doctor", back_populates="availabilities")

class AppointmentType(Base):
    __tablename__ = "appointment_types"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    duration_minutes = Column(Integer, default=30)

    appointments = relationship("Appointment", back_populates="appointment_type")

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    booking_id = Column(String(40), unique=True, index=True, nullable=False)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False)
    doctor_id = Column(String(36), ForeignKey("doctors.id"), nullable=False)
    appointment_type_id = Column(Integer, ForeignKey("appointment_types.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    time_slot = Column(String(20), nullable=False)  # e.g., "10:00 AM" or "10:00"
    status = Column(SQLEnum(AppointmentStatus), default=AppointmentStatus.BOOKED, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    appointment_type = relationship("AppointmentType", back_populates="appointments")
    notifications = relationship("NotificationLog", back_populates="appointment")

    __table_args__ = (
        # Note: Non-cancelled appointments for same doctor, date, and slot must be guarded
        UniqueConstraint("doctor_id", "date", "time_slot", "status", name="uq_doctor_date_slot_status"),
    )

class NotificationLog(Base):
    __tablename__ = "notifications_log"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)
    recipient_email = Column(String(255), nullable=True)
    channel = Column(SQLEnum(NotificationChannel), default=NotificationChannel.EMAIL, nullable=False)
    type = Column(SQLEnum(NotificationType), nullable=False)
    sent_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(SQLEnum(NotificationStatus), nullable=False)
    message_content = Column(Text, nullable=True)

    appointment = relationship("Appointment", back_populates="notifications")

class Enquiry(Base):
    __tablename__ = "enquiries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=True)
    patient_name = Column(String(120), nullable=False)
    patient_phone = Column(String(30), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(20), default="unread")  # unread, responded
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient", back_populates="enquiries")
