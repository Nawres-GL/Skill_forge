# backend/routes/applications.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime
from backend.models import JobApplication
from backend.utils.utils import get_current_candidate, get_current_hr
from backend.db import get_collection
from backend.ai.ai_matching import matching_engine
from bson import ObjectId

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.post("/apply/{job_id}", response_model=dict, status_code=status.HTTP_201_CREATED)
async def apply_to_job(
    job_id: str,
    current_user: dict = Depends(get_current_candidate)
):
    """Apply to a job posting"""
    applications_collection = get_collection("applications")
    jobs_collection = get_collection("jobs")
    candidates_collection = get_collection("candidates")

    # Check if job exists
    try:
        job = jobs_collection.find_one({"_id": ObjectId(job_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID"
        )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Check if already applied
    existing_application = applications_collection.find_one({
        "candidate_email": current_user["email"],
        "job_id": job_id
    })

    if existing_application:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already applied to this job"
        )

    # Get candidate for match score calculation
    candidate = candidates_collection.find_one({"email": current_user["email"]})
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )

    # Calculate match score
    try:
        match_score = matching_engine.calculate_match_score(candidate, job)
    except Exception as e:
        print("Warning: failed to calculate match score:", e)
        match_score = 0.0

    # Create application
    application = {
        "candidate_email": current_user["email"],
        "job_id": job_id,
        "applied_at": datetime.utcnow(),
        "status": "pending",
        "matching_score": match_score,
        "job_source": job.get("source", "unknown")
    }

    result = applications_collection.insert_one(application)

    return {
        "message": "Application submitted successfully",
        "application_id": str(result.inserted_id),
        "match_score": match_score
    }


@router.get("/my-applications", response_model=List[dict])
async def get_my_applications(current_user: dict = Depends(get_current_candidate)):
    """Get all applications for current candidate"""
    applications_collection = get_collection("applications")
    jobs_collection = get_collection("jobs")

    applications = list(applications_collection.find({
        "candidate_email": current_user["email"]
    }))

    for app in applications:
        app["_id"] = str(app["_id"])
        try:
            job = jobs_collection.find_one({"_id": ObjectId(app["job_id"])})
            if job:
                app["job_title"] = job.get("title")
                app["company"] = job.get("company")
                app["job_type"] = job.get("job_type")
                app["job_source"] = job.get("source", "unknown")
        except Exception:
            pass

    return applications


@router.get("/job/{job_id}/applications", response_model=List[dict])
async def get_job_applications(
    job_id: str,
    current_user: dict = Depends(get_current_hr)
):
    """Get all applications for a specific job (HR only)"""
    applications_collection = get_collection("applications")
    candidates_collection = get_collection("candidates")
    jobs_collection = get_collection("jobs")

    # Get job data
    try:
        job = jobs_collection.find_one({"_id": ObjectId(job_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format"
        )

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # ✅ If job is HR-posted -> must match email
    if job.get("source") != "api" and job.get("posted_by") != current_user["email"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view applications for this job"
        )

    # Fetch applications for this job
    applications = list(applications_collection.find({"job_id": job_id}))

    # Attach candidate profiles + formatting
    for app in applications:
        app["_id"] = str(app["_id"])
        candidate = candidates_collection.find_one(
            {"email": app["candidate_email"]},
            {"password": 0}
        )
        if candidate:
            candidate["_id"] = str(candidate["_id"])
            app["candidate"] = candidate

    # ✅ Sort by AI match score
    applications.sort(key=lambda x: x.get("matching_score", 0), reverse=True)

    return applications



@router.put("/applications/{application_id}/status", response_model=dict)
async def update_application_status(
    application_id: str,
    new_status: str,
    current_user: dict = Depends(get_current_hr)
):
    """Update application status (HR only)"""
    if new_status not in ["pending", "reviewed", "interview", "accepted", "rejected"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status value"
        )

    applications_collection = get_collection("applications")
    jobs_collection = get_collection("jobs")

    # Get application
    try:
        application = applications_collection.find_one({"_id": ObjectId(application_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid application ID"
        )

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )

    # Get related job
    job = jobs_collection.find_one({"_id": ObjectId(application["job_id"])})

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated job not found"
        )

    # ✅ Same ownership rule as above
    if job.get("source") != "api" and job.get("posted_by") != current_user["email"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update applications for this job"
        )

    applications_collection.update_one(
        {"_id": ObjectId(application_id)},
        {"$set": {"status": new_status}}
    )

    return {
        "message": "Application status updated successfully",
        "new_status": new_status
    }
