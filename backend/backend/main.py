from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.config import settings
from backend.db import Database
from backend.routes import auth, users, hr, matching, apps, job_fetcher
import os

# Initialize FastAPI app
app = FastAPI(
    title="SkillForge API",
    description="Backend API for SkillForge - AI-powered job matching platform",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Serve uploaded files (profile pictures, etc.)
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Database connection events
@app.on_event("startup")
async def startup_db_client():
    Database.connect_db()
    print("✅ SkillForge API started successfully!")

@app.on_event("shutdown")
async def shutdown_db_client():
    Database.close_db()

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(hr.router)
app.include_router(matching.router)
app.include_router(apps.router)
app.include_router(job_fetcher.router)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to SkillForge API",
        "version": "1.0.0",
        "docs": "/docs"
    }

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
