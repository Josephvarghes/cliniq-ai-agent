from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Appointment, AppointmentStatus, Patient, NotificationType
from app.schemas.schemas import AppointmentBookRequest, AppointmentRescheduleRequest, AppointmentOut
from app.services.auth_service import get_current_patient, get_default_doctor
from app.services.slot_service import is_slot_available
from app.services.chatbot_fsm import generate_booking_id
from app.services.email_service import send_appointment_email

router = APIRouter(prefix="/appointments", tags=["Appointments"])

@router.post("/book", response_model=AppointmentOut)
def book_appointment(
    payload: AppointmentBookRequest,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db)
):
    doctor = get_default_doctor(db)

    # Double-booking guard
    if not is_slot_available(db, payload.date, payload.time_slot, doctor.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This slot is already booked or unavailable. Please choose another slot."
        )

    booking_id = generate_booking_id(payload.date)
    appointment = Appointment(
        booking_id=booking_id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_type_id=payload.appointment_type_id,
        date=payload.date,
        time_slot=payload.time_slot,
        status=AppointmentStatus.BOOKED,
        notes=payload.notes
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    # Trigger booking confirmation email
    send_appointment_email(db, appointment, NotificationType.BOOKING_CONFIRMATION)

    return AppointmentOut(
        id=appointment.id,
        booking_id=appointment.booking_id,
        patient_id=appointment.patient_id,
        doctor_id=appointment.doctor_id,
        appointment_type_id=appointment.appointment_type_id,
        appointment_type_name=appointment.appointment_type.name if appointment.appointment_type else "Consultation",
        patient_name=patient.full_name,
        patient_phone=patient.phone_number,
        patient_email=patient.email,
        doctor_name=doctor.full_name,
        date=appointment.date,
        time_slot=appointment.time_slot,
        status=appointment.status,
        notes=appointment.notes,
        created_at=appointment.created_at,
        updated_at=appointment.updated_at
    )

@router.post("/{id}/cancel")
def cancel_appointment(
    id: int,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db)
):
    appointment = db.query(Appointment).filter(
        Appointment.id == id,
        Appointment.patient_id == patient.id
    ).first()

    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")

    if appointment.status == AppointmentStatus.CANCELLED:
        return {"booking_id": appointment.booking_id, "status": "cancelled", "message": "Appointment is already cancelled."}

    appointment.status = AppointmentStatus.CANCELLED
    db.commit()

    # Trigger cancellation email
    send_appointment_email(db, appointment, NotificationType.CANCELLATION)

    return {
        "booking_id": appointment.booking_id,
        "status": "cancelled",
        "message": f"Appointment {appointment.booking_id} successfully cancelled."
    }

@router.post("/{id}/reschedule", response_model=AppointmentOut)
def reschedule_appointment(
    id: int,
    payload: AppointmentRescheduleRequest,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db)
):
    appointment = db.query(Appointment).filter(
        Appointment.id == id,
        Appointment.patient_id == patient.id
    ).first()

    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")

    # Guard availability on new slot
    if not is_slot_available(db, payload.new_date, payload.new_time_slot, appointment.doctor_id, exclude_appointment_id=appointment.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The requested slot is already booked. Please choose another."
        )

    appointment.date = payload.new_date
    appointment.time_slot = payload.new_time_slot
    appointment.status = AppointmentStatus.RESCHEDULED
    if payload.reason:
        appointment.notes = f"{appointment.notes or ''} | Reschedule note: {payload.reason}".strip()

    db.commit()
    db.refresh(appointment)

    # Trigger reschedule email
    send_appointment_email(db, appointment, NotificationType.RESCHEDULE)

    return AppointmentOut(
        id=appointment.id,
        booking_id=appointment.booking_id,
        patient_id=appointment.patient_id,
        doctor_id=appointment.doctor_id,
        appointment_type_id=appointment.appointment_type_id,
        appointment_type_name=appointment.appointment_type.name if appointment.appointment_type else "Consultation",
        patient_name=patient.full_name,
        patient_phone=patient.phone_number,
        patient_email=patient.email,
        doctor_name=appointment.doctor.full_name if appointment.doctor else None,
        date=appointment.date,
        time_slot=appointment.time_slot,
        status=appointment.status,
        notes=appointment.notes,
        created_at=appointment.created_at,
        updated_at=appointment.updated_at
    )
