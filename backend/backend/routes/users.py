from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Body
import os
from backend.config import settings
from typing import Any, Dict, List, Optional
from backend.models import CandidateOut, SkillItem, PortfolioItem, EducationItem, ExperienceItem
from backend.utils.utils import get_current_candidate
from backend.db import get_collection
from bson import ObjectId

router = APIRouter(prefix="/candidates", tags=["Candidates"])

UPLOAD_DIR = "uploads/profile_pictures"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/me")
async def get_my_profile(current_user: dict = Depends(get_current_candidate)):
    """Retrieve candidate profile"""
    candidates = get_collection("candidates")
    user = candidates.find_one({"email": current_user["email"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return user


@router.put("/me")
async def update_my_profile(
    updates: Dict[str, Any] = Body(
        ...,
        example={
            "name": "John Doe",
            "bio": "Passionate data scientist with 3 years of experience.",
            "skills": ["Python", "FastAPI", "MongoDB"],
            "portfolio": "https://myportfolio.com",
            "education": "BSc in Computer Science",
            "experience": "3 years at TechCorp"
        },
        description="Provide the candidate fields to update."
    ),
    current_user: dict = Depends(get_current_candidate)
):
    """Update candidate profile (name, bio, skills, etc.)"""
    candidates = get_collection("candidates")
    allowed_fields = {"name", "bio", "skills", "portfolio", "education", "experience"}

    # ✅ Filter allowed and non-empty fields
    update_data = {
        k: v for k, v in updates.items()
        if k in allowed_fields and v not in [None, "", []]
    }

    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update.")

    # ✅ Perform the update
    result = candidates.update_one(
        {"email": current_user["email"]},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    return {
        "message": "Profile updated successfully.",
        "updated_fields": list(update_data.keys())
    }


@router.post("/me/profile-picture")
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_candidate)
):
    """Upload or update candidate's profile picture"""
    candidates = get_collection("candidates")

    filename = f"{current_user['email'].replace('@', '_')}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    public_url = f"{settings.BASE_URL}/{file_path.replace(os.sep, '/')}"  # ✅ Serve static URL

    result = candidates.update_one(
        {"email": current_user["email"]},
        {"$set": {"profile_picture": public_url}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Candidate not found")

    return {"message": "Profile picture uploaded successfully", "url": public_url}

@router.post("/me/skills", response_model=dict)
async def add_skill(
    skill: SkillItem,
    current_user: dict = Depends(get_current_candidate)
):
    """Add a skill to candidate's profile"""
    candidates_collection = get_collection("candidates")
    
    result = candidates_collection.update_one(
        {"email": current_user["email"]},
        {"$push": {"skills": skill.model_dump()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    return {"message": "Skill added successfully"}

@router.put("/me/skills/{skill_name}", response_model=dict)
async def update_skill(
    skill_name: str,
    updated_skill: SkillItem,
    current_user: dict = Depends(get_current_candidate)
):
    """Update an existing skill by name"""
    candidates_collection = get_collection("candidates")
    
    result = candidates_collection.update_one(
        {"email": current_user["email"], "skills.name": skill_name},
        {"$set": {"skills.$": updated_skill.model_dump()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found"
        )
    
    return {"message": "Skill updated successfully"}

@router.delete("/me/skills/{skill_name}", response_model=dict)
async def delete_skill(
    skill_name: str,
    current_user: dict = Depends(get_current_candidate)
):
    """Delete a skill by name"""
    candidates_collection = get_collection("candidates")
    
    result = candidates_collection.update_one(
        {"email": current_user["email"]},
        {"$pull": {"skills": {"name": skill_name}}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found"
        )
    
    return {"message": "Skill deleted successfully"}


@router.post("/me/portfolio", response_model=dict)
async def add_portfolio_item(
    portfolio_item: PortfolioItem,
    current_user: dict = Depends(get_current_candidate)
):
    """Add a portfolio item to candidate's profile"""
    candidates_collection = get_collection("candidates")
    
    result = candidates_collection.update_one(
        {"email": current_user["email"]},
        {"$push": {"portfolio": portfolio_item.model_dump()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    return {"message": "Portfolio item added successfully"}

@router.put("/me/portfolio/{title}", response_model=dict)
async def update_portfolio_item(
    title: str,
    updated_portfolio: PortfolioItem,
    current_user: dict = Depends(get_current_candidate)
):
    """Update an existing portfolio item by title"""
    candidates_collection = get_collection("candidates")
    
    result = candidates_collection.update_one(
        {"email": current_user["email"], "portfolio.title": title},
        {"$set": {"portfolio.$": updated_portfolio.model_dump()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio item not found"
        )
    
    return {"message": "Portfolio item updated successfully"}


@router.delete("/me/portfolio/{title}", response_model=dict)
async def delete_portfolio_item(
    title: str,
    current_user: dict = Depends(get_current_candidate)
):
    """Delete a portfolio item by title"""
    candidates_collection = get_collection("candidates")
    
    result = candidates_collection.update_one(
        {"email": current_user["email"]},
        {"$pull": {"portfolio": {"title": title}}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio item not found"
        )
    
    return {"message": "Portfolio item deleted successfully"}


@router.post("/me/education", response_model=dict)
async def add_education(
    education: EducationItem,
    current_user: dict = Depends(get_current_candidate)
):
    """Add education to candidate's profile"""
    candidates_collection = get_collection("candidates")
    
    result = candidates_collection.update_one(
        {"email": current_user["email"]},
        {"$push": {"education": education.model_dump()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    return {"message": "Education added successfully"}

@router.put("/me/education/{degree}", response_model=dict)
async def update_education(
    degree: str,
    updated_education: EducationItem,
    current_user: dict = Depends(get_current_candidate)
):
    """Update education item by degree"""
    candidates_collection = get_collection("candidates")
    
    result = candidates_collection.update_one(
        {"email": current_user["email"], "education.degree": degree},
        {"$set": {"education.$": updated_education.model_dump()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Education not found"
        )
    
    return {"message": "Education updated successfully"}

@router.delete("/me/education/{degree}", response_model=dict)
async def delete_education(
    degree: str,
    current_user: dict = Depends(get_current_candidate)
):
    """Delete an education item by degree"""
    candidates_collection = get_collection("candidates")
    
    result = candidates_collection.update_one(
        {"email": current_user["email"]},
        {"$pull": {"education": {"degree": degree}}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Education not found"
        )
    
    return {"message": "Education deleted successfully"}


@router.post("/me/experience", response_model=dict)
async def add_experience(
    experience: ExperienceItem,
    current_user: dict = Depends(get_current_candidate)
):
    """Add work experience to candidate's profile"""
    candidates_collection = get_collection("candidates")

    # Convert date -> datetime
    exp_data = experience.model_dump()
    exp_data["start_date"] = datetime.combine(exp_data["start_date"], datetime.min.time())
    if exp_data.get("end_date"):
        exp_data["end_date"] = datetime.combine(exp_data["end_date"], datetime.min.time())

    result = candidates_collection.update_one(
        {"email": current_user["email"]},
        {"$push": {"experience": exp_data}}
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )

    return {"message": "Experience added successfully"}

@router.put("/me/experience/{role}", response_model=dict)
async def update_experience(
    role: str,
    updated_experience: ExperienceItem,
    current_user: dict = Depends(get_current_candidate)
):
    """Update an existing work experience by role"""
    candidates_collection = get_collection("candidates")

    exp_data = updated_experience.model_dump()
    exp_data["start_date"] = datetime.combine(exp_data["start_date"], datetime.min.time())
    if exp_data.get("end_date"):
        exp_data["end_date"] = datetime.combine(exp_data["end_date"], datetime.min.time())

    result = candidates_collection.update_one(
        {"email": current_user["email"], "experience.role": role},
        {"$set": {"experience.$": exp_data}}
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experience not found"
        )

    return {"message": "Experience updated successfully"}

@router.delete("/me/experience/{role}", response_model=dict)
async def delete_experience(
    role: str,
    current_user: dict = Depends(get_current_candidate)
):
    """Delete an experience item by role"""
    candidates_collection = get_collection("candidates")
    
    result = candidates_collection.update_one(
        {"email": current_user["email"]},
        {"$pull": {"experience": {"role": role}}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Experience not found"
        )
    
    return {"message": "Experience deleted successfully"}
