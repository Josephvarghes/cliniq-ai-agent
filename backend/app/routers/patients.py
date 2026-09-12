from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Appointment, Patient, AppointmentStatus
from app.schemas.schemas import AppointmentOut
from app.services.auth_service import get_current_user_token

router = APIRouter(prefix="/patients", tags=["Patients"])

@router.get("/{id}/bookings", response_model=List[AppointmentOut])
def get_patient_bookings(
    id: str,
    status_filter: Optional[str] = Query(None, description="Filter by status: booked, cancelled, rescheduled, completed"),
    token_data: dict = Depends(get_current_user_token),
    db: Session = Depends(get_db)
):
    # Verify authorization: patient can only access their own, doctor can access any
    if token_data.get("role") == "patient" and token_data.get("sub") != id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view another patient's bookings."
        )

    query = db.query(Appointment).filter(Appointment.patient_id == id)
    if status_filter:
        query = query.filter(Appointment.status == status_filter.lower())

    appts = query.order_by(Appointment.date.desc(), Appointment.time_slot.asc()).all()

    # Format output with relation names
    results = []
    for a in appts:
        results.append(
            AppointmentOut(
                id=a.id,
                booking_id=a.booking_id,
                patient_id=a.patient_id,
                doctor_id=a.doctor_id,
                appointment_type_id=a.appointment_type_id,
                appointment_type_name=a.appointment_type.name if a.appointment_type else "Consultation",
                patient_name=a.patient.full_name if a.patient else None,
                patient_phone=a.patient.phone_number if a.patient else None,
                patient_email=a.patient.email if a.patient else None,
                doctor_name=a.doctor.full_name if a.doctor else None,
                date=a.date,
                time_slot=a.time_slot,
                status=a.status,
                notes=a.notes,
                created_at=a.created_at,
                updated_at=a.updated_at
            )
        )
    return results
