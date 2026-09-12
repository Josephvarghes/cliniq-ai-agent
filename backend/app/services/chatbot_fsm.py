import random
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.models import (
    Patient, Doctor, Appointment, AppointmentType, AppointmentStatus, NotificationType, Enquiry
)
from app.schemas.schemas import QuickReplyChip, ChatbotMessageResponse
from app.services.intent_matcher import detect_intent
from app.services.slot_service import get_available_slots_for_date, is_slot_available
from app.services.email_service import send_appointment_email
from app.services.auth_service import get_default_doctor

def generate_booking_id(booking_date: date) -> str:
    """Generates unique readable booking ID like APT-20260915-014."""
    date_part = booking_date.strftime("%Y%m%d")
    rand_seq = f"{random.randint(10, 999):03d}"
    return f"APT-{date_part}-{rand_seq}"

def fallback_quick_replies() -> List[QuickReplyChip]:
    return [
        QuickReplyChip(label="📅 Book Appointment", value="INTENT_BOOK"),
        QuickReplyChip(label="❌ Cancel Appointment", value="INTENT_CANCEL"),
        QuickReplyChip(label="🔄 Reschedule", value="INTENT_RESCHEDULE"),
        QuickReplyChip(label="📋 My Bookings", value="INTENT_MY_BOOKINGS"),
        QuickReplyChip(label="💬 Talk to Someone", value="INTENT_ENQUIRY")
    ]

