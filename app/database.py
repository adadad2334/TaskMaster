"""
Модуль для работы с базой данных.

Этот модуль содержит настройки соединения с базой данных SQLAlchemy,
создание базового класса для всех моделей и зависимость для получения сессии БД.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Получаем URL подключения к БД из переменных окружения или используем значение по умолчанию
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./taskmaster.db"
)

# Создаем движок SQLAlchemy
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создаем базовый класс для моделей
Base = declarative_base()

def get_db():
    """
    Зависимость для получения сессии БД.
    
    Yields:
        Session: Сессия базы данных
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 