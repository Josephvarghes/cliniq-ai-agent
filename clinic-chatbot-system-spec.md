# Project Spec: Clinic Appointment Booking System (Chatbot-driven)

> **Instructions for the coding agent:** Build this as a full-stack application. Follow the tech stack exactly. The chatbot is a **rule-based / decision-tree bot — NOT an LLM**. Do not integrate any LLM API. Natural language handling should be done via simple intent matching (keywords, regex, or a small NLU library like `rasa`-lite patterns or `spaCy`/`rapidfuzz` for fuzzy matching) plus structured button/quick-reply options for anything ambiguous. Implement in phases as listed at the end of this document, and confirm each phase before moving to the next.
>
> **Current scope: SINGLE DOCTOR.** There is only one doctor in the system for now. Do not build a doctor-selection step in the chatbot or a doctor list/switcher anywhere in the UI. Keep `doctor_id` as a foreign key in the schema (for future multi-doctor scalability), but treat it as a fixed/implicit value everywhere — e.g., resolve it once from the single row in the `doctors` table (or a config/env value) rather than asking the patient to choose. All availability, schedule, dashboard, and insights logic is scoped to this one doctor only.

---

## 1. Tech Stack (mandatory)

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI |
| Database | Supabase (PostgreSQL) |
| ORM | SQLAlchemy |
| Frontend | ReactJS |
| Email | Any free provider (e.g., SMTP via Gmail App Password, or SendGrid free tier) |
| Auth | Custom — phone number + password (JWT-based sessions) |

---

## 2. User Roles

1. **Patient** — interacts only through: Login screen → Chatbot screen → My Bookings screen. No other UI surfaces.
2. **Doctor** — CRM-style dashboard: Login → Dashboard → Schedule management → Bookings/Enquiries → Insights.

---

## 3. Database Schema (Supabase/Postgres via SQLAlchemy models)

```
patients
  id (PK, uuid)
  full_name
  phone_number (unique, used for login)
  password_hash
  email
  created_at

doctors
  id (PK, uuid)
  full_name
  phone_number (unique, used for login)
  password_hash
  email
  specialization
  created_at

doctor_availability
  id (PK)
  doctor_id (FK -> doctors)
  date
  start_time
  end_time
  slot_duration_minutes
  is_blocked (bool)  -- for emergency blocking

appointment_types
  id (PK)
  name (e.g., "General Consultation", "Follow-up")
  duration_minutes

appointments
  id (PK)
  booking_id (human-readable unique code, e.g., APT-20260912-001)
  patient_id (FK -> patients)
  doctor_id (FK -> doctors)
  appointment_type_id (FK -> appointment_types)
  date
  time_slot
  status (enum: booked, cancelled, rescheduled, completed)
  notes
  created_at
  updated_at

notifications_log
  id (PK)
  appointment_id (FK -> appointments)
  channel (email)
  type (booking_confirmation, cancellation, reschedule, reminder, emergency_notice)
  sent_at
  status (sent/failed)
```

---

## 4. Patient Module

### 4.1 Authentication
- Signup/Login via **phone number + password**.
- JWT token issued on login, stored client-side, used for all chatbot/API calls.

### 4.2 Chatbot (rule-based, no LLM)
Implement as a finite-state conversation engine. Each state maps to expected inputs (free text OR button click).

**Core intents to detect:**
- `book_appointment`
- `cancel_appointment`
- `reschedule_appointment`
- `check_my_bookings`
- `general_enquiry` (fallback → route to doctor's enquiry inbox)

**Interaction pattern:**
- Free-text natural language input is matched against intent keywords (e.g., "cancel", "reschedule", "book", "change my appointment").
- Whenever a decision point has limited valid answers, chatbot renders **quick-reply buttons** (e.g., YES/NO, list of available time slots, list of appointment types) instead of expecting free text.
- If bot cannot confidently match intent → show fallback buttons: `[Book] [Cancel] [Reschedule] [My Bookings] [Talk to someone]`.

**Data to collect during booking flow (single-doctor mode — no doctor-selection step):**
1. Appointment type (button list)
2. Preferred date (calendar picker widget inside chat)
3. Available time slot (buttons, generated from `doctor_availability` minus already-booked slots, for the one doctor)
4. Reason/notes (free text, optional)
5. Confirmation step → YES/NO buttons

All collected fields are persisted to the `appointments` table tied to `patient_id`.

### 4.3 Cancellation Flow
1. Patient says "cancel my appointment" (or clicks Cancel button).
2. Bot asks for `booking_id` (or shows list of patient's upcoming bookings as buttons to pick from — preferred over asking user to type it).
3. Bot shows booking details → asks YES/NO to confirm cancellation.
4. On YES: update `status = cancelled`, free up the slot in `doctor_availability`, send cancellation email, log in `notifications_log`.

### 4.4 Reschedule Flow
1. Patient says "reschedule" or clicks Reschedule button.
2. Bot shows the patient's upcoming bookings as selectable buttons.
3. Bot shows new available dates/slots (for the single doctor).
4. Confirm via YES/NO.
5. On YES: mark old appointment `status = rescheduled`, create new appointment row (or update date/time in place — choose one convention, log clearly), send updated confirmation email.

### 4.5 My Bookings Page
- Simple list/table view (not chatbot) showing: booking_id, doctor, date, time, type, status.
- Filter by status (upcoming/past/cancelled).

---

## 5. Doctor Module (CRM-style)

### 5.1 Authentication
- Phone number + password, JWT-based, same pattern as patient.

### 5.2 Dashboard
- Today's bookings list.
- Upcoming bookings (next 7 days).
- Patient enquiries (from chatbot fallback intent).

### 5.3 Schedule Management
- Doctor sets/edits availability: date + start time + end time + slot duration.
- Doctor can block specific slots/dates (emergency) → triggers **automatic notification email to affected patients** asking them to cancel/reschedule, with a link/reference back to the chatbot.
- Schedule lookup/reminder table view (calendar or table format).

### 5.4 Insights Dashboard
Minimum metrics:
- Total patients seen (monthly/weekly/custom range)
- Total bookings vs cancellations vs no-shows
- Busiest days/time slots
- New vs returning patients count
- Simple text summary (rule-based, e.g., "You had 32 appointments this month, 12% more than last month, with Mondays being your busiest day.") — **not LLM-generated, computed from aggregated SQL queries and templated sentences.**

### 5.5 Notifications
- Reminder email to patient before next appointment (e.g., 24 hours prior — implement via a scheduled job/cron, e.g. APScheduler or Supabase scheduled functions).
- Emergency cancellation broadcast email when doctor blocks a slot.

---

## 6. Email Notifications (triggers)

| Event | Recipient | Trigger |
|---|---|---|
| Booking confirmed | Patient | On successful booking |
| Cancellation confirmed | Patient | On cancellation |
| Reschedule confirmed | Patient | On reschedule |
| Appointment reminder | Patient | Scheduled job, X hours before appointment |
| Emergency slot blocked | Patient(s) affected | When doctor blocks a date/slot with existing bookings |

Each email should include: booking_id, patient name, doctor name, date, time, appointment type, and a short action note if applicable.

---

## 7. Suggested API Endpoints (FastAPI)

```
POST   /auth/patient/signup
POST   /auth/patient/login
POST   /auth/doctor/login

POST   /chatbot/message           -> handles all conversational turns (intent detection + state machine)
GET    /chatbot/availability?date=          -> availability for the single doctor (no doctor_id needed in request)

GET    /patients/{id}/bookings
POST   /appointments/book
POST   /appointments/{id}/cancel
POST   /appointments/{id}/reschedule

GET    /doctors/{id}/dashboard
GET    /doctors/{id}/schedule
POST   /doctors/{id}/schedule
POST   /doctors/{id}/schedule/block   -> emergency block + trigger notifications

GET    /doctors/{id}/insights?range=monthly
```

---

## 8. Example End-to-End Flow (for the agent to test against)

**Scenario: Book → Cancel next day**

1. `POST /auth/patient/login` with `{ "phone_number": "9876543210", "password": "pass123" }` → returns JWT.
2. Chatbot: patient types "I want to book an appointment" →
   Bot responds with buttons: `[General Consultation] [Follow-up]`.
3. Patient clicks "General Consultation" → bot shows date picker → patient picks `2026-09-15`.
4. Bot shows available slots: `[10:00 AM] [11:30 AM] [3:00 PM]` → patient picks `11:30 AM`.
5. Bot: "Confirm booking for General Consultation on 2026-09-15 at 11:30 AM? [YES] [NO]" → patient clicks YES.
6. System creates appointment `booking_id = APT-20260915-014`, sends confirmation email.
   **Expected response:**
   ```json
   {
     "booking_id": "APT-20260915-014",
     "status": "booked",
     "date": "2026-09-15",
     "time": "11:30",
     "type": "General Consultation"
   }
   ```
7. Next day, patient opens chatbot: "cancel my appointment" → bot shows `[APT-20260915-014 - Sep 15, 11:30 AM]` as a button.
8. Patient clicks it → bot: "Cancel this booking? [YES] [NO]" → YES.
9. System sets `status = cancelled`, frees the slot, sends cancellation email.
   **Expected response:**
   ```json
   { "booking_id": "APT-20260915-014", "status": "cancelled" }
   ```

---

## 9. Non-Functional Requirements

- Passwords stored hashed (bcrypt/argon2), never plain text.
- JWT expiry + refresh token handling.
- Input validation on all chatbot-collected fields (Pydantic schemas).
- Slot double-booking prevention (DB-level unique constraint or transaction lock on doctor_id + date + time_slot).
- All email sends should be logged and retried once on failure.

---

## 10. Suggested Build Phases (do these in order, confirm each with the user before proceeding)

1. **Phase 1:** DB schema + SQLAlchemy models + Supabase connection + auth (patient & doctor).
2. **Phase 2:** Doctor schedule management (create/view/block availability).
3. **Phase 3:** Chatbot state machine + booking flow (no email yet).
4. **Phase 4:** Cancellation + reschedule flows.
5. **Phase 5:** Email integration for all triggers.
6. **Phase 6:** My Bookings page (patient) + Doctor dashboard & bookings/enquiries view.
7. **Phase 7:** Insights dashboard with aggregated metrics.
8. **Phase 8:** Emergency slot blocking + patient notification broadcast.
9. **Phase 9:** Polish — reminder cron job, error handling, edge cases (double-booking, expired slots, timezone handling).

---

### Note on scope control
Do not add features beyond what's listed here (e.g., no payment integration, no video consultation, no multi-language support) unless explicitly requested in a future prompt.