from datetime import date as DateType, time as TimeType, datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models.models import AppointmentStatus, NotificationType, NotificationStatus

# --- Auth Schemas ---
class PatientSignupRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=120)
    phone_number: str = Field(..., min_length=7, max_length=20)
    password: str = Field(..., min_length=6)
    email: EmailStr

class PatientLoginRequest(BaseModel):
    phone_number: str
    password: str

class DoctorLoginRequest(BaseModel):
    phone_number: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str  # "patient" or "doctor"
    user: Dict[str, Any]

class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    phone_number: str
    email: str
    created_at: datetime

class DoctorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    phone_number: str
    email: str
    specialization: str

# --- Appointment Type Schemas ---
class AppointmentTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    duration_minutes: int

# --- Availability Schemas ---
class AvailabilityCreate(BaseModel):
    date: DateType
    start_time: str  # e.g., "09:00"
    end_time: str    # e.g., "17:00"
    slot_duration_minutes: int = 30

class AvailabilityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doctor_id: str
    date: DateType
    start_time: str
    end_time: str
    slot_duration_minutes: int
    is_blocked: bool

class EmergencyBlockRequest(BaseModel):
    date: DateType
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    reason: Optional[str] = "Doctor emergency unavailability"

# --- Appointment Schemas ---
class AppointmentBookRequest(BaseModel):
    appointment_type_id: int
    date: DateType
    time_slot: str
    notes: Optional[str] = None

class AppointmentRescheduleRequest(BaseModel):
    new_date: DateType
    new_time_slot: str
    reason: Optional[str] = None

class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_id: str
    patient_id: str
    doctor_id: str
    appointment_type_id: int
    appointment_type_name: Optional[str] = None
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    patient_email: Optional[str] = None
    doctor_name: Optional[str] = None
    date: DateType
    time_slot: str
    status: AppointmentStatus
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

# --- Chatbot Schemas ---
class QuickReplyChip(BaseModel):
    label: str
    value: str
    payload: Optional[Dict[str, Any]] = None

class ChatbotMessageRequest(BaseModel):
    session_id: Optional[str] = None
    message: Optional[str] = None
    action_value: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None

class ChatbotMessageResponse(BaseModel):
    reply_text: str
    action_type: str  # "buttons", "date_picker", "slot_picker", "confirm", "text", "completed"
    quick_replies: List[QuickReplyChip] = []
    current_state: str
    session_data: Dict[str, Any] = {}
    booking_summary: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

# --- Enquiry Schemas ---
class EnquiryCreate(BaseModel):
    patient_name: str
    patient_phone: str
    message: str

class EnquiryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: Optional[str] = None
    patient_name: str
    patient_phone: str
    message: str
    status: str
    created_at: datetime

# --- Doctor CRM Dashboard & Insights Schemas ---
class DoctorDashboardResponse(BaseModel):
    doctor: DoctorOut
    today_date: DateType
    today_bookings: List[AppointmentOut]
    upcoming_bookings: List[AppointmentOut]
    recent_enquiries: List[EnquiryOut]
    metrics_summary: Dict[str, Any]

class InsightsResponse(BaseModel):
    range: str
    total_patients_seen: int
    total_bookings: int
    total_cancellations: int
    total_rescheduled: int
    new_patients_count: int
    returning_patients_count: int
    busiest_day: Optional[str] = None
    busiest_slot: Optional[str] = None
    summary_text: str
    daily_breakdown: List[Dict[str, Any]] = []
