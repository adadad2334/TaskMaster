import pytest
from sqlalchemy.orm import Session
from app import crud, models, schemas
from .conftest import test_db_session, auth_headers

def test_get_project_tasks(test_db_session: Session):
    # Создаем проект
    project = crud.create_project(
        db=test_db_session,
        project=schemas.ProjectCreate(
            name="Test Project",
            description="Test Description"
        )
    )
    
    # Создаем задачи в проекте
    for i in range(3):
        crud.create_task(
            db=test_db_session,
            task=schemas.TaskCreate(
                title=f"Task {i}",
                description=f"Description {i}",
                project_id=project.id,
                status=models.TaskStatus.TODO,
                priority=models.TaskPriority.MEDIUM,
                estimated_hours=5.0
            )
        )
    
    # Получаем задачи проекта
    tasks = crud.get_project_tasks(test_db_session, project.id)
    
    # Проверяем, что все задачи получены
    assert len(tasks) == 3
    for task in tasks:
        assert task.project_id == project.id

def test_get_user_tasks(test_db_session: Session):
    # Создаем нового пользователя вместо получения существующего
    user = crud.create_user(
        db=test_db_session,
        user=schemas.UserCreate(
            username="taskuser",
            email="taskuser@example.com",
            password="password123",
            workload_capacity=100.0,
            current_workload=0.0
        )
    )
    
    # Создаем проект
    project = crud.create_project(
        db=test_db_session,
        project=schemas.ProjectCreate(
            name="Test Project",
            description="Test Description"
        )
    )
    
    # Создаем задачи и назначаем их пользователю
    for i in range(3):
        task = crud.create_task(
            db=test_db_session,
            task=schemas.TaskCreate(
                title=f"Task {i}",
                description=f"Description {i}",
                project_id=project.id,
                status=models.TaskStatus.TODO,
                priority=models.TaskPriority.MEDIUM,
                estimated_hours=5.0
            )
        )
        # Назначаем задачу пользователю
        crud.update_task(
            db=test_db_session,
            task_id=task.id,
            task=schemas.TaskUpdate(assignee_id=user.id)
        )
    
    # Получаем задачи пользователя
    tasks = crud.get_user_tasks(test_db_session, user.id)
    
    # Проверяем, что все задачи получены
    assert len(tasks) == 3
    for task in tasks:
        assert task.assignee_id == user.id

def test_get_skill_by_name(test_db_session: Session):
    # Создаем навык
    skill_name = "Python"
    skill = crud.create_skill(
        db=test_db_session,
        skill=schemas.SkillCreate(
            name=skill_name,
            description="Python programming language"
        )
    )
    
    # Получаем навык по имени
    db_skill = crud.get_skill_by_name(test_db_session, skill_name)
    
    # Проверяем, что навык найден
    assert db_skill is not None
    assert db_skill.name == skill_name
    assert db_skill.id == skill.id

def test_add_skill_to_task(test_db_session: Session):
    # Создаем навык
    skill = crud.create_skill(
        db=test_db_session,
        skill=schemas.SkillCreate(
            name="Python",
            description="Python programming language"
        )
    )
    
    # Создаем проект
    project = crud.create_project(
        db=test_db_session,
        project=schemas.ProjectCreate(
            name="Test Project",
            description="Test Description"
        )
    )
    
    # Создаем задачу
    task = crud.create_task(
        db=test_db_session,
        task=schemas.TaskCreate(
            title="Task with Skill",
            description="Task requiring Python",
            project_id=project.id,
            status=models.TaskStatus.TODO,
            priority=models.TaskPriority.MEDIUM,
            estimated_hours=5.0
        )
    )
    
    # Добавляем навык к задаче
    result = crud.add_skill_to_task(test_db_session, task.id, skill.id, required_level=4)
    
    # Проверяем результат
    assert result is not None
    assert skill in result.required_skills
    
    # Проверяем, что уровень навыка установлен правильно
    task_skill = test_db_session.query(models.task_skill).filter(
        models.task_skill.c.task_id == task.id,
        models.task_skill.c.skill_id == skill.id
    ).first()
    
    assert task_skill is not None
    assert task_skill.required_level == 4

def test_remove_skill_from_task(test_db_session: Session):
    # Создаем навык
    skill = crud.create_skill(
        db=test_db_session,
        skill=schemas.SkillCreate(
            name="Python",
            description="Python programming language"
        )
    )
    
    # Создаем проект
    project = crud.create_project(
        db=test_db_session,
        project=schemas.ProjectCreate(
            name="Test Project",
            description="Test Description"
        )
    )
    
    # Создаем задачу с навыком
    task = crud.create_task(
        db=test_db_session,
        task=schemas.TaskCreate(
            title="Task with Skill",
            description="Task requiring Python",
            project_id=project.id,
            status=models.TaskStatus.TODO,
            priority=models.TaskPriority.MEDIUM,
            estimated_hours=5.0,
            required_skills=[skill.id]
        )
    )
    
    # Проверяем, что навык добавлен
    assert skill in task.required_skills
    
    # Удаляем навык
    result = crud.remove_skill_from_task(test_db_session, task.id, skill.id)
    
    # Проверяем результат
    assert result is not None
    assert skill not in result.required_skills

def test_update_task_status(test_db_session: Session):
    # Создаем проект
    project = crud.create_project(
        db=test_db_session,
        project=schemas.ProjectCreate(
            name="Test Project",
            description="Test Description"
        )
    )
    
    # Создаем задачу
    task = crud.create_task(
        db=test_db_session,
        task=schemas.TaskCreate(
            title="Task",
            description="Task description",
            project_id=project.id,
            status=models.TaskStatus.TODO,
            priority=models.TaskPriority.MEDIUM,
            estimated_hours=5.0
        )
    )
    
    # Обновляем статус задачи
    updated_task = crud.update_task_status(
        db=test_db_session,
        task_id=task.id,
        status=models.TaskStatus.IN_PROGRESS
    )
    
    # Проверяем результат
    assert updated_task is not None
    assert updated_task.status == models.TaskStatus.IN_PROGRESS
    
    # Обновляем статус задачи на DONE и устанавливаем completed_at
    updated_task = crud.update_task_status(
        db=test_db_session,
        task_id=task.id,
        status=models.TaskStatus.DONE
    )
    
    # Проверяем, что completed_at установлено
    assert updated_task.status == models.TaskStatus.DONE
    assert updated_task.completed_at is not None

def test_get_project_by_name(test_db_session: Session):
    # Создаем проект с уникальным именем
    project_name = "Unique Project Name"
    project = crud.create_project(
        db=test_db_session,
        project=schemas.ProjectCreate(
            name=project_name,
            description="Project with unique name"
        )
    )
    
    # Получаем проект по имени
    db_project = crud.get_project_by_name(test_db_session, project_name)
    
    # Проверяем, что проект найден
    assert db_project is not None
    assert db_project.name == project_name
    assert db_project.id == project.id 