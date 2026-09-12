from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Patient
from app.schemas.schemas import ChatbotMessageRequest, ChatbotMessageResponse
from app.services.auth_service import get_current_patient, get_default_doctor
from app.services.chatbot_fsm import process_chat_turn
from app.services.slot_service import get_available_slots_for_date

router = APIRouter(prefix="/chatbot", tags=["Chatbot"])

@router.post("/message", response_model=ChatbotMessageResponse)
def handle_chat_message(
    payload: ChatbotMessageRequest,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db)
):
    """
    Processes a conversational turn for the logged-in patient.
    Accepts text or quick-reply action payload and updates the conversation state.
    """
    response = process_chat_turn(
        db=db,
        patient=patient,
        message=payload.message,
        action_value=payload.action_value,
        client_payload=payload.payload
    )
    return response

@router.get("/availability", response_model=List[str])
def get_availability(
    date_query: date = Query(..., alias="date", description="Query date in YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    Returns live available time slots for the clinic doctor on the given date.
    No doctor_id is required from client as system is scoped to single doctor.
    """
    doctor = get_default_doctor(db)
    slots = get_available_slots_for_date(db, date_query, doctor.id)
    return slots
