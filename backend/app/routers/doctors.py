from datetime import date, datetime, timedelta, time
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import (
    Doctor, DoctorAvailability, Appointment, AppointmentStatus, NotificationType, Enquiry
)
from app.schemas.schemas import (
    DoctorDashboardResponse,
    DoctorOut,
    AppointmentOut,
    AvailabilityCreate,
    AvailabilityOut,
    EmergencyBlockRequest,
    InsightsResponse,
    EnquiryOut
)
from app.services.auth_service import get_current_doctor, get_default_doctor
from app.services.insights_service import calculate_insights
from app.services.email_service import send_appointment_email
from app.services.slot_service import parse_slot_str

router = APIRouter(prefix="/doctors", tags=["Doctor CRM"])

@router.get("/{id}/dashboard", response_model=DoctorDashboardResponse)
def get_doctor_dashboard(
    id: str,
    doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    today = date.today()
    next_7_days = today + timedelta(days=7)

    # Today's appointments
    today_appts = db.query(Appointment).filter(
        Appointment.doctor_id == doctor.id,
        Appointment.date == today
    ).order_by(Appointment.time_slot.asc()).all()

    # Next 7 days
    upcoming_appts = db.query(Appointment).filter(
        Appointment.doctor_id == doctor.id,
        Appointment.date > today,
        Appointment.date <= next_7_days
    ).order_by(Appointment.date.asc(), Appointment.time_slot.asc()).all()

    # Recent patient enquiries
    enquiries = db.query(Enquiry).order_by(Enquiry.created_at.desc()).limit(10).all()

    # Helper mapper
    def map_appt(a: Appointment) -> AppointmentOut:
        return AppointmentOut(
            id=a.id,
            booking_id=a.booking_id,
            patient_id=a.patient_id,
            doctor_id=a.doctor_id,
            appointment_type_id=a.appointment_type_id,
            appointment_type_name=a.appointment_type.name if a.appointment_type else "Consultation",
            patient_name=a.patient.full_name if a.patient else None,
            patient_phone=a.patient.phone_number if a.patient else None,
            patient_email=a.patient.email if a.patient else None,
            doctor_name=doctor.full_name,
            date=a.date,
            time_slot=a.time_slot,
            status=a.status,
            notes=a.notes,
            created_at=a.created_at,
            updated_at=a.updated_at
        )

    # Summary metrics for header cards
    active_today = sum(1 for a in today_appts if a.status in [AppointmentStatus.BOOKED, AppointmentStatus.RESCHEDULED])
    total_upcoming = sum(1 for a in upcoming_appts if a.status in [AppointmentStatus.BOOKED, AppointmentStatus.RESCHEDULED])
    unread_enquiries = sum(1 for e in enquiries if e.status == "unread")

    return DoctorDashboardResponse(
        doctor=DoctorOut(
            id=doctor.id,
            full_name=doctor.full_name,
            phone_number=doctor.phone_number,
            email=doctor.email,
            specialization=doctor.specialization
        ),
        today_date=today,
        today_bookings=[map_appt(a) for a in today_appts],
        upcoming_bookings=[map_appt(a) for a in upcoming_appts],
        recent_enquiries=[
            EnquiryOut(
                id=e.id,
                patient_id=e.patient_id,
                patient_name=e.patient_name,
                patient_phone=e.patient_phone,
                message=e.message,
                status=e.status,
                created_at=e.created_at
            ) for e in enquiries
        ],
        metrics_summary={
            "today_active_appointments": active_today,
            "next_7_days_appointments": total_upcoming,
            "pending_enquiries": unread_enquiries
        }
    )

@router.get("/{id}/schedule", response_model=List[AvailabilityOut])
def get_doctor_schedule(
    id: str,
    doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    availabilities = db.query(DoctorAvailability).filter(
        DoctorAvailability.doctor_id == doctor.id,
        DoctorAvailability.date >= date.today()
    ).order_by(DoctorAvailability.date.asc(), DoctorAvailability.start_time.asc()).all()

    return [
        AvailabilityOut(
            id=a.id,
            doctor_id=a.doctor_id,
            date=a.date,
            start_time=a.start_time.strftime("%H:%M"),
            end_time=a.end_time.strftime("%H:%M"),
            slot_duration_minutes=a.slot_duration_minutes,
            is_blocked=a.is_blocked
        ) for a in availabilities
    ]

@router.post("/{id}/schedule", response_model=AvailabilityOut)
def create_doctor_schedule(
    id: str,
    payload: AvailabilityCreate,
    doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    try:
        s_time = parse_slot_str(payload.start_time)
        e_time = parse_slot_str(payload.end_time)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid start or end time format (use HH:MM).")

    new_avail = DoctorAvailability(
        doctor_id=doctor.id,
        date=payload.date,
        start_time=s_time,
        end_time=e_time,
        slot_duration_minutes=payload.slot_duration_minutes,
        is_blocked=False
    )
    db.add(new_avail)
    db.commit()
    db.refresh(new_avail)

    return AvailabilityOut(
        id=new_avail.id,
        doctor_id=new_avail.doctor_id,
        date=new_avail.date,
        start_time=new_avail.start_time.strftime("%H:%M"),
        end_time=new_avail.end_time.strftime("%H:%M"),
        slot_duration_minutes=new_avail.slot_duration_minutes,
        is_blocked=new_avail.is_blocked
    )

@router.post("/{id}/schedule/block")
def emergency_block_schedule(
    id: str,
    payload: EmergencyBlockRequest,
    doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    """
    Emergency blocks a day or specific hours and automatically notifies all affected patients via email.
    """
    s_time = parse_slot_str(payload.start_time) if payload.start_time else time(0, 0)
    e_time = parse_slot_str(payload.end_time) if payload.end_time else time(23, 59)

    block_record = DoctorAvailability(
        doctor_id=doctor.id,
        date=payload.date,
        start_time=s_time,
        end_time=e_time,
        slot_duration_minutes=30,
        is_blocked=True
    )
    db.add(block_record)
    db.commit()

    # Find all active appointments scheduled on this date (and time range if given)
    affected = db.query(Appointment).filter(
        Appointment.doctor_id == doctor.id,
        Appointment.date == payload.date,
        Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.RESCHEDULED])
    ).all()

    notified_patients = []
    for appt in affected:
        # Broadcast emergency notice email
        send_appointment_email(
            db,
            appt,
            NotificationType.EMERGENCY_NOTICE,
            custom_notes=payload.reason
        )
        notified_patients.append({
            "booking_id": appt.booking_id,
            "patient_name": appt.patient.full_name if appt.patient else "Patient",
            "patient_email": appt.patient.email if appt.patient else "",
            "time_slot": appt.time_slot
        })

    return {
        "status": "blocked",
        "date": payload.date.isoformat(),
        "start_time": s_time.strftime("%H:%M"),
        "end_time": e_time.strftime("%H:%M"),
        "affected_appointments_count": len(notified_patients),
        "notified_patients": notified_patients,
        "message": f"Emergency block registered for {payload.date}. Automated email alerts sent to {len(notified_patients)} affected patient(s)."
    }

@router.get("/{id}/insights", response_model=InsightsResponse)
def get_doctor_insights(
    id: str,
    range: str = Query("monthly", pattern="^(monthly|weekly)$"),
    doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    return calculate_insights(db, doctor.id, range)

@router.get("/{id}/enquiries", response_model=List[EnquiryOut])
def get_enquiries(
    id: str,
    doctor: Doctor = Depends(get_current_doctor),
    db: Session = Depends(get_db)
):
    enquiries = db.query(Enquiry).order_by(Enquiry.created_at.desc()).all()
    return [
        EnquiryOut(
            id=e.id,
            patient_id=e.patient_id,
            patient_name=e.patient_name,
            patient_phone=e.patient_phone,
            message=e.message,
            status=e.status,
            created_at=e.created_at
        ) for e in enquiries
    ]
