from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from . import models
from .database import engine, get_db
from .routers import users, projects, tasks, skills, assign

# Создаем таблицы в БД при первом запуске
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TaskMaster API",
    description="API для управления задачами с оптимальным распределением нагрузки между исполнителями",
    version="1.0.0",
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
    return {
        "message": "Welcome to TaskMaster API",
        "docs": "/docs",
        "redoc": "/redoc"
    }

# Эндпоинт для проверки соединения с БД
@app.get("/ping", tags=["healthcheck"])
async def ping_db(db = Depends(get_db)):
    try:
        # Пытаемся выполнить простой запрос к БД
        db.execute("SELECT 1")
        return {"status": "ok", "message": "Database connection successful"}
    except Exception as e:
        return {"status": "error", "message": str(e)}