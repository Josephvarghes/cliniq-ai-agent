from datetime import date, datetime, time, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.models import DoctorAvailability, Appointment, AppointmentStatus
from app.services.auth_service import get_default_doctor

def format_slot_display(t: time) -> str:
    """Formats time to readable 12-hour AM/PM string, e.g. '10:00 AM'."""
    return t.strftime("%I:%M %p").lstrip("0")

def parse_slot_str(slot_str: str) -> time:
    """Parses various slot strings into time object."""
    slot_str = slot_str.strip()
    for fmt in ("%I:%M %p", "%H:%M", "%H:%M:%S", "%I:%M%p"):
        try:
            return datetime.strptime(slot_str, fmt).time()
        except ValueError:
            pass
    raise ValueError(f"Unable to parse time slot: {slot_str}")

def get_slots_for_interval(start_t: time, end_t: time, duration_min: int) -> List[str]:
    """Divides an interval into discrete slot strings."""
    slots = []
    curr = datetime.combine(date.today(), start_t)
    end = datetime.combine(date.today(), end_t)
    delta = timedelta(minutes=duration_min)

    while curr + delta <= end:
        slots.append(format_slot_display(curr.time()))
        curr += delta
    return slots

def get_available_slots_for_date(
    db: Session,
    query_date: date,
    doctor_id: Optional[str] = None
) -> List[str]:
    """
    Computes all open, unbooked time slots for the single doctor on query_date.
    Checks doctor_availability table, falls back to standard clinic hours if not explicitly set,
    and removes slots that are already booked (status != cancelled) or blocked.
    """
    if not doctor_id:
        doc = get_default_doctor(db)
        doctor_id = doc.id

    # 1. Fetch any specific availability entries for this date
    availabilities = db.query(DoctorAvailability).filter(
        DoctorAvailability.doctor_id == doctor_id,
        DoctorAvailability.date == query_date
    ).all()

    # If any availability specifically blocks the entire day (is_blocked and 00:00-23:59 or covers all)
    all_day_blocked = any(a.is_blocked for a in availabilities if a.start_time <= time(9, 0) and a.end_time >= time(17, 0))
    if all_day_blocked:
        return []

    generated_slots: List[str] = []

    if availabilities:
        for entry in availabilities:
            if entry.is_blocked:
                continue
            entry_slots = get_slots_for_interval(
                entry.start_time,
                entry.end_time,
                entry.slot_duration_minutes or 30
            )
            for s in entry_slots:
                if s not in generated_slots:
                    generated_slots.append(s)
            # Remove any specific blocked slots
            for blk in availabilities:
                if blk.is_blocked:
                    blocked_slots = get_slots_for_interval(blk.start_time, blk.end_time, blk.slot_duration_minutes or 30)
                    generated_slots = [s for s in generated_slots if s not in blocked_slots]
    else:
        # Default operational clinic hours: 09:00 to 17:00 (lunch 13:00-14:00), 30 min slots
        morning_slots = get_slots_for_interval(time(9, 0), time(13, 0), 30)
        afternoon_slots = get_slots_for_interval(time(14, 0), time(17, 0), 30)
        generated_slots = morning_slots + afternoon_slots

    # 2. Fetch already booked appointments for this doctor on query_date
    active_appointments = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.date == query_date,
        Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.RESCHEDULED])
    ).all()

    booked_slot_set = {apt.time_slot.strip().upper() for apt in active_appointments}

    # Helper normalizer for comparison
    def normalize_slot(s: str) -> str:
        try:
            t = parse_slot_str(s)
            return format_slot_display(t).strip().upper()
        except Exception:
            return s.strip().upper()

    booked_normalized = {normalize_slot(s) for s in booked_slot_set}

    # 3. Filter out booked slots
    open_slots = [slot for slot in generated_slots if normalize_slot(slot) not in booked_normalized]
    return open_slots

def is_slot_available(
    db: Session,
    query_date: date,
    time_slot: str,
    doctor_id: Optional[str] = None,
    exclude_appointment_id: Optional[int] = None
) -> bool:
    """Verifies that a slot is free and not conflicting with an existing booking."""
    if not doctor_id:
        doc = get_default_doctor(db)
        doctor_id = doc.id

    query = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.date == query_date,
        Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.RESCHEDULED])
    )

    if exclude_appointment_id:
        query = query.filter(Appointment.id != exclude_appointment_id)

    existing = query.all()

    def normalize(s: str) -> str:
        try:
            return format_slot_display(parse_slot_str(s)).upper()
        except Exception:
            return s.strip().upper()

    target_normalized = normalize(time_slot)
    for apt in existing:
        if normalize(apt.time_slot) == target_normalized:
            return False

    return True