def process_chat_turn(
    db: Session,
    patient: Patient,
    message: Optional[str] = None,
    action_value: Optional[str] = None,
    client_payload: Optional[Dict[str, Any]] = None
) -> ChatbotMessageResponse:
    """
    Main finite-state conversation engine for patient scheduling.
    """
    doctor = get_default_doctor(db)
    session_data = client_payload.copy() if client_payload else {}
    current_state = session_data.get("state", "INIT")
    user_text = (message or "").strip()

    # Direct Reset / Start Over
    if action_value in ["RESET", "START_OVER"] or user_text.lower() in ["reset", "restart", "start over", "menu"]:
        session_data = {"state": "INIT"}
        return ChatbotMessageResponse(
            reply_text=f"Welcome back, {patient.full_name}! How can I assist you with Dr. {doctor.full_name}'s clinic today?",
            action_type="buttons",
            quick_replies=fallback_quick_replies(),
            current_state="INIT",
            session_data=session_data
        )

    # If in INIT or user triggers explicit top-level intent button/text
    intent = None
    if action_value == "INTENT_BOOK":
        intent = "book_appointment"
    elif action_value == "INTENT_CANCEL":
        intent = "cancel_appointment"
    elif action_value == "INTENT_RESCHEDULE":
        intent = "reschedule_appointment"
    elif action_value == "INTENT_MY_BOOKINGS":
        intent = "check_my_bookings"
    elif action_value == "INTENT_ENQUIRY":
        intent = "general_enquiry"
    elif current_state == "INIT" and user_text:
        detected, score = detect_intent(user_text)
        if detected != "fallback":
            intent = detected

    # Route based on detected top-level intent
    if intent == "book_appointment":
        # Load appointment types
        types = db.query(AppointmentType).all()
        if not types:
            # Seed standard types if empty
            types = [
                AppointmentType(name="General Consultation", duration_minutes=30),
                AppointmentType(name="Follow-up Consultation", duration_minutes=20),
                AppointmentType(name="Comprehensive Checkup", duration_minutes=45)
            ]
            db.add_all(types)
            db.commit()

        chips = [
            QuickReplyChip(label=f"🩺 {t.name} ({t.duration_minutes}m)", value=f"SELECT_TYPE_{t.id}", payload={"type_id": t.id, "type_name": t.name})
            for t in types
        ]
        session_data = {"state": "BOOK_AWAITING_TYPE"}
        return ChatbotMessageResponse(
            reply_text=f"Let's schedule your consultation with {doctor.full_name}. Please choose your appointment type:",
            action_type="buttons",
            quick_replies=chips,
            current_state="BOOK_AWAITING_TYPE",
            session_data=session_data
        )

    elif intent == "cancel_appointment":
        active_appts = db.query(Appointment).filter(
            Appointment.patient_id == patient.id,
            Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.RESCHEDULED]),
            Appointment.date >= date.today()
        ).order_by(Appointment.date.asc()).all()

        if not active_appts:
            return ChatbotMessageResponse(
                reply_text="You do not have any upcoming confirmed appointments to cancel.",
                action_type="buttons",
                quick_replies=fallback_quick_replies(),
                current_state="INIT",
                session_data={"state": "INIT"}
            )

        chips = [
            QuickReplyChip(
                label=f"Cancel {apt.booking_id} ({apt.date.strftime('%b %d')} at {apt.time_slot})",
                value=f"SELECT_CANCEL_{apt.id}",
                payload={"appointment_id": apt.id, "booking_id": apt.booking_id}
            )
            for apt in active_appts
        ]
        chips.append(QuickReplyChip(label="Nevermind / Back", value="RESET"))
        session_data = {"state": "CANCEL_SELECT_BOOKING"}
        return ChatbotMessageResponse(
            reply_text="Please select the appointment you wish to cancel:",
            action_type="buttons",
            quick_replies=chips,
            current_state="CANCEL_SELECT_BOOKING",
            session_data=session_data
        )

    elif intent == "reschedule_appointment":
        active_appts = db.query(Appointment).filter(
            Appointment.patient_id == patient.id,
            Appointment.status.in_([AppointmentStatus.BOOKED, AppointmentStatus.RESCHEDULED]),
            Appointment.date >= date.today()
        ).order_by(Appointment.date.asc()).all()

        if not active_appts:
            return ChatbotMessageResponse(
                reply_text="You do not have any upcoming appointments to reschedule. Would you like to book a new appointment?",
                action_type="buttons",
                quick_replies=[
                    QuickReplyChip(label="📅 Book New Appointment", value="INTENT_BOOK"),
                    QuickReplyChip(label="🔙 Main Menu", value="RESET")
                ],
                current_state="INIT",
                session_data={"state": "INIT"}
            )

        chips = [
            QuickReplyChip(
                label=f"Reschedule {apt.booking_id} ({apt.date.strftime('%b %d')}, {apt.time_slot})",
                value=f"SELECT_RESCHEDULE_{apt.id}",
                payload={"appointment_id": apt.id, "booking_id": apt.booking_id}
            )
            for apt in active_appts
        ]
        chips.append(QuickReplyChip(label="Nevermind / Back", value="RESET"))
        session_data = {"state": "RESCHEDULE_SELECT_BOOKING"}
        return ChatbotMessageResponse(
            reply_text="Which appointment would you like to reschedule?",
            action_type="buttons",
            quick_replies=chips,
            current_state="RESCHEDULE_SELECT_BOOKING",
            session_data=session_data
        )

    elif intent == "check_my_bookings":
        active_appts = db.query(Appointment).filter(
            Appointment.patient_id == patient.id,
            Appointment.date >= date.today()
        ).order_by(Appointment.date.asc()).all()

        if not active_appts:
            summary = "You currently have no upcoming appointments."
        else:
            summary = "Here are your upcoming appointments:\n\n"
            for apt in active_appts:
                type_name = apt.appointment_type.name if apt.appointment_type else "Consultation"
                summary += f"• **{apt.booking_id}**: {type_name} on {apt.date.strftime('%A, %b %d')} at {apt.time_slot} ({apt.status.value.upper()})\n"

        return ChatbotMessageResponse(
            reply_text=summary,
            action_type="buttons",
            quick_replies=[
                QuickReplyChip(label="📅 Book Another", value="INTENT_BOOK"),
                QuickReplyChip(label="📋 View All in My Bookings", value="REDIRECT_BOOKINGS"),
                QuickReplyChip(label="🔙 Main Menu", value="RESET")
            ],
            current_state="INIT",
            session_data={"state": "INIT"}
        )

    elif intent == "general_enquiry":
        session_data = {"state": "AWAITING_ENQUIRY_TEXT"}
        return ChatbotMessageResponse(
            reply_text="Please type your medical question or message below. Our clinic front desk will review it promptly:",
            action_type="text",
            quick_replies=[QuickReplyChip(label="Cancel / Back", value="RESET")],
            current_state="AWAITING_ENQUIRY_TEXT",
            session_data=session_data
        )

    # -------------------------------------------------------------
    # State-based Handlers (Booking, Cancellation, Reschedule)
    # -------------------------------------------------------------

    # 1. BOOKING: AWAITING TYPE
    if current_state == "BOOK_AWAITING_TYPE":
        type_id = None
        type_name = None
        if action_value and action_value.startswith("SELECT_TYPE_"):
            try:
                type_id = int(action_value.split("SELECT_TYPE_")[1])
                appt_type = db.query(AppointmentType).filter(AppointmentType.id == type_id).first()
                if appt_type:
                    type_name = appt_type.name
            except ValueError:
                pass
        elif user_text:
            # Match text to appointment type
            appt_type = db.query(AppointmentType).filter(AppointmentType.name.ilike(f"%{user_text}%")).first()
            if appt_type:
                type_id = appt_type.id
                type_name = appt_type.name

        if not type_id:
            # Re-prompt
            types = db.query(AppointmentType).all()
            chips = [QuickReplyChip(label=f"🩺 {t.name}", value=f"SELECT_TYPE_{t.id}") for t in types]
            return ChatbotMessageResponse(
                reply_text="Please select one of the available appointment types below:",
                action_type="buttons",
                quick_replies=chips,
                current_state="BOOK_AWAITING_TYPE",
                session_data=session_data
            )

        session_data["appointment_type_id"] = type_id
        session_data["appointment_type_name"] = type_name
        session_data["state"] = "BOOK_AWAITING_DATE"

        # Date suggestions: Tomorrow, Day after tomorrow, or Date Picker
        tomorrow = date.today() + timedelta(days=1)
        day_after = date.today() + timedelta(days=2)
        quick_dates = [
            QuickReplyChip(label=f"Today ({date.today().strftime('%b %d')})", value=f"DATE_{date.today().isoformat()}"),
            QuickReplyChip(label=f"Tomorrow ({tomorrow.strftime('%b %d')})", value=f"DATE_{tomorrow.isoformat()}"),
            QuickReplyChip(label=f"{day_after.strftime('%A (%b %d)')}", value=f"DATE_{day_after.isoformat()}"),
            QuickReplyChip(label="Cancel", value="RESET")
        ]

        return ChatbotMessageResponse(
            reply_text=f"Selected: **{type_name}**.\n\nPlease pick your preferred consultation date using the calendar or quick options below:",
            action_type="date_picker",
            quick_replies=quick_dates,
            current_state="BOOK_AWAITING_DATE",
            session_data=session_data
        )

    # 2. BOOKING: AWAITING DATE
    elif current_state == "BOOK_AWAITING_DATE":
        selected_date_str = None
        if action_value and action_value.startswith("DATE_"):
            selected_date_str = action_value.split("DATE_")[1]
        elif user_text:
            # Try parsing date strings
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
                try:
                    parsed_d = datetime.strptime(user_text, fmt).date()
                    selected_date_str = parsed_d.isoformat()
                    break
                except ValueError:
                    pass

        if not selected_date_str:
            return ChatbotMessageResponse(
                reply_text="Please select or enter a valid date (YYYY-MM-DD):",
                action_type="date_picker",
                quick_replies=[QuickReplyChip(label="Cancel", value="RESET")],
                current_state="BOOK_AWAITING_DATE",
                session_data=session_data
            )

        chosen_date = date.fromisoformat(selected_date_str)
        if chosen_date < date.today():
            return ChatbotMessageResponse(
                reply_text="Appointments cannot be scheduled in the past. Please pick today or a future date:",
                action_type="date_picker",
                quick_replies=[QuickReplyChip(label="Cancel", value="RESET")],
                current_state="BOOK_AWAITING_DATE",
                session_data=session_data
            )

        # Get open slots
        open_slots = get_available_slots_for_date(db, chosen_date, doctor.id)
        if not open_slots:
            return ChatbotMessageResponse(
                reply_text=f"No consultation slots are available on {chosen_date.strftime('%A, %b %d, %Y')}. Please choose another date:",
                action_type="date_picker",
                quick_replies=[
                    QuickReplyChip(label="Tomorrow", value=f"DATE_{(chosen_date + timedelta(days=1)).isoformat()}"),
                    QuickReplyChip(label="Cancel", value="RESET")
                ],
                current_state="BOOK_AWAITING_DATE",
                session_data=session_data
            )

        session_data["booking_date"] = chosen_date.isoformat()
        session_data["state"] = "BOOK_AWAITING_SLOT"

        slot_chips = [
            QuickReplyChip(label=f"⏰ {slot}", value=f"SLOT_{slot}", payload={"slot": slot})
            for slot in open_slots
        ]
        slot_chips.append(QuickReplyChip(label="Change Date", value="CHANGE_DATE"))
        slot_chips.append(QuickReplyChip(label="Cancel", value="RESET"))

        return ChatbotMessageResponse(
            reply_text=f"Available slots for **{chosen_date.strftime('%A, %b %d, %Y')}** with {doctor.full_name}:",
            action_type="slot_picker",
            quick_replies=slot_chips,
            current_state="BOOK_AWAITING_SLOT",
            session_data=session_data
        )

    # 3. BOOKING: AWAITING SLOT
    elif current_state == "BOOK_AWAITING_SLOT":
        if action_value == "CHANGE_DATE":
            session_data["state"] = "BOOK_AWAITING_DATE"
            return ChatbotMessageResponse(
                reply_text="Please select another date:",
                action_type="date_picker",
                quick_replies=[QuickReplyChip(label="Cancel", value="RESET")],
                current_state="BOOK_AWAITING_DATE",
                session_data=session_data
            )

        chosen_slot = None
        if action_value and action_value.startswith("SLOT_"):
            chosen_slot = action_value.split("SLOT_")[1]
        elif user_text:
            chosen_slot = user_text.strip()

        chosen_date = date.fromisoformat(session_data.get("booking_date"))
        if not chosen_slot or not is_slot_available(db, chosen_date, chosen_slot, doctor.id):
            open_slots = get_available_slots_for_date(db, chosen_date, doctor.id)
            slot_chips = [QuickReplyChip(label=f"⏰ {s}", value=f"SLOT_{s}") for s in open_slots]
            return ChatbotMessageResponse(
                reply_text=f"The slot '{chosen_slot}' is either invalid or was just taken. Please pick one of the available slots:",
                action_type="slot_picker",
                quick_replies=slot_chips,
                current_state="BOOK_AWAITING_SLOT",
                session_data=session_data
            )

        session_data["time_slot"] = chosen_slot
        session_data["state"] = "BOOK_AWAITING_NOTES"

        return ChatbotMessageResponse(
            reply_text=f"Slot selected: **{chosen_slot}**.\n\nWould you like to provide any brief notes or reason for visit? (Optional)",
            action_type="text",
            quick_replies=[
                QuickReplyChip(label="➡️ Skip / No Notes", value="SKIP_NOTES"),
                QuickReplyChip(label="Cancel", value="RESET")
            ],
            current_state="BOOK_AWAITING_NOTES",
            session_data=session_data
        )

    # 4. BOOKING: AWAITING NOTES
    elif current_state == "BOOK_AWAITING_NOTES":
        notes = None
        if action_value != "SKIP_NOTES" and user_text:
            notes = user_text.strip()

        session_data["notes"] = notes
        session_data["state"] = "BOOK_AWAITING_CONFIRM"

        type_name = session_data.get("appointment_type_name")
        b_date = date.fromisoformat(session_data.get("booking_date"))
        t_slot = session_data.get("time_slot")

        summary_text = (
            f"📋 **Please confirm your consultation details:**\n\n"
            f"• **Doctor:** {doctor.full_name} ({doctor.specialization})\n"
            f"• **Type:** {type_name}\n"
            f"• **Date:** {b_date.strftime('%A, %b %d, %Y')}\n"
            f"• **Time:** {t_slot}\n"
            f"• **Patient:** {patient.full_name} ({patient.phone_number})\n"
            + (f"• **Notes:** {notes}\n" if notes else "")
        )

        return ChatbotMessageResponse(
            reply_text=summary_text,
            action_type="confirm",
            quick_replies=[
                QuickReplyChip(label="✅ Confirm Booking", value="CONFIRM_BOOKING_YES"),
                QuickReplyChip(label="❌ Cancel / Start Over", value="RESET")
            ],
            current_state="BOOK_AWAITING_CONFIRM",
            session_data=session_data
        )

    # 5. BOOKING: AWAITING CONFIRMATION
    elif current_state == "BOOK_AWAITING_CONFIRM":
        if action_value == "CONFIRM_BOOKING_YES" or user_text.lower() in ["yes", "y", "confirm"]:
            b_date = date.fromisoformat(session_data.get("booking_date"))
            t_slot = session_data.get("time_slot")
            type_id = session_data.get("appointment_type_id")
            notes = session_data.get("notes")

            # Final check against concurrent double-booking
            if not is_slot_available(db, b_date, t_slot, doctor.id):
                session_data["state"] = "BOOK_AWAITING_DATE"
                return ChatbotMessageResponse(
                    reply_text="Sorry! This slot was just reserved by another patient. Please choose another date or slot:",
                    action_type="date_picker",
                    quick_replies=[QuickReplyChip(label="Cancel", value="RESET")],
                    current_state="BOOK_AWAITING_DATE",
                    session_data=session_data
                )

            booking_code = generate_booking_id(b_date)
            new_appointment = Appointment(
                booking_id=booking_code,
                patient_id=patient.id,
                doctor_id=doctor.id,
                appointment_type_id=type_id,
                date=b_date,
                time_slot=t_slot,
                status=AppointmentStatus.BOOKED,
                notes=notes
            )
            db.add(new_appointment)
            db.commit()
            db.refresh(new_appointment)

            # Trigger email notification
            send_appointment_email(db, new_appointment, NotificationType.BOOKING_CONFIRMATION)

            type_name = session_data.get("appointment_type_name")
            success_msg = (
                f"🎉 **Your appointment is confirmed!**\n\n"
                f"• **Booking ID:** `{booking_code}`\n"
                f"• **Doctor:** {doctor.full_name}\n"
                f"• **Type:** {type_name}\n"
                f"• **Date:** {b_date.strftime('%A, %b %d, %Y')}\n"
                f"• **Time:** {t_slot}\n\n"
                f"A confirmation email has been dispatched to `{patient.email}`."
            )

            booking_summary = {
                "booking_id": booking_code,
                "status": "booked",
                "date": b_date.isoformat(),
                "time": t_slot,
                "type": type_name
            }

            return ChatbotMessageResponse(
                reply_text=success_msg,
                action_type="completed",
                quick_replies=[
                    QuickReplyChip(label="📋 View in My Bookings", value="REDIRECT_BOOKINGS"),
                    QuickReplyChip(label="📅 Book Another", value="INTENT_BOOK"),
                    QuickReplyChip(label="🏠 Back to Start", value="RESET")
                ],
                current_state="INIT",
                session_data={"state": "INIT"},
                booking_summary=booking_summary
            )
        else:
            return ChatbotMessageResponse(
                reply_text="Booking was cancelled. What else can I assist you with?",
                action_type="buttons",
                quick_replies=fallback_quick_replies(),
                current_state="INIT",
                session_data={"state": "INIT"}
            )

    # 6. CANCELLATION FLOW
    elif current_state == "CANCEL_SELECT_BOOKING":
        target_appt_id = None
        if action_value and action_value.startswith("SELECT_CANCEL_"):
            try:
                target_appt_id = int(action_value.split("SELECT_CANCEL_")[1])
            except ValueError:
                pass
        elif user_text:
            appt = db.query(Appointment).filter(
                Appointment.patient_id == patient.id,
                Appointment.booking_id.ilike(user_text.strip())
            ).first()
            if appt:
                target_appt_id = appt.id

        if not target_appt_id:
            return ChatbotMessageResponse(
                reply_text="Could not locate that booking. Please select an active appointment to cancel:",
                action_type="buttons",
                quick_replies=fallback_quick_replies(),
                current_state="INIT",
                session_data={"state": "INIT"}
            )

        appt = db.query(Appointment).filter(Appointment.id == target_appt_id).first()
        session_data["target_appointment_id"] = target_appt_id
        session_data["booking_id"] = appt.booking_id
        session_data["state"] = "CANCEL_CONFIRM"

        type_name = appt.appointment_type.name if appt.appointment_type else "Consultation"
        return ChatbotMessageResponse(
            reply_text=(
                f"Are you sure you want to cancel booking **{appt.booking_id}** "
                f"({type_name} on {appt.date.strftime('%b %d, %Y')} at {appt.time_slot})?"
            ),
            action_type="confirm",
            quick_replies=[
                QuickReplyChip(label="⚠️ Yes, Cancel Booking", value="CONFIRM_CANCEL_YES"),
                QuickReplyChip(label="Keep Appointment", value="RESET")
            ],
            current_state="CANCEL_CONFIRM",
            session_data=session_data
        )

    elif current_state == "CANCEL_CONFIRM":
        if action_value == "CONFIRM_CANCEL_YES" or user_text.lower() in ["yes", "y", "cancel"]:
            appt_id = session_data.get("target_appointment_id")
            appt = db.query(Appointment).filter(Appointment.id == appt_id).first()
            if appt:
                appt.status = AppointmentStatus.CANCELLED
                db.commit()
                # Send cancellation email
                send_appointment_email(db, appt, NotificationType.CANCELLATION)

                return ChatbotMessageResponse(
                    reply_text=f"Appointment `{appt.booking_id}` has been cancelled, and the time slot has been freed. A cancellation confirmation has been emailed to you.",
                    action_type="buttons",
                    quick_replies=[
                        QuickReplyChip(label="📅 Book New Appointment", value="INTENT_BOOK"),
                        QuickReplyChip(label="📋 My Bookings", value="REDIRECT_BOOKINGS"),
                        QuickReplyChip(label="🏠 Main Menu", value="RESET")
                    ],
                    current_state="INIT",
                    session_data={"state": "INIT"},
                    booking_summary={"booking_id": appt.booking_id, "status": "cancelled"}
                )

        return ChatbotMessageResponse(
            reply_text="Cancellation was stopped. Your appointment remains safely scheduled.",
            action_type="buttons",
            quick_replies=fallback_quick_replies(),
            current_state="INIT",
            session_data={"state": "INIT"}
        )

    # 7. RESCHEDULE FLOW
    elif current_state == "RESCHEDULE_SELECT_BOOKING":
        target_appt_id = None
        if action_value and action_value.startswith("SELECT_RESCHEDULE_"):
            try:
                target_appt_id = int(action_value.split("SELECT_RESCHEDULE_")[1])
            except ValueError:
                pass

        if not target_appt_id:
            return ChatbotMessageResponse(
                reply_text="Please select the appointment you would like to reschedule:",
                action_type="buttons",
                quick_replies=fallback_quick_replies(),
                current_state="INIT",
                session_data={"state": "INIT"}
            )

        appt = db.query(Appointment).filter(Appointment.id == target_appt_id).first()
        session_data["target_appointment_id"] = target_appt_id
        session_data["booking_id"] = appt.booking_id
        session_data["state"] = "RESCHEDULE_AWAITING_DATE"

        tomorrow = date.today() + timedelta(days=1)
        quick_dates = [
            QuickReplyChip(label=f"Tomorrow ({tomorrow.strftime('%b %d')})", value=f"RESCHED_DATE_{tomorrow.isoformat()}"),
            QuickReplyChip(label=f"Next Week ({(date.today() + timedelta(days=7)).strftime('%b %d')})", value=f"RESCHED_DATE_{(date.today() + timedelta(days=7)).isoformat()}"),
            QuickReplyChip(label="Cancel", value="RESET")
        ]

        return ChatbotMessageResponse(
            reply_text=f"Rescheduling booking **{appt.booking_id}**.\nPlease select your new desired consultation date:",
            action_type="date_picker",
            quick_replies=quick_dates,
            current_state="RESCHEDULE_AWAITING_DATE",
            session_data=session_data
        )

    elif current_state == "RESCHEDULE_AWAITING_DATE":
        new_date_str = None
        if action_value and (action_value.startswith("RESCHED_DATE_") or action_value.startswith("DATE_")):
            new_date_str = action_value.split("_")[-1]
        elif user_text:
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
                try:
                    new_date_str = datetime.strptime(user_text, fmt).date().isoformat()
                    break
                except ValueError:
                    pass

        if not new_date_str:
            return ChatbotMessageResponse(
                reply_text="Please choose a valid new date:",
                action_type="date_picker",
                quick_replies=[QuickReplyChip(label="Cancel", value="RESET")],
                current_state="RESCHEDULE_AWAITING_DATE",
                session_data=session_data
            )

        new_date = date.fromisoformat(new_date_str)
        open_slots = get_available_slots_for_date(db, new_date, doctor.id)
        if not open_slots:
            return ChatbotMessageResponse(
                reply_text=f"No slots are open on {new_date.strftime('%A, %b %d')}. Please choose another date:",
                action_type="date_picker",
                quick_replies=[QuickReplyChip(label="Cancel", value="RESET")],
                current_state="RESCHEDULE_AWAITING_DATE",
                session_data=session_data
            )

        session_data["new_date"] = new_date_str
        session_data["state"] = "RESCHEDULE_AWAITING_SLOT"

        slot_chips = [
            QuickReplyChip(label=f"⏰ {s}", value=f"RESCHED_SLOT_{s}") for s in open_slots
        ]
        slot_chips.append(QuickReplyChip(label="Pick Another Date", value="RESCHEDULE_CHANGE_DATE"))
        slot_chips.append(QuickReplyChip(label="Cancel", value="RESET"))

        return ChatbotMessageResponse(
            reply_text=f"Available slots on **{new_date.strftime('%A, %b %d, %Y')}**:",
            action_type="slot_picker",
            quick_replies=slot_chips,
            current_state="RESCHEDULE_AWAITING_SLOT",
            session_data=session_data
        )

    elif current_state == "RESCHEDULE_AWAITING_SLOT":
        if action_value == "RESCHEDULE_CHANGE_DATE":
            session_data["state"] = "RESCHEDULE_AWAITING_DATE"
            return ChatbotMessageResponse(
                reply_text="Please pick another date:",
                action_type="date_picker",
                quick_replies=[QuickReplyChip(label="Cancel", value="RESET")],
                current_state="RESCHEDULE_AWAITING_DATE",
                session_data=session_data
            )

        new_slot = None
        if action_value and action_value.startswith("RESCHED_SLOT_"):
            new_slot = action_value.split("RESCHED_SLOT_")[1]
        elif user_text:
            new_slot = user_text.strip()

        target_appt_id = session_data.get("target_appointment_id")
        new_d = date.fromisoformat(session_data.get("new_date"))

        if not new_slot or not is_slot_available(db, new_d, new_slot, doctor.id, exclude_appointment_id=target_appt_id):
            return ChatbotMessageResponse(
                reply_text="That time slot is not available. Please choose another slot:",
                action_type="slot_picker",
                quick_replies=[QuickReplyChip(label="Cancel", value="RESET")],
                current_state="RESCHEDULE_AWAITING_SLOT",
                session_data=session_data
            )

        session_data["new_slot"] = new_slot
        session_data["state"] = "RESCHEDULE_CONFIRM"

        return ChatbotMessageResponse(
            reply_text=(
                f"Please confirm: Reschedule booking `{session_data.get('booking_id')}` "
                f"to **{new_d.strftime('%A, %b %d, %Y')}** at **{new_slot}**?"
            ),
            action_type="confirm",
            quick_replies=[
                QuickReplyChip(label="✅ Yes, Reschedule", value="CONFIRM_RESCHEDULE_YES"),
                QuickReplyChip(label="❌ No, Keep Original", value="RESET")
            ],
            current_state="RESCHEDULE_CONFIRM",
            session_data=session_data
        )

    elif current_state == "RESCHEDULE_CONFIRM":
        if action_value == "CONFIRM_RESCHEDULE_YES" or user_text.lower() in ["yes", "y"]:
            target_appt_id = session_data.get("target_appointment_id")
            new_d = date.fromisoformat(session_data.get("new_date"))
            new_slot = session_data.get("new_slot")

            appt = db.query(Appointment).filter(Appointment.id == target_appt_id).first()
            if appt:
                appt.date = new_d
                appt.time_slot = new_slot
                appt.status = AppointmentStatus.RESCHEDULED
                db.commit()
                db.refresh(appt)

                # Send reschedule email
                send_appointment_email(db, appt, NotificationType.RESCHEDULE)

                return ChatbotMessageResponse(
                    reply_text=(
                        f"🔄 **Appointment Rescheduled!**\n\n"
                        f"• **Booking ID:** `{appt.booking_id}`\n"
                        f"• **New Date:** {new_d.strftime('%A, %b %d, %Y')}\n"
                        f"• **New Time:** {new_slot}\n\n"
                        f"A confirmation email has been sent to `{patient.email}`."
                    ),
                    action_type="completed",
                    quick_replies=[
                        QuickReplyChip(label="📋 My Bookings", value="REDIRECT_BOOKINGS"),
                        QuickReplyChip(label="🏠 Main Menu", value="RESET")
                    ],
                    current_state="INIT",
                    session_data={"state": "INIT"},
                    booking_summary={
                        "booking_id": appt.booking_id,
                        "status": "rescheduled",
                        "date": new_d.isoformat(),
                        "time": new_slot
                    }
                )

        return ChatbotMessageResponse(
            reply_text="Reschedule cancelled. Your appointment schedule remains intact.",
            action_type="buttons",
            quick_replies=fallback_quick_replies(),
            current_state="INIT",
            session_data={"state": "INIT"}
        )

    # 8. GENERAL ENQUIRY INPUT
    elif current_state == "AWAITING_ENQUIRY_TEXT":
        if user_text:
            enquiry = Enquiry(
                patient_id=patient.id,
                patient_name=patient.full_name,
                patient_phone=patient.phone_number,
                message=user_text,
                status="unread"
            )
            db.add(enquiry)
            db.commit()

            return ChatbotMessageResponse(
                reply_text="📬 Thank you! Your enquiry has been routed directly to Dr. Varghese's clinic front desk. We will review and get in touch with you shortly.",
                action_type="buttons",
                quick_replies=fallback_quick_replies(),
                current_state="INIT",
                session_data={"state": "INIT"}
            )

    # Fallback default response
    return ChatbotMessageResponse(
        reply_text="I didn't quite catch that. How can I assist you with your appointment today?",
        action_type="buttons",
        quick_replies=fallback_quick_replies(),
        current_state="INIT",
        session_data={"state": "INIT"}
    )
