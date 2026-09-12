from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.seed import init_db_and_seed
from app.services.scheduler_service import start_scheduler, stop_scheduler
from app.routers import auth, chatbot, patients, appointments, doctors

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables and seed data exist
    init_db_and_seed()
    # Start reminder background scheduler
    try:
        start_scheduler()
    except Exception as e:
        print(f"Scheduler failed to start: {e}")
    yield
    # Shutdown
    stop_scheduler()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Autonomous Clinical Appointment Booking & Doctor Practice Management Engine",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(chatbot.router)
app.include_router(patients.router)
app.include_router(appointments.router)
app.include_router(doctors.router)

@app.get("/")
def root():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "scope": "Single Doctor Practice (Rule-Based FSM Chatbot)"
    }

@app.get("/health")
def health_check():
    return {"status": "ok"}
