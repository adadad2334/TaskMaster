# ER-диаграмма проекта TaskMaster

```mermaid
erDiagram
    USER {
        int id PK
        string username
        string email
        string hashed_password
        boolean is_active
        datetime created_at
        float workload_capacity
        float current_workload
    }
    
    PROJECT {
        int id PK
        string name
        string description
        datetime created_at
    }
    
    TASK {
        int id PK
        string title
        string description
        enum status
        enum priority
        datetime created_at
        datetime updated_at
        datetime due_date
        float estimated_hours
        int project_id FK
        int assignee_id FK
    }
    
    SKILL {
        int id PK
        string name
        string description
    }
    
    PROJECT_USER {
        int user_id FK
        int project_id FK
    }
    
    USER_SKILL {
        int user_id FK
        int skill_id FK
        int level
    }
    
    TASK_SKILL {
        int task_id FK
        int skill_id FK
        int required_level
    }
    
    USER ||--o{ TASK : "выполняет"
    PROJECT ||--o{ TASK : "содержит"
    
    USER }|--|| PROJECT_USER : "участвует"
    PROJECT }|--|| PROJECT_USER : "имеет участников"
    
    USER }|--|| USER_SKILL : "обладает"
    SKILL }|--|| USER_SKILL : "принадлежит"
    
    TASK }|--|| TASK_SKILL : "требует"
    SKILL }|--|| TASK_SKILL : "требуется для"
```

## Описание сущностей и связей

### Основные сущности:

1. **User** (Пользователь)
   - Основные атрибуты: id, username, email, hashed_password
   - Дополнительные атрибуты: workload_capacity (максимальная нагрузка), current_workload (текущая нагрузка)

2. **Project** (Проект)
   - Атрибуты: id, name, description, created_at

3. **Task** (Задача)
   - Основные атрибуты: id, title, description, status, priority
   - Временные атрибуты: created_at, updated_at, due_date (срок)
   - Трудоемкость: estimated_hours (оценка в часах)
   - Связи: project_id (проект), assignee_id (исполнитель)

4. **Skill** (Навык)
   - Атрибуты: id, name, description

### Связующие таблицы:

1. **PROJECT_USER** - связь многие-ко-многим между пользователями и проектами
   - user_id, project_id

2. **USER_SKILL** - связь многие-ко-многим между пользователями и навыками
   - user_id, skill_id, level (уровень навыка от 1 до 5)

3. **TASK_SKILL** - связь многие-ко-многим между задачами и навыками
   - task_id, skill_id, required_level (требуемый уровень навыка)

### Основные связи:

- Пользователь может быть участником многих проектов, проект может иметь много участников
- Пользователь может выполнять много задач, задача назначается одному исполнителю
- Проект содержит много задач, задача принадлежит одному проекту
- Пользователь может обладать многими навыками, навык может быть у многих пользователей
- Задача может требовать многих навыков, навык может требоваться для многих задач 