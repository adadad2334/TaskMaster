from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta

from .. import crud, models, schemas, auth
from ..database import get_db

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)

@router.post("/register", response_model=schemas.User)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    db_email = crud.get_user_by_email(db, email=user.email)
    if db_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    return crud.create_user(db=db, user=user)

@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Создаем access token с временем жизни 30 минут
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(auth.get_current_active_user)):
    return current_user

@router.get("/", response_model=List[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db),
               current_user: models.User = Depends(auth.get_current_active_user)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users

@router.get("/{user_id}", response_model=schemas.UserWithSkills)
def read_user(user_id: int, db: Session = Depends(get_db),
              current_user: models.User = Depends(auth.get_current_active_user)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.put("/{user_id}", response_model=schemas.User)
def update_user(user_id: int, user: schemas.UserUpdate, db: Session = Depends(get_db),
                current_user: models.User = Depends(auth.get_current_active_user)):
    # Только администратор или сам пользователь может обновить свой профиль
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    db_user = crud.update_user(db, user_id=user_id, user=user)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.delete("/{user_id}", response_model=bool)
def delete_user(user_id: int, db: Session = Depends(get_db),
                current_user: models.User = Depends(auth.get_current_active_user)):
    # Только администратор или сам пользователь может удалить свой профиль
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    result = crud.delete_user(db, user_id=user_id)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    return result

@router.post("/{user_id}/skills/{skill_id}", response_model=schemas.UserWithSkills)
def add_skill_to_user(user_id: int, skill_id: int, level: int = 1, db: Session = Depends(get_db),
                       current_user: models.User = Depends(auth.get_current_active_user)):
    # Проверяем, что пользователь имеет право добавлять навыки себе
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Проверяем, что уровень навыка в пределах от 1 до 5
    if level < 1 or level > 5:
        raise HTTPException(status_code=400, detail="Skill level must be between 1 and 5")
    
    db_user = crud.add_skill_to_user(db, user_id=user_id, skill_id=skill_id, level=level)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User or skill not found")
    return db_user

@router.delete("/{user_id}/skills/{skill_id}", response_model=schemas.UserWithSkills)
def remove_skill_from_user(user_id: int, skill_id: int, db: Session = Depends(get_db),
                           current_user: models.User = Depends(auth.get_current_active_user)):
    # Проверяем, что пользователь имеет право удалять навыки у себя
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    db_user = crud.remove_skill_from_user(db, user_id=user_id, skill_id=skill_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User or skill not found")
    return db_user 