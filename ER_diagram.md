# ER-диаграмма проекта TaskMaster

```mermaid
erDiagram
    USER {
        int id PK "Первичный ключ"
        string username "Уникальное имя пользователя"
        string email "Email пользователя"
        string hashed_password "Хешированный пароль"
        boolean is_active "Статус активности"
        datetime created_at "Дата создания"
        float workload_capacity "Максимальная нагрузка"
        float current_workload "Текущая нагрузка"
    }
    
    PROJECT {
        int id PK "Первичный ключ"
        string name "Название проекта"
        string description "Описание проекта"
        datetime created_at "Дата создания"
        string status "Статус проекта"
    }
    
    TASK {
        int id PK "Первичный ключ"
        string title "Название задачи"
        string description "Описание задачи"
        enum status "Статус: NEW, IN_PROGRESS, REVIEW, DONE"
        enum priority "Приоритет: LOW, MEDIUM, HIGH, CRITICAL"
        datetime created_at "Дата создания"
        datetime updated_at "Дата обновления"
        datetime due_date "Срок выполнения"
        float estimated_hours "Оценка трудозатрат"
        int project_id FK "ID проекта"
        int assignee_id FK "ID исполнителя"
    }
    
    SKILL {
        int id PK "Первичный ключ"
        string name "Название навыка"
        string description "Описание навыка"
        string category "Категория навыка"
    }
    
    PROJECT_USER {
        int user_id FK "ID пользователя"
        int project_id FK "ID проекта"
        string role "Роль в проекте"
        datetime joined_at "Дата присоединения"
    }
    
    USER_SKILL {
        int user_id FK "ID пользователя"
        int skill_id FK "ID навыка"
        int level "Уровень (1-5)"
        datetime acquired_at "Дата получения"
    }
    
    TASK_SKILL {
        int task_id FK "ID задачи"
        int skill_id FK "ID навыка"
        int required_level "Требуемый уровень"
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
   - Дополнительные атрибуты: 
     - workload_capacity (максимальная нагрузка)
     - current_workload (текущая нагрузка)
     - is_active (статус активности)
     - created_at (дата создания)

2. **Project** (Проект)
   - Атрибуты: 
     - id (первичный ключ)
     - name (название)
     - description (описание)
     - created_at (дата создания)
     - status (статус проекта)

3. **Task** (Задача)
   - Основные атрибуты: 
     - id (первичный ключ)
     - title (название)
     - description (описание)
     - status (статус: NEW, IN_PROGRESS, REVIEW, DONE)
     - priority (приоритет: LOW, MEDIUM, HIGH, CRITICAL)
   - Временные атрибуты: 
     - created_at (дата создания)
     - updated_at (дата обновления)
     - due_date (срок выполнения)
   - Трудоемкость: estimated_hours (оценка в часах)
   - Связи: 
     - project_id (проект)
     - assignee_id (исполнитель)

4. **Skill** (Навык)
   - Атрибуты: 
     - id (первичный ключ)
     - name (название)
     - description (описание)
     - category (категория навыка)

### Связующие таблицы:

1. **PROJECT_USER** - связь многие-ко-многим между пользователями и проектами
   - user_id (ID пользователя)
   - project_id (ID проекта)
   - role (роль в проекте)
   - joined_at (дата присоединения)

2. **USER_SKILL** - связь многие-ко-многим между пользователями и навыками
   - user_id (ID пользователя)
   - skill_id (ID навыка)
   - level (уровень навыка от 1 до 5)
   - acquired_at (дата получения навыка)

3. **TASK_SKILL** - связь многие-ко-многим между задачами и навыками
   - task_id (ID задачи)
   - skill_id (ID навыка)
   - required_level (требуемый уровень навыка)

### Основные связи:

- Пользователь может быть участником многих проектов, проект может иметь много участников
- Пользователь может выполнять много задач, задача назначается одному исполнителю
- Проект содержит много задач, задача принадлежит одному проекту
- Пользователь может обладать многими навыками, навык может быть у многих пользователей
- Задача может требовать многих навыков, навык может требоваться для многих задач 