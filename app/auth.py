"""
Модуль аутентификации и авторизации.
Содержит функции для работы с паролями, генерации и проверки JWT токенов,
а также зависимости FastAPI для проверки авторизации пользователей.
"""

from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv
from jwt.exceptions import PyJWTError

from .database import get_db
from .models import User
from .schemas import TokenData

load_dotenv()

# Настройки для JWT
# В тестовой среде может быть переопределено в conftest.py
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет соответствие введенного пароля хешированному.
    
    Args:
        plain_password: Введенный пароль в открытом виде
        hashed_password: Хешированный пароль из базы данных
        
    Returns:
        bool: True если пароль соответствует, иначе False
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Создает хеш для пароля.
    
    Args:
        password: Пароль в открытом виде
        
    Returns:
        str: Хешированный пароль
    """
    return pwd_context.hash(password)

def get_user(db: Session, username: str) -> Optional[User]:
    """
    Получает пользователя по имени.
    
    Args:
        db: Сессия базы данных
        username: Имя пользователя
        
    Returns:
        Optional[User]: Объект пользователя или None, если пользователь не найден
    """
    return db.query(User).filter(User.username == username).first()

def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Аутентифицирует пользователя по имени и паролю.
    
    Args:
        db: Сессия базы данных
        username: Имя пользователя
        password: Пароль в открытом виде
        
    Returns:
        Optional[User]: Объект пользователя если аутентификация успешна, иначе None
    """
    user = get_user(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Создает JWT токен доступа.
    
    Args:
        data: Данные для кодирования в токене
        expires_delta: Время жизни токена
        
    Returns:
        str: JWT токен
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> TokenData:
    """
    Декодирует JWT токен.
    
    Args:
        token: JWT токен
        
    Returns:
        TokenData: Данные из токена
        
    Raises:
        HTTPException: Если токен невалидный
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token_data = TokenData(username=username)
        return token_data
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Получает текущего пользователя на основе JWT токена.
    
    Args:
        token: JWT токен из заголовка авторизации
        db: Сессия базы данных
        
    Returns:
        User: Текущий пользователь
        
    Raises:
        HTTPException: Если токен невалидный или пользователь не найден
    """
    token_data = decode_access_token(token)
    user = get_user(db, username=token_data.username)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
    
async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Проверяет, что текущий пользователь активен.
    
    Args:
        current_user: Текущий пользователь
        
    Returns:
        User: Активный текущий пользователь
        
    Raises:
        HTTPException: Если пользователь неактивен
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# End of file 