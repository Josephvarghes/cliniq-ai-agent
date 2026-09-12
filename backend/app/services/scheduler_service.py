from datetime import date, datetime, timedelta, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.models import Appointment, AppointmentStatus, NotificationType, NotificationLog
from app.services.email_service import send_appointment_email

scheduler = BackgroundScheduler()

def check_and_send_appointment_reminders():
    """Runs periodically to send reminders 24h before scheduled appointments."""
    db: Session = SessionLocal()
    try:
        tomorrow = date.today() + timedelta(days=1)
        # Find active appointments for tomorrow
        upcoming = db.query(Appointment).filter(
            Appointment.date == tomorrow,
            Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.RESCHEDULED])
        ).all()

        for appt in upcoming:
            # Check if reminder already logged
            already_sent = db.query(NotificationLog).filter(
                NotificationLog.appointment_id == appt.id,
                NotificationLog.type == NotificationType.REMINDER
            ).first()

            if not already_sent:
                send_appointment_email(db, appt, NotificationType.REMINDER)
                print(f"⏰ [REMINDER] Sent 24h reminder for {appt.booking_id}")
    except Exception as e:
        print(f"[Scheduler Error] {e}")
    finally:
        db.close()

def start_scheduler():
    if not scheduler.running:
        # Check every 30 minutes
        scheduler.add_job(check_and_send_appointment_reminders, "interval", minutes=30, id="appointment_reminders", replace_existing=True)
        scheduler.start()
        print("🕒 Background Appointment Reminder Scheduler Started.")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
