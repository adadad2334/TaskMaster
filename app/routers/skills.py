"""
Skills router module.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, crud
from ..database import get_db
from ..auth import get_current_active_user

router = APIRouter(
    prefix="/skills",
    tags=["skills"],
    dependencies=[Depends(get_current_active_user)]
)

@router.post("/", response_model=schemas.Skill)
def create_skill(skill: schemas.SkillCreate, db: Session = Depends(get_db),
                current_user: models.User = Depends(get_current_active_user)):
    # Проверяем, не существует ли уже навык с таким именем
    db_skill = crud.get_skill_by_name(db, name=skill.name)
    if db_skill:
        raise HTTPException(status_code=400, detail="Skill already exists")
    
    return crud.create_skill(db=db, skill=skill)

@router.get("/", response_model=List[schemas.Skill])
def read_skills(skip: int = 0, limit: int = 100, db: Session = Depends(get_db),
               current_user: models.User = Depends(get_current_active_user)):
    skills = crud.get_skills(db, skip=skip, limit=limit)
    return skills

@router.get("/{skill_id}", response_model=schemas.Skill)
def read_skill(skill_id: int, db: Session = Depends(get_db),
              current_user: models.User = Depends(get_current_active_user)):
    db_skill = crud.get_skill(db, skill_id=skill_id)
    if db_skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return db_skill

@router.delete("/{skill_id}", response_model=bool)
def delete_skill(skill_id: int, db: Session = Depends(get_db),
                current_user: models.User = Depends(get_current_active_user)):
    # Сначала проверяем, существует ли навык
    db_skill = crud.get_skill(db, skill_id=skill_id)
    if db_skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    result = crud.delete_skill(db, skill_id=skill_id)
    return result

@router.put("/{skill_id}", response_model=schemas.Skill)
def update_skill(
    skill_id: int,
    skill: schemas.SkillCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_active_user)
):
    """
    Update a skill.
    """
    db_skill = crud.get_skill(db, skill_id)
    if db_skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    # Update skill fields
    db_skill.name = skill.name
    db_skill.description = skill.description
    
    db.commit()
    db.refresh(db_skill)
    return db_skill 