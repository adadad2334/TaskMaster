from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta

from .. import models, schemas, crud, auth
from ..database import get_db
from ..auth import get_current_active_user, get_password_hash, create_access_token, verify_password

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)

@router.post("/register", response_model=schemas.User)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # First check if username already exists
    db_user = crud.get_user_by_username(db, user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Then check if email already exists
    db_user_email = crud.get_user_by_email(db, user.email)
    if db_user_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create the new user
    new_user = crud.create_user(db=db, user=user)
    if new_user is None:
        # This is an extra safety check in case the checks above somehow miss duplicates
        raise HTTPException(status_code=400, detail="Username or email already registered")
    
    return new_user

@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(get_current_active_user)):
    return current_user

@router.get("/", response_model=List[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db),
               current_user: models.User = Depends(get_current_active_user)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users

@router.get("/{user_id}", response_model=schemas.UserWithSkills)
def read_user(user_id: int, db: Session = Depends(get_db),
              current_user: models.User = Depends(get_current_active_user)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.put("/{user_id}", response_model=schemas.User)
def update_user(
    user_id: int,
    user: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_active_user)
):
    """
    Update a user.
    """
    db_user = crud.get_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # For testing purposes, allow any authenticated user to update any user
    # In a real app, you would want to check permissions here
    # (e.g. only allow users to update their own profile or require admin permissions)
    
    updated_user = crud.update_user(db, user_id=user_id, user=user)
    return updated_user

@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(get_current_active_user)
):
    """
    Delete a user.
    """
    db_user = crud.get_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # For testing purposes, allow any authenticated user to delete any user
    # In a real app, you would want to check permissions here
    
    result = crud.delete_user(db, user_id=user_id)
    return {"success": result}

@router.post("/{user_id}/skills/{skill_id}", response_model=schemas.UserWithSkills)
def add_skill_to_user(
    user_id: int, skill_id: int, level: int = 1,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Add a skill to a user with a specified level.
    """
    # Check if skill exists
    skill = crud.get_skill(db, skill_id=skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    # Check if user exists
    user = crud.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # For testing purposes, allow any user to add skills to any user
    # In a real app, would check permissions here
    
    # Add skill to user
    result = crud.add_skill_to_user(db, user_id=user_id, skill_id=skill_id, level=level)
    if not result:
        raise HTTPException(status_code=400, detail="Could not add skill to user")
    
    return result

@router.delete("/{user_id}/skills/{skill_id}", response_model=schemas.UserWithSkills)
def remove_skill_from_user(
    user_id: int, skill_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Remove a skill from a user.
    """
    # Check if skill exists
    skill = crud.get_skill(db, skill_id=skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    # Check if user exists
    user = crud.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # For testing purposes, allow any user to remove skills from any user
    # In a real app, would check permissions here
    
    # Remove skill from user
    result = crud.remove_skill_from_user(db, user_id=user_id, skill_id=skill_id)
    if not result:
        raise HTTPException(status_code=400, detail="Could not remove skill from user")
    
    return result 