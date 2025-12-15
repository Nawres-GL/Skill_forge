# backend/routes/matching.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from backend.utils.utils import get_current_candidate, get_current_hr
from backend.ai.ai_matching import matching_engine

router = APIRouter(prefix="/matching", tags=["AI Matching"])


@router.get("/jobs/recommended", response_model=List[dict])
async def get_recommended_jobs(
    top_n: int = Query(default=10, ge=1, le=50),
    source: Optional[str] = Query(default=None, description="Filter by job source: 'hr'|'api' or None for all"),
    current_user: dict = Depends(get_current_candidate)
):
    """
    Get AI-recommended jobs for current candidate (optionally filter by source).
    """
    jobs = matching_engine.find_matching_jobs_for_candidate(
        candidate_email=current_user["email"],
        top_n=top_n,
        source=source
    )
    return jobs


@router.get("/candidates/recommended/{job_id}", response_model=List[dict])
async def get_recommended_candidates(
    job_id: str,
    top_n: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_hr)
):
    """
    Get AI-recommended candidates for a specific job
    """
    candidates = matching_engine.find_matching_candidates_for_job(
        job_id=job_id,
        top_n=top_n
    )

    if not candidates:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or no candidates available"
        )

    return candidates


@router.get("/skill-gap/{job_id}", response_model=dict)
async def analyze_skill_gap(
    job_id: str,
    current_user: dict = Depends(get_current_candidate)
):
    """
    Analyze skill gaps between current candidate and a job
    """
    analysis = matching_engine.analyze_skill_gaps(
        candidate_email=current_user["email"],
        job_id=job_id
    )

    if "error" in analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=analysis["error"]
        )

    return analysis


@router.post("/calculate-score", response_model=dict)
async def calculate_match_score(
    candidate_email: str,
    job_id: str,
    current_user: dict = Depends(get_current_hr)
):
    """
    Calculate match score between a specific candidate and job (HR only)
    """
    # Import here to avoid circular import in some setups
    from backend.db import get_collection
    from bson import ObjectId

    candidates_collection = get_collection("candidates")
    jobs_collection = get_collection("jobs")

    candidate = candidates_collection.find_one({"email": candidate_email})
    try:
        job = jobs_collection.find_one({"_id": ObjectId(job_id)})
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID"
        )

    if not candidate or not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate or job not found"
        )

    score = matching_engine.calculate_match_score(candidate, job)

    return {
        "candidate_email": candidate_email,
        "job_id": job_id,
        "job_title": job.get("title"),
        "match_score": score,
        "match_percentage": round(score * 100, 1)
    }
