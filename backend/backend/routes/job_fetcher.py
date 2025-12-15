from fastapi import APIRouter, Query, HTTPException
from backend.ai.job_fetcher import search_jobs

router = APIRouter(prefix="/jobs", tags=["Job Fetcher"])


@router.get("/fetch")
def fetch_jobs(
    query: str = Query(..., description="Job search query, e.g. 'Python developer'"),
    location: str = Query("", description="Optional job location"),
    limit: int = Query(5, ge=1, le=20, description="Number of jobs to fetch (max 20)"),
    auto_store: bool = Query(True, description="Whether to store jobs & precompute embeddings"),
):
    """
    Fetch jobs from the external RapidAPI (JSearch) and optionally store them in the database.
    Returns the list of inserted jobs.
    """
    try:
        jobs = search_jobs(query=query, location=location, limit=limit, auto_store=auto_store)

        # ✅ Convert ObjectId fields to string for JSON serialization
        for job in jobs:
            if "_id" in job:
                job["_id"] = str(job["_id"])

        return {"count": len(jobs), "jobs": jobs}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
