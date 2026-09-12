from datetime import date, timedelta
from typing import Dict, Any, List
from collections import Counter
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.models import Appointment, AppointmentStatus, Patient, Doctor
from app.schemas.schemas import InsightsResponse

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def calculate_insights(db: Session, doctor_id: str, range_type: str = "monthly") -> InsightsResponse:
    today = date.today()
    if range_type == "weekly":
        start_date = today - timedelta(days=7)
        prev_start = start_date - timedelta(days=7)
        period_label = "this week"
    else:  # monthly
        start_date = today - timedelta(days=30)
        prev_start = start_date - timedelta(days=30)
        period_label = "this month"

    # Current period query
    appts = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.date >= start_date,
        Appointment.date <= today
    ).all()

    # Previous period count for trend comparison
    prev_count = db.query(func.count(Appointment.id)).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.date >= prev_start,
        Appointment.date < start_date
    ).scalar() or 0

    total_bookings = len(appts)
    total_cancelled = sum(1 for a in appts if a.status == AppointmentStatus.CANCELLED)
    total_rescheduled = sum(1 for a in appts if a.status == AppointmentStatus.RESCHEDULED)
    total_seen = sum(1 for a in appts if a.status in [AppointmentStatus.COMPLETED, AppointmentStatus.BOOKED] and a.date <= today)

    # Patient repetition check (new vs returning)
    patient_ids_in_period = [a.patient_id for a in appts]
    unique_patients = set(patient_ids_in_period)

    new_patients_count = 0
    returning_patients_count = 0

    for pid in unique_patients:
        # Check if patient had appointments prior to start_date
        prior_count = db.query(func.count(Appointment.id)).filter(
            Appointment.patient_id == pid,
            Appointment.doctor_id == doctor_id,
            Appointment.date < start_date
        ).scalar() or 0

        if prior_count > 0:
            returning_patients_count += 1
        else:
            new_patients_count += 1

    # Busiest days & time slots
    days_counter = Counter([DAY_NAMES[a.date.weekday()] for a in appts])
    slots_counter = Counter([a.time_slot for a in appts])

    busiest_day = days_counter.most_common(1)[0][0] if days_counter else "None"
    busiest_slot = slots_counter.most_common(1)[0][0] if slots_counter else "None"

    # Trend calculation
    trend_pct = 0
    if prev_count > 0:
        trend_pct = round(((total_bookings - prev_count) / prev_count) * 100)
        trend_text = f"{abs(trend_pct)}% {'more' if trend_pct >= 0 else 'less'} than last {range_type.replace('ly', '')}"
    else:
        trend_text = "steady volume"

    # Rule-based templated summary
    if total_bookings > 0:
        cancellation_rate = round((total_cancelled / total_bookings) * 100) if total_bookings else 0
        summary_text = (
            f"You had {total_bookings} appointments {period_label} ({trend_text}). "
            f"{busiest_day}s were your busiest days, with peak demand at {busiest_slot}. "
            f"Cancellation rate stood at {cancellation_rate}%, with {new_patients_count} new patient(s) registered."
        )
    else:
        summary_text = f"No appointment records found for {period_label}. Booking channels are live and accepting patients."

    # Build daily breakdown list for charting
    daily_map = {}
    curr = start_date
    while curr <= today:
        daily_map[curr.isoformat()] = {"date": curr.strftime("%b %d"), "booked": 0, "cancelled": 0}
        curr += timedelta(days=1)

    for a in appts:
        d_str = a.date.isoformat()
        if d_str in daily_map:
            if a.status == AppointmentStatus.CANCELLED:
                daily_map[d_str]["cancelled"] += 1
            else:
                daily_map[d_str]["booked"] += 1

    daily_breakdown = list(daily_map.values())[-14:]  # Last 14 days

    return InsightsResponse(
        range=range_type,
        total_patients_seen=total_seen,
        total_bookings=total_bookings,
        total_cancellations=total_cancelled,
        total_rescheduled=total_rescheduled,
        new_patients_count=new_patients_count,
        returning_patients_count=returning_patients_count,
        busiest_day=busiest_day,
        busiest_slot=busiest_slot,
        summary_text=summary_text,
        daily_breakdown=daily_breakdown
    )
