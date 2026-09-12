from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    PROJECT_NAME: str = "Cliniq AI Agent"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"

    DATABASE_URL: str = "sqlite:///./clinic.db"

    JWT_SECRET_KEY: str = "cliniq_secret_key_super_secure_clinic_agent_2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "cliniq.agent@example.com"
    EMAIL_MOCK_FALLBACK: bool = True

    DOCTOR_DEFAULT_NAME: str = "Dr. Joseph Varghese, MD"
    DOCTOR_DEFAULT_PHONE: str = "9876543210"
    DOCTOR_DEFAULT_PASSWORD: str = "doctor123"
    DOCTOR_DEFAULT_EMAIL: str = "dr.varghese@exampleclinic.com"
    DOCTOR_DEFAULT_SPECIALIZATION: str = "General Physician"

settings = Settings()
