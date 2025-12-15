from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime, date


# ----------------------
# Portfolio & Education Models
# ----------------------
class PortfolioItem(BaseModel):
    title: str
    description: Optional[str] = None
    link: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class EducationItem(BaseModel):
    degree: str
    institution: str
    start_year: int
    end_year: Optional[int] = None
    description: Optional[str] = None

class ExperienceItem(BaseModel):
    role: str
    company: str
    start_date: date
    end_date: Optional[date] = None
    description: Optional[str] = None

# ----------------------
# Skills & Recommendations
# ----------------------
class SkillItem(BaseModel):
    name: str
    level: Optional[int] = Field(0, ge=0, le=100, description="Skill level as a percentage (0–100%)")

class RecommendationItem(BaseModel):
    skill_name: str
    recommendation_text: str
    suggested_by: Optional[str] = None  # Could be AI system or HR
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ----------------------
# Candidate Models
# ----------------------
class CandidateBase(BaseModel):
    name: str
    email: EmailStr
    role: str = "candidate"
    bio: Optional[str] = None
    profile_picture: Optional[str] = None  # ✅ NEW

class CandidateCreate(CandidateBase):
    password: str
    skills: Optional[List[SkillItem]] = []
    portfolio: Optional[List[PortfolioItem]] = []
    education: Optional[List[EducationItem]] = []
    experience: Optional[List[ExperienceItem]] = []

class CandidateOut(CandidateBase):
    skills: Optional[List[SkillItem]] = []
    portfolio: Optional[List[PortfolioItem]] = []
    education: Optional[List[EducationItem]] = []
    experience: Optional[List[ExperienceItem]] = []
    recommendations: Optional[List[RecommendationItem]] = []

# ----------------------
# HR / Recruiter Models
# ----------------------
class HRBase(BaseModel):
    name: str
    email: EmailStr
    role: str = "hr"
    company: Optional[str] = None
    bio: Optional[str] = None
    profile_picture: Optional[str] = None  # ✅ NEW

class HRCreate(HRBase):
    password: str

class HROut(HRBase):
    pass

# ----------------------
# Job Models
# ----------------------
class JobBase(BaseModel):
    title: str
    description: str
    required_skills: List[str]
    job_type: str = "Full-time"  # Full-time, Part-time, Remote
    location: Optional[str] = None
    created_at: datetime | None = None

class JobCreate(JobBase):
    pass


class JobOut(JobBase):
    posted_by: str

# ----------------------
# Job Matching & Application Models
# ----------------------
class JobApplication(BaseModel):
    candidate_email: EmailStr
    job_id: str
    applied_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "pending"  # pending, accepted, rejected
    matching_score: Optional[float] = None  # AI similarity score
