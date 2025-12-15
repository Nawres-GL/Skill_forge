# backend/job_fetcher.py

import os
import time
import requests
from dotenv import load_dotenv
from backend.db import get_collection
from backend.ai.ai_matching import matching_engine

load_dotenv()

API_KEY = os.getenv("RAPIDAPI_KEY")
API_HOST = os.getenv("RAPIDAPI_HOST", "jsearch.p.rapidapi.com")
API_URL = os.getenv("RAPIDAPI_URL", "https://jsearch.p.rapidapi.com")

if not API_KEY:
    raise ValueError("RapidAPI key not set in environment variables!")


# 🔹 A simple fallback skill list for extraction
COMMON_SKILLS = [
    "python", "java", "javascript", "typescript", "react", "angular", "vue",
    "node", "django", "flask", "fastapi", "sql", "mysql", "postgresql",
    "mongodb", "aws", "azure", "docker", "kubernetes", "git", "linux",
    "html", "css", "pandas", "numpy", "machine learning", "ai", "devops"
]


def extract_skills(text: str) -> list[str]:
    """Extracts skills by keyword matching from job description."""
    if not text:
        return []
    text_lower = text.lower()
    found = [s for s in COMMON_SKILLS if s in text_lower]
    return list(set(found))  # remove duplicates


def search_jobs(query: str, location: str = "", limit: int = 5, auto_store: bool = True):
    """
    Fetch job postings from RapidAPI's JSearch endpoint.
    - Inserts them into jobs collection with `source: "api"` and `posted_by: "system@autofetch.ai"`
    - Precomputes embeddings (if auto_store True) by calling matching_engine.embed_and_store_job
    Returns list of inserted job documents (with _id).
    """
    url = f"{API_URL}/search"
    headers = {"X-RapidAPI-Key": API_KEY, "X-RapidAPI-Host": API_HOST}
    params = {"query": query, "location": location, "num_pages": 1, "page": 1}

    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds

    for attempt in range(1, MAX_RETRIES + 1):
        res = requests.get(url, headers=headers, params=params)
        if res.status_code == 200:
            break
        elif res.status_code == 401:
            raise Exception("Invalid API key. Please check your RapidAPI key!")
        elif res.status_code == 429:
            time.sleep(RETRY_DELAY * attempt)
            continue
        else:
            raise Exception(f"Job API error {res.status_code}: {res.text}")
    else:
        raise Exception("Job API fetch failed after retries")

    data = res.json()
    jobs_collection = get_collection("jobs")
    inserted = []

    for j in data.get("data", [])[:limit]:
        # Try using provided required_skills; otherwise extract from description
        skills = [s.strip() for s in (j.get("job_required_skills") or "").split(",") if s.strip()]
        if not skills:
            skills = extract_skills(j.get("job_description", ""))

        job_doc = {
            "title": j.get("job_title"),
            "company": j.get("employer_name"),
            "location": j.get("job_city") or j.get("job_country"),
            "description": j.get("job_description"),
            "required_skills": skills,
            "job_type": j.get("job_employment_type"),
            "source": "api",
            "posted_by": "system@autofetch.ai"
        }

        result = jobs_collection.insert_one(job_doc)
        job_doc["_id"] = result.inserted_id

        if auto_store:
            try:
                matching_engine.embed_and_store_job(job_doc)
            except Exception as e:
                print(f"⚠️ Failed to embed job (id={job_doc['_id']}): {e}")

        inserted.append(job_doc)

    return inserted
