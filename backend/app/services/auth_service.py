from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token
from app.models.models import Patient, Doctor
from app.core.config import settings

security = HTTPBearer(auto_error=False)

def get_default_doctor(db: Session) -> Doctor:
    """Returns the primary (single) doctor in the system."""
    doc = db.query(Doctor).first()
    if not doc:
        # Seed on demand if somehow missing
        doc = Doctor(
            full_name=settings.DOCTOR_DEFAULT_NAME,
            phone_number=settings.DOCTOR_DEFAULT_PHONE,
            password_hash=get_password_hash(settings.DOCTOR_DEFAULT_PASSWORD),
            email=settings.DOCTOR_DEFAULT_EMAIL,
            specialization=settings.DOCTOR_DEFAULT_SPECIALIZATION
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
    return doc

def authenticate_patient(db: Session, phone_number: str, password: str) -> Optional[Patient]:
    patient = db.query(Patient).filter(Patient.phone_number == phone_number.strip()).first()
    if not patient:
        return None
    if not verify_password(password, patient.password_hash):
        return None
    return patient

def authenticate_doctor(db: Session, phone_number: str, password: str) -> Optional[Doctor]:
    doctor = db.query(Doctor).filter(Doctor.phone_number == phone_number.strip()).first()
    if not doctor:
        # Check against default doctor credentials
        if phone_number.strip() == settings.DOCTOR_DEFAULT_PHONE and password == settings.DOCTOR_DEFAULT_PASSWORD:
            return get_default_doctor(db)
        return None
    if not verify_password(password, doctor.password_hash):
        return None
    return doctor

def get_current_user_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> dict:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload

def get_current_patient(
    token_data: dict = Depends(get_current_user_token),
    db: Session = Depends(get_db)
) -> Patient:
    if token_data.get("role") != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to patients"
        )
    patient_id = token_data.get("sub")
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return patient

def get_current_doctor(
    token_data: dict = Depends(get_current_user_token),
    db: Session = Depends(get_db)
) -> Doctor:
    if token_data.get("role") != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to doctors"
        )
    doctor_id = token_data.get("sub")
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        # Fallback to default doctor if ID matches
        def_doc = get_default_doctor(db)
        if def_doc.id == doctor_id:
            return def_doc
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    return doctor
