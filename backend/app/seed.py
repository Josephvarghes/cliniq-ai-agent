from app.core.database import Base, engine, SessionLocal
from app.models.models import Doctor, AppointmentType
from app.core.security import get_password_hash
from app.core.config import settings

def init_db_and_seed():
    print("🛠️ Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created successfully.")

    db = SessionLocal()
    try:
        # Check or seed single default doctor
        doc = db.query(Doctor).first()
        if not doc:
            doc = Doctor(
                full_name=settings.DOCTOR_DEFAULT_NAME,
                phone_number=settings.DOCTOR_DEFAULT_PHONE,
                password_hash=get_password_hash(settings.DOCTOR_DEFAULT_PASSWORD),
                email=settings.DOCTOR_DEFAULT_EMAIL,
                specialization=settings.DOCTOR_DEFAULT_SPECIALIZATION
            )
            db.add(doc)
            db.commit()
            print(f"✅ Default Doctor seeded: {doc.full_name} ({doc.phone_number})")
        else:
            print(f"ℹ️ Doctor already exists: {doc.full_name}")

        # Check or seed appointment types
        types_count = db.query(AppointmentType).count()
        if types_count == 0:
            std_types = [
                AppointmentType(name="General Consultation", duration_minutes=30),
                AppointmentType(name="Follow-up Consultation", duration_minutes=20),
                AppointmentType(name="Comprehensive Health Checkup", duration_minutes=45)
            ]
            db.add_all(std_types)
            db.commit()
            print("✅ Default appointment types seeded.")
        else:
            print(f"ℹ️ Appointment types already seeded ({types_count} types).")
    finally:
        db.close()

if __name__ == "__main__":
    init_db_and_seed()
