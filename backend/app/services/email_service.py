import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.models import (
    NotificationLog,
    NotificationChannel,
    NotificationType,
    NotificationStatus,
    Appointment
)

def format_email_body(
    event_type: NotificationType,
    booking_id: str,
    patient_name: str,
    doctor_name: str,
    date_str: str,
    time_slot: str,
    appointment_type: str,
    notes: Optional[str] = None
) -> tuple[str, str]:
    """Generates subject and HTML body for notifications."""
    if event_type == NotificationType.BOOKING_CONFIRMATION:
        subject = f"✅ Appointment Confirmed - {booking_id} | Cliniq"
        heading = "Appointment Confirmation"
        intro = f"Dear {patient_name}, your consultation appointment has been successfully scheduled."
        action_note = "Please arrive 10 minutes prior to your scheduled consultation."
    elif event_type == NotificationType.CANCELLATION:
        subject = f"❌ Appointment Cancelled - {booking_id} | Cliniq"
        heading = "Appointment Cancellation"
        intro = f"Dear {patient_name}, your appointment has been cancelled as requested."
        action_note = "If you wish to reschedule or book a new appointment, you can do so anytime via our clinic booking portal."
    elif event_type == NotificationType.RESCHEDULE:
        subject = f"🔄 Appointment Rescheduled - {booking_id} | Cliniq"
        heading = "Appointment Reschedule Confirmation"
        intro = f"Dear {patient_name}, your appointment has been rescheduled to a new time."
        action_note = "Please note your updated consultation schedule below."
    elif event_type == NotificationType.REMINDER:
        subject = f"⏰ Upcoming Consultation Reminder - {booking_id} | Cliniq"
        heading = "Appointment Reminder"
        intro = f"Dear {patient_name}, this is a friendly reminder of your upcoming consultation."
        action_note = "If you need to reschedule, please visit the clinic portal at least 4 hours in advance."
    elif event_type == NotificationType.EMERGENCY_NOTICE:
        subject = f"⚠️ Important: Urgent Schedule Change - {booking_id} | Cliniq"
        heading = "Urgent Schedule Notice"
        intro = f"Dear {patient_name}, due to an unforeseen doctor emergency, your appointment has to be rescheduled."
        action_note = "Please open the clinic portal or reply to this notice to choose an alternate time that suits you best."
    else:
        subject = f"Appointment Notification - {booking_id} | Cliniq"
        heading = "Clinic Notification"
        intro = f"Dear {patient_name}, here is an update regarding your appointment."
        action_note = ""

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; color: #1e293b; }}
    .container {{ max-width: 580px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
    .header {{ background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%); color: #ffffff; padding: 24px; text-align: center; }}
    .content {{ padding: 24px; }}
    .card {{ background: #f1f5f9; border-radius: 8px; padding: 16px; margin: 20px 0; }}
    .card-row {{ display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #e2e8f0; }}
    .card-row:last-child {{ border-bottom: none; }}
    .label {{ font-weight: 600; color: #64748b; font-size: 14px; }}
    .val {{ font-weight: 600; color: #0f172a; font-size: 14px; }}
    .footer {{ background: #f8fafc; padding: 16px; text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; }}
    .notice {{ background: #e0f2fe; color: #0369a1; padding: 12px; border-radius: 6px; font-size: 13px; margin-top: 16px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h2 style="margin:0; font-size: 20px;">Cliniq Medical Care</h2>
      <p style="margin:4px 0 0 0; opacity: 0.9; font-size: 14px;">{heading}</p>
    </div>
    <div class="content">
      <p>{intro}</p>
      <div class="card">
        <div class="card-row"><span class="label">Booking Reference:</span><span class="val" style="color:#0284c7;">{booking_id}</span></div>
        <div class="card-row"><span class="label">Patient Name:</span><span class="val">{patient_name}</span></div>
        <div class="card-row"><span class="label">Doctor:</span><span class="val">{doctor_name}</span></div>
        <div class="card-row"><span class="label">Appointment Type:</span><span class="val">{appointment_type}</span></div>
        <div class="card-row"><span class="label">Scheduled Date:</span><span class="val">{date_str}</span></div>
        <div class="card-row"><span class="label">Time Slot:</span><span class="val">{time_slot}</span></div>
        {f'<div class="card-row"><span class="label">Notes:</span><span class="val">{notes}</span></div>' if notes else ''}
      </div>
      {f'<div class="notice">💡 <strong>Note:</strong> {action_note}</div>' if action_note else ''}
      <p style="font-size: 13px; color: #64748b; margin-top: 24px;">Need help? You can manage your appointments anytime via the Cliniq online portal.</p>
    </div>
    <div class="footer">
      Cliniq Automated Practice Notification • Please do not reply directly to this automated email.
    </div>
  </div>
</body>
</html>
"""
    return subject, html_content

def send_appointment_email(
    db: Session,
    appointment: Appointment,
    event_type: NotificationType,
    custom_recipient: Optional[str] = None,
    custom_notes: Optional[str] = None
) -> bool:
    """Dispatches email notification with retry and DB logging."""
    recipient_email = custom_recipient or (appointment.patient.email if appointment.patient else None)
    if not recipient_email:
        return False

    patient_name = appointment.patient.full_name if appointment.patient else "Valued Patient"
    doctor_name = appointment.doctor.full_name if appointment.doctor else settings.DOCTOR_DEFAULT_NAME
    appt_type_name = appointment.appointment_type.name if appointment.appointment_type else "Consultation"
    date_str = appointment.date.strftime("%A, %b %d, %Y")
    time_slot = appointment.time_slot
    notes = custom_notes or appointment.notes

    subject, html_content = format_email_body(
        event_type=event_type,
        booking_id=appointment.booking_id,
        patient_name=patient_name,
        doctor_name=doctor_name,
        date_str=date_str,
        time_slot=time_slot,
        appointment_type=appt_type_name,
        notes=notes
    )

    status_result = NotificationStatus.FAILED

    # Check if SMTP configuration is provided
    can_send_smtp = bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)

    if can_send_smtp:
        # Try sending via SMTP with 1 retry
        for attempt in range(2):
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
                msg["To"] = recipient_email
                msg.attach(MIMEText(html_content, "html"))

                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                    server.starttls()
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.sendmail(msg["From"], [recipient_email], msg.as_string())

                status_result = NotificationStatus.SENT
                break
            except Exception as e:
                print(f"[Email Error] Attempt {attempt + 1} failed: {e}")
                if attempt == 1:
                    status_result = NotificationStatus.FAILED
    else:
        # Development / mock fallback mode
        if settings.EMAIL_MOCK_FALLBACK:
            print(f"\n📨 [MOCK EMAIL DISPATCHED] To: {recipient_email} | Subject: {subject} | Booking: {appointment.booking_id}")
            status_result = NotificationStatus.SENT
        else:
            status_result = NotificationStatus.FAILED

    # Log into notifications_log
    log_entry = NotificationLog(
        appointment_id=appointment.id,
        recipient_email=recipient_email,
        channel=NotificationChannel.EMAIL,
        type=event_type,
        sent_at=datetime.now(timezone.utc),
        status=status_result,
        message_content=f"Subject: {subject}\nRecipient: {recipient_email}"
    )
    db.add(log_entry)
    db.commit()

    return status_result == NotificationStatus.SENT
