# backend/ai_matching.py
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
import numpy as np
from bson import ObjectId

try:
    from backend.db import get_collection
except Exception:
    from backend.db import get_collection


class AIMatchingEngine:
    """
    AI-powered semantic matching engine for job-candidate matching using sentence-transformers.
    Adds weighted skill-level embeddings and improved composite scoring.
    """

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    # -------------------------
    # Text extraction utilities
    # -------------------------
    def _extract_candidate_text(self, candidate: dict) -> str:
        """Return a concatenated text representation of candidate profile."""
        text_parts: List[str] = []

        if candidate.get("bio"):
            text_parts.append(candidate["bio"])

        # 🧠 Skill names + level weights (makes model aware of proficiency)
        if candidate.get("skills"):
            skills_weighted = [
                f"{s['name']} ({int(s['level']/10)} stars)"
                for s in candidate["skills"]
                if isinstance(s, dict) and s.get("name")
            ]
            text_parts.append(" ".join(skills_weighted))

        if candidate.get("experience"):
            for exp in candidate["experience"]:
                if exp.get("role"):
                    text_parts.append(exp["role"])
                if exp.get("description"):
                    text_parts.append(exp["description"])

        if candidate.get("education"):
            for edu in candidate["education"]:
                if edu.get("degree"):
                    text_parts.append(edu["degree"])
                if edu.get("institution"):
                    text_parts.append(edu["institution"])

        if candidate.get("portfolio"):
            for p in candidate["portfolio"]:
                if p.get("title"):
                    text_parts.append(p["title"])
                if p.get("description"):
                    text_parts.append(p["description"])

        return " ".join(text_parts).strip()

    def _extract_job_text(self, job: dict) -> str:
        """Return a concatenated text representation of the job posting."""
        text_parts: List[str] = []
        if job.get("title"):
            text_parts.append(job["title"])
        if job.get("company"):
            text_parts.append(job["company"])
        if job.get("description"):
            text_parts.append(job["description"])
        if job.get("required_skills"):
            text_parts.append(" ".join(job["required_skills"]))
        if job.get("job_type"):
            text_parts.append(job["job_type"])
        if job.get("location"):
            text_parts.append(job["location"])
        return " ".join(text_parts).strip()

    # -------------------------
    # Embedding + DB utilities
    # -------------------------
    def encode_text(self, text: str) -> Optional[np.ndarray]:
        """Encode text to a numpy embedding."""
        if not text:
            return None
        emb = self.model.encode(text, convert_to_tensor=False)
        return np.asarray(emb, dtype=float)

    def embed_and_store_job(self, job: dict):
        """Compute embedding for job text and store in MongoDB."""
        jobs_col = get_collection("jobs")
        job_text = self._extract_job_text(job)
        if not job_text:
            return None
        emb = self.encode_text(job_text)
        if emb is None:
            return None
        jobs_col.update_one({"_id": job["_id"]}, {"$set": {"embedding": emb.tolist()}}, upsert=False)
        return emb

    def embed_and_store_candidate(self, candidate: dict):
        """Compute embedding for candidate profile and store in MongoDB."""
        cand_col = get_collection("candidates")
        cand_text = self._extract_candidate_text(candidate)
        if not cand_text:
            return None
        emb = self.encode_text(cand_text)
        if emb is None:
            return None
        cand_col.update_one({"_id": candidate["_id"]}, {"$set": {"embedding": emb.tolist()}}, upsert=False)
        return emb

    def bulk_embed_jobs(self, source: Optional[str] = None) -> int:
        """Embed all jobs missing embeddings (optionally by source)."""
        jobs_col = get_collection("jobs")
        query = {"embedding": {"$exists": False}}
        if source:
            query["source"] = source
        jobs = list(jobs_col.find(query))
        for job in jobs:
            try:
                self.embed_and_store_job(job)
            except Exception as e:
                print("Warning embedding job", job.get("_id"), e)
        return len(jobs)

    # -------------------------
    # Matching utilities
    # -------------------------
    def _calculate_skill_match(self, candidate: dict, job: dict) -> float:
        """
        Compute skill match weighted by level.
        Example: if candidate has AI (90) and job requires AI, they contribute 0.9 instead of 1.
        """
        if not job.get("required_skills"):
            return 0.0
        required = [s.lower() for s in job.get("required_skills", []) if isinstance(s, str)]
        if not candidate.get("skills"):
            return 0.0

        cand_skills = {s["name"].lower(): s["level"] for s in candidate["skills"] if s.get("name")}
        total_weight = 0
        matched_weight = 0
        for skill in required:
            total_weight += 1
            if skill in cand_skills:
                matched_weight += cand_skills[skill] / 100.0  # normalize 0–1 scale
        if total_weight == 0:
            return 0.0
        return matched_weight / total_weight

    def _cosine_similarity(self, a: Optional[np.ndarray], b: Optional[np.ndarray]) -> float:
        """Safe cosine similarity."""
        if a is None or b is None:
            return 0.0
        a = np.asarray(a).ravel()
        b = np.asarray(b).ravel()
        denom = (np.linalg.norm(a) * np.linalg.norm(b))
        if denom == 0:
            return 0.0
        return float(np.dot(a, b) / denom)

    def _calculate_experience_boost(self, candidate: dict) -> float:
        """Add a small bonus based on number of experiences."""
        exp = candidate.get("experience", [])
        if not exp:
            return 0.0
        return min(len(exp) * 0.05, 0.2)  # max +0.2 boost

    def calculate_match_score(self, candidate: dict, job: dict) -> float:
        """Final composite match score = 0.6 * semantic + 0.3 * skill + 0.1 * exp."""
        cand_text = self._extract_candidate_text(candidate)
        job_text = self._extract_job_text(job)
        if not cand_text or not job_text:
            return 0.0

        jobs_col = get_collection("jobs")
        cands_col = get_collection("candidates")

        candidate_emb = None
        job_emb = None

        try:
            if candidate.get("_id"):
                cand_db = cands_col.find_one({"_id": candidate["_id"]})
                if cand_db and cand_db.get("embedding"):
                    candidate_emb = np.asarray(cand_db["embedding"], dtype=float)
                else:
                    candidate_emb = self.embed_and_store_candidate(candidate)
            else:
                candidate_emb = self.encode_text(cand_text)
        except Exception:
            candidate_emb = self.encode_text(cand_text)

        try:
            if job.get("_id"):
                job_db = jobs_col.find_one({"_id": job["_id"]})
                if job_db and job_db.get("embedding"):
                    job_emb = np.asarray(job_db["embedding"], dtype=float)
                else:
                    job_emb = self.embed_and_store_job(job)
            else:
                job_emb = self.encode_text(job_text)
        except Exception:
            job_emb = self.encode_text(job_text)

        semantic_sim = self._cosine_similarity(candidate_emb, job_emb)
        skill_score = self._calculate_skill_match(candidate, job)
        exp_boost = self._calculate_experience_boost(candidate)

        final_score = (0.6 * semantic_sim) + (0.3 * skill_score) + (0.1 * exp_boost)
        return round(float(max(0.0, min(1.0, final_score))), 3)

    # -------------------------
    # Candidate ↔ Job search
    # -------------------------
    def find_matching_jobs_for_candidate(self, candidate_email: str, top_n: int = 10, source: Optional[str] = None) -> List[Dict]:
        cands_col = get_collection("candidates")
        jobs_col = get_collection("jobs")

        candidate = cands_col.find_one({"email": candidate_email})
        if not candidate:
            return []

        if not candidate.get("embedding"):
            self.embed_and_store_candidate(candidate)
            candidate = cands_col.find_one({"_id": candidate["_id"]})

        query = {"source": source} if source else {}
        jobs = list(jobs_col.find(query))
        scored = []
        for job in jobs:
            score = self.calculate_match_score(candidate, job)
            job_copy = dict(job)
            job_copy["_id"] = str(job_copy["_id"])
            job_copy["match_score"] = score
            scored.append(job_copy)
        scored.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        return scored[:top_n]

    def find_matching_candidates_for_job(self, job_id: str, top_n: int = 20) -> List[Dict]:
        cands_col = get_collection("candidates")
        jobs_col = get_collection("jobs")

        try:
            job = jobs_col.find_one({"_id": ObjectId(job_id)})
        except Exception:
            return []

        if not job:
            return []

        if not job.get("embedding"):
            self.embed_and_store_job(job)
            job = jobs_col.find_one({"_id": job["_id"]})

        candidates = list(cands_col.find({}, {"password": 0}))
        scored = []
        for candidate in candidates:
            if not candidate.get("embedding"):
                self.embed_and_store_candidate(candidate)
                candidate = cands_col.find_one({"_id": candidate["_id"]})
            score = self.calculate_match_score(candidate, job)
            cand_copy = dict(candidate)
            cand_copy["_id"] = str(cand_copy["_id"])
            cand_copy["match_score"] = score
            scored.append(cand_copy)
        scored.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        return scored[:top_n]

    # -------------------------
    # Skill gap analysis
    # -------------------------
    def analyze_skill_gaps(self, candidate_email: str, job_id: str) -> Dict:
        cands_col = get_collection("candidates")
        jobs_col = get_collection("jobs")

        candidate = cands_col.find_one({"email": candidate_email})
        try:
            job = jobs_col.find_one({"_id": ObjectId(job_id)})
        except Exception:
            return {"error": "Invalid job ID"}

        if not candidate or not job:
            return {"error": "Candidate or job not found"}

        candidate_skills = set(s.get("name", "").lower() for s in candidate.get("skills", []) if isinstance(s, dict))
        required_skills = set(s.lower() for s in job.get("required_skills", []) if isinstance(s, str))

        missing_skills = sorted(list(required_skills - candidate_skills))
        matching_skills = sorted(list(required_skills.intersection(candidate_skills)))

        match_percentage = 0.0
        if len(required_skills) > 0:
            match_percentage = round((len(matching_skills) / len(required_skills)) * 100, 1)

        return {
            "job_title": job.get("title"),
            "match_percentage": match_percentage,
            "matching_skills": matching_skills,
            "missing_skills": missing_skills,
            "total_required": len(required_skills),
            "recommendations": self._generate_recommendations(missing_skills)
        }

    def _generate_recommendations(self, missing_skills: List[str]) -> List[str]:
        return [f"Consider learning {s.title()} through online courses or certifications" for s in missing_skills[:5]]


# Global instance
matching_engine = AIMatchingEngine()
