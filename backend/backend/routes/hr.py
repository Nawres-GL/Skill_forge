from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Body
from typing import Any, Dict, List, Optional
from backend.models import JobCreate, JobOut
from backend.utils.utils import get_current_hr
from backend.db import get_collection
from bson import ObjectId
from backend.config import settings
import os

router = APIRouter(prefix="/hr", tags=["HR"])

UPLOAD_DIR = "uploads/profile_pictures"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/me")
async def get_my_profile(current_user: dict = Depends(get_current_hr)):
    """Retrieve HR profile"""
    hr_collection = get_collection("hr_users")
    user = hr_collection.find_one({"email": current_user["email"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="HR user not found")
    return user


@router.put("/me/hr")
async def update_hr_profile(
    updates: Dict[str, Any] = Body(
        ...,
        example={
            "name": "Alice HR",
            "bio": "HR manager passionate about connecting talent with opportunities.",
            "company": "TechRecruiters Inc."
        },
        description="Provide the HR fields to update."
    ),
    current_user: dict = Depends(get_current_hr)
):
    """Update HR profile (name, bio, company, etc.)"""
    hr_collection = get_collection("hr_users")
    allowed_fields = {"name", "bio", "company"}

    # ✅ Filter allowed and non-empty fields
    update_data = {
        k: v for k, v in updates.items()
        if k in allowed_fields and v not in [None, "", []]
    }

    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    # ✅ Perform the update
    result = hr_collection.update_one(
        {"email": current_user["email"]},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="HR user not found.")

    return {
        "message": "Profile updated successfully.",
        "updated_fields": list(update_data.keys())
    }

@router.post("/me/profile-picture")
async def upload_hr_profile_picture(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_hr)
):
    """Upload or update HR's profile picture"""
    hr_collection = get_collection("hr_users")

    filename = f"{current_user['email'].replace('@', '_')}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    public_url = f"{settings.BASE_URL}/{file_path.replace(os.sep, '/')}"  # ✅ Serve static URL

    result = hr_collection.update_one(
        {"email": current_user["email"]},
        {"$set": {"profile_picture": public_url}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="HR user not found")

    return {"message": "Profile picture uploaded successfully", "url": public_url}

@router.post("/jobs", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_job(
    job: JobCreate,
    current_user: dict = Depends(get_current_hr)
):
    """Create a new job posting"""
    jobs_collection = get_collection("jobs")
    
    # Add HR email to job posting
    job_dict = job.model_dump()
    job_dict = job.model_dump()
    job_dict["created_at"] = datetime.utcnow()
    job_dict["posted_by"] = current_user["email"]
    
    result = jobs_collection.insert_one(job_dict)
    
    return {
        "message": "Job created successfully",
        "job_id": str(result.inserted_id)
    }

@router.get("/jobs", response_model=List[dict])
async def get_my_jobs(current_user: dict = Depends(get_current_hr)):
    """Get all jobs posted by current HR"""
    jobs_collection = get_collection("jobs")
    
    jobs = list(jobs_collection.find({"posted_by": current_user["email"]}))
    
    # Convert ObjectId to string
    for job in jobs:
        job["_id"] = str(job["_id"])
    
    return jobs

@router.get("/jobs/{job_id}", response_model=dict)
async def get_job(
    job_id: str,
    current_user: dict = Depends(get_current_hr)
):
    """Get a specific job by ID"""
    jobs_collection = get_collection("jobs")
    
    try:
        job = jobs_collection.find_one({
            "_id": ObjectId(job_id),
            "posted_by": current_user["email"]
        })
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID"
        )
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    job["_id"] = str(job["_id"])
    return job

@router.put("/jobs/{job_id}", response_model=dict)
async def update_job(
    job_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,   # ← ADD THIS
    required_skills: Optional[List[str]] = None,
    current_user: dict = Depends(get_current_hr)
):
    jobs_collection = get_collection("jobs")

    update_data = {}
    if title:
        update_data["title"] = title
    if description:
        update_data["description"] = description
    if location:                   # ← ADD THIS
        update_data["location"] = location
    if required_skills:
        update_data["required_skills"] = required_skills

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update"
        )

    result = jobs_collection.update_one(
        {"_id": ObjectId(job_id), "posted_by": current_user["email"]},
        {"$set": update_data}
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or no changes made"
        )

    return {"message": "Job updated successfully"}


@router.delete("/jobs/{job_id}", response_model=dict)
async def delete_job(
    job_id: str,
    current_user: dict = Depends(get_current_hr)
):
    """Delete a job posting"""
    jobs_collection = get_collection("jobs")
    
    try:
        result = jobs_collection.delete_one({
            "_id": ObjectId(job_id),
            "posted_by": current_user["email"]
        })
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID"
        )
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    return {"message": "Job deleted successfully"}

@router.get("/candidates/search", response_model=List[dict])
async def search_candidates(
    skills: Optional[str] = None,
    current_user: dict = Depends(get_current_hr)
):
    """Search candidates by skills"""
    candidates_collection = get_collection("candidates")
    
    query = {}
    if skills:
        skill_list = [s.strip() for s in skills.split(",")]
        query["skills.name"] = {"$in": skill_list}
    
    candidates = list(candidates_collection.find(query, {"password": 0}))
    
    # Convert ObjectId to string
    for candidate in candidates:
        candidate["_id"] = str(candidate["_id"])
    
    return candidates
