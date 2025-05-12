"""
Main application module.
This module initializes the FastAPI application and includes all routers.
"""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .routers import users, projects, tasks, skills, assign
from .database import engine, Base

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем таблицы в БД при первом запуске
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TaskMaster API",
    description="API для системы управления задачами с оптимизацией назначений",
    version="1.0.0"
)

# Добавляем CORS middleware для возможности использования API из веб-приложений
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшне здесь нужно указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(skills.router)
app.include_router(assign.router)

@app.get("/")
async def root():
    """Root endpoint returning API information."""
    return {"message": "Welcome to Task Assignment API", "docs": "/docs", "redoc": "/redoc"}

# Эндпоинт для проверки соединения с БД
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Проверка подключения к БД
        Base.metadata.create_all(bind=engine)
        return {"status": "healthy"}
    except Exception as e:
        logger.error("Health check failed: %s", str(e))
        raise HTTPException(status_code=503, detail="Service unavailable") from e