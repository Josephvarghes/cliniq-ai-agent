import os
import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient

# Ensure test DB is isolated
os.environ["DATABASE_URL"] = "sqlite:///./test_clinic.db"
os.environ["EMAIL_MOCK_FALLBACK"] = "True"

from app.main import app
from app.seed import init_db_and_seed
from app.core.database import Base, engine

client = TestClient(app)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    init_db_and_seed()
    yield
    # Cleanup test DB if needed

def test_health_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_doctor_login():
    res = client.post("/auth/doctor/login", json={
        "phone_number": "9876543210",
        "password": "doctor123"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "doctor"
    assert data["user"]["phone_number"] == "9876543210"

def test_patient_signup_and_login():
    phone = "9112233445"
    # Signup
    signup_res = client.post("/auth/patient/signup", json={
        "full_name": "Test Patient",
        "phone_number": phone,
        "password": "patient_pass_123",
        "email": "testpatient@example.com"
    })
    assert signup_res.status_code == 200
    signup_data = signup_res.json()
    assert "access_token" in signup_data
    assert signup_data["role"] == "patient"

    # Login
    login_res = client.post("/auth/patient/login", json={
        "phone_number": phone,
        "password": "patient_pass_123"
    })
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()

def test_chatbot_booking_flow_end_to_end():
    # 1. Login patient
    login_res = client.post("/auth/patient/login", json={
        "phone_number": "9112233445",
        "password": "patient_pass_123"
    })
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Start conversation with intent: "I want to book an appointment"
    msg1 = client.post("/chatbot/message", json={
        "message": "I want to book an appointment"
    }, headers=headers)
    assert msg1.status_code == 200
    data1 = msg1.json()
    assert data1["current_state"] == "BOOK_AWAITING_TYPE"
    assert len(data1["quick_replies"]) > 0

    # Pick first appointment type
    first_type_chip = data1["quick_replies"][0]
    session_data = data1["session_data"]

    # 3. Choose type
    msg2 = client.post("/chatbot/message", json={
        "action_value": first_type_chip["value"],
        "payload": session_data
    }, headers=headers)
    assert msg2.status_code == 200
    data2 = msg2.json()
    assert data2["current_state"] == "BOOK_AWAITING_DATE"

    # Pick tomorrow's date
    tomorrow = (date.today() + timedelta(days=2)).isoformat()
    session_data = data2["session_data"]

    # 4. Choose date
    msg3 = client.post("/chatbot/message", json={
        "action_value": f"DATE_{tomorrow}",
        "payload": session_data
    }, headers=headers)
    assert msg3.status_code == 200
    data3 = msg3.json()
    assert data3["current_state"] == "BOOK_AWAITING_SLOT"
    assert len(data3["quick_replies"]) > 0

    # Pick first slot
    slot_chip = [c for c in data3["quick_replies"] if c["value"].startswith("SLOT_")][0]
    session_data = data3["session_data"]

    # 5. Choose slot
    msg4 = client.post("/chatbot/message", json={
        "action_value": slot_chip["value"],
        "payload": session_data
    }, headers=headers)
    assert msg4.status_code == 200
    data4 = msg4.json()
    assert data4["current_state"] == "BOOK_AWAITING_NOTES"

    # 6. Skip notes
    session_data = data4["session_data"]
    msg5 = client.post("/chatbot/message", json={
        "action_value": "SKIP_NOTES",
        "payload": session_data
    }, headers=headers)
    assert msg5.status_code == 200
    data5 = msg5.json()
    assert data5["current_state"] == "BOOK_AWAITING_CONFIRM"

    # 7. Confirm booking
    session_data = data5["session_data"]
    msg6 = client.post("/chatbot/message", json={
        "action_value": "CONFIRM_BOOKING_YES",
        "payload": session_data
    }, headers=headers)
    assert msg6.status_code == 200
    data6 = msg6.json()
    assert data6["action_type"] == "completed"
    assert data6["booking_summary"] is not None
    booking_id = data6["booking_summary"]["booking_id"]
    assert booking_id.startswith("APT-")

    # 8. Verify appointment in patient's bookings
    patient_id = login_res.json()["user"]["id"]
    bookings_res = client.get(f"/patients/{patient_id}/bookings", headers=headers)
    assert bookings_res.status_code == 200
    bookings = bookings_res.json()
    assert any(b["booking_id"] == booking_id for b in bookings)

    # 9. Test cancellation flow via chatbot
    cancel_init = client.post("/chatbot/message", json={
        "message": "cancel my appointment"
    }, headers=headers)
    assert cancel_init.status_code == 200
    cancel_data = cancel_init.json()
    assert cancel_data["current_state"] == "CANCEL_SELECT_BOOKING"

    # Select the booking to cancel
    cancel_chip = [c for c in cancel_data["quick_replies"] if c["value"].startswith("SELECT_CANCEL_")][0]
    cancel_confirm = client.post("/chatbot/message", json={
        "action_value": cancel_chip["value"],
        "payload": cancel_data["session_data"]
    }, headers=headers)
    assert cancel_confirm.status_code == 200
    assert cancel_confirm.json()["current_state"] == "CANCEL_CONFIRM"

    # Confirm cancellation
    cancelled_res = client.post("/chatbot/message", json={
        "action_value": "CONFIRM_CANCEL_YES",
        "payload": cancel_confirm.json()["session_data"]
    }, headers=headers)
    assert cancelled_res.status_code == 200
    assert "cancelled" in cancelled_res.json()["reply_text"].lower()

def test_doctor_crm_and_emergency_block():
    # 1. Login doctor
    doc_login = client.post("/auth/doctor/login", json={
        "phone_number": "9876543210",
        "password": "doctor123"
    })
    doc_token = doc_login.json()["access_token"]
    doc_id = doc_login.json()["user"]["id"]
    doc_headers = {"Authorization": f"Bearer {doc_token}"}

    # 2. View dashboard
    dash = client.get(f"/doctors/{doc_id}/dashboard", headers=doc_headers)
    assert dash.status_code == 200
    dash_data = dash.json()
    assert "metrics_summary" in dash_data

    # 3. View insights
    insights = client.get(f"/doctors/{doc_id}/insights?range=monthly", headers=doc_headers)
    assert insights.status_code == 200
    insights_data = insights.json()
    assert "summary_text" in insights_data

    # 4. Emergency block schedule
    block_date = (date.today() + timedelta(days=5)).isoformat()
    block_res = client.post(f"/doctors/{doc_id}/schedule/block", json={
        "date": block_date,
        "reason": "Attending urgent surgical symposium"
    }, headers=doc_headers)
    assert block_res.status_code == 200
    assert block_res.json()["status"] == "blocked"
