from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_password_hash, create_access_token
from app.models.models import Patient, Doctor
from app.schemas.schemas import (
    PatientSignupRequest,
    PatientLoginRequest,
    DoctorLoginRequest,
    TokenResponse,
    PatientOut,
    DoctorOut
)
from app.services.auth_service import authenticate_patient, authenticate_doctor, get_default_doctor

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/patient/signup", response_model=TokenResponse)
def patient_signup(data: PatientSignupRequest, db: Session = Depends(get_db)):
    clean_phone = data.phone_number.strip()
    existing = db.query(Patient).filter(Patient.phone_number == clean_phone).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A patient account with this phone number already exists."
        )

    patient = Patient(
        full_name=data.full_name.strip(),
        phone_number=clean_phone,
        password_hash=get_password_hash(data.password),
        email=data.email.strip().lower()
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)

    token = create_access_token({"sub": patient.id, "role": "patient", "phone": patient.phone_number})
    return TokenResponse(
        access_token=token,
        role="patient",
        user={
            "id": patient.id,
            "full_name": patient.full_name,
            "phone_number": patient.phone_number,
            "email": patient.email
        }
    )

@router.post("/patient/login", response_model=TokenResponse)
def patient_login(data: PatientLoginRequest, db: Session = Depends(get_db)):
    patient = authenticate_patient(db, data.phone_number, data.password)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid phone number or password."
        )

    token = create_access_token({"sub": patient.id, "role": "patient", "phone": patient.phone_number})
    return TokenResponse(
        access_token=token,
        role="patient",
        user={
            "id": patient.id,
            "full_name": patient.full_name,
            "phone_number": patient.phone_number,
            "email": patient.email
        }
    )

@router.post("/doctor/login", response_model=TokenResponse)
def doctor_login(data: DoctorLoginRequest, db: Session = Depends(get_db)):
    doctor = authenticate_doctor(db, data.phone_number, data.password)
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid doctor credentials."
        )

    token = create_access_token({"sub": doctor.id, "role": "doctor", "phone": doctor.phone_number})
    return TokenResponse(
        access_token=token,
        role="doctor",
        user={
            "id": doctor.id,
            "full_name": doctor.full_name,
            "phone_number": doctor.phone_number,
            "email": doctor.email,
            "specialization": doctor.specialization
        }
    )
