from sqlalchemy.orm import Session
from . import models, schemas, crud
from typing import List, Dict, Tuple
import math
import logging
from datetime import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaskAssignmentOptimizer:
    """
    Класс для оптимального распределения задач между исполнителями
    Использует модифицированный Hungarian algorithm (алгоритм Венгерской матрицы)
    для решения задачи о назначениях (assignment problem)
    """
    
    def __init__(self, db: Session, project_id: int, optimize_for: str = "balanced"):
        self.db = db
        self.project_id = project_id
        self.optimize_for = optimize_for  # balanced, workload, skills, priority
        
        # Получаем все задачи проекта, которые не назначены или находятся в статусе TODO
        self.tasks = db.query(models.Task).filter(
            models.Task.project_id == project_id,
            models.Task.status == models.TaskStatus.TODO,
            models.Task.assignee_id.is_(None)
        ).all()
        
        # Получаем всех участников проекта
        project = crud.get_project(db, project_id)
        if not project:
            raise ValueError(f"Project with id {project_id} not found")
        
        self.users = project.members
        
        if not self.tasks:
            logger.info(f"No unassigned tasks found in project {project_id}")
        
        if not self.users:
            logger.info(f"No members found in project {project_id}")
    
    def calculate_cost_matrix(self) -> List[List[float]]:
        """
        Создаем матрицу стоимости для каждой пары (задача, пользователь)
        Меньшее значение означает лучшее соответствие
        
        Матрица будет иметь размер len(tasks) x len(users)
        """
        cost_matrix = []
        
        for task in self.tasks:
            task_costs = []
            for user in self.users:
                # Рассчитываем стоимость назначения на основе различных факторов
                cost = self._calculate_assignment_cost(task, user)
                task_costs.append(cost)
            cost_matrix.append(task_costs)
        
        return cost_matrix
    
    def _calculate_assignment_cost(self, task: models.Task, user: models.User) -> float:
        """
        Рассчитываем "стоимость" назначения задачи пользователю
        Меньшее значение означает лучшее соответствие
        
        Учитываем:
        1. Загруженность пользователя
        2. Соответствие навыков задачи и пользователя
        3. Приоритет задачи
        4. Срок выполнения (если есть)
        """
        # Начальная стоимость
        cost = 100.0
        
        # Коэффициенты важности разных факторов (сумма = 1)
        workload_weight = 0.3
        skills_weight = 0.4
        priority_weight = 0.2
        deadline_weight = 0.1
        
        # Корректируем веса в зависимости от стратегии оптимизации
        if self.optimize_for == "workload":
            workload_weight = 0.6
            skills_weight = 0.2
            priority_weight = 0.1
            deadline_weight = 0.1
        elif self.optimize_for == "skills":
            workload_weight = 0.1
            skills_weight = 0.6
            priority_weight = 0.2
            deadline_weight = 0.1
        elif self.optimize_for == "priority":
            workload_weight = 0.1
            skills_weight = 0.3
            priority_weight = 0.5
            deadline_weight = 0.1
        
        # 1. Фактор загруженности (0-100)
        # Чем выше загруженность пользователя относительно его capacity, тем выше стоимость
        workload_ratio = user.current_workload / user.workload_capacity if user.workload_capacity > 0 else 1.0
        workload_cost = 100 * workload_ratio
        
        # 2. Фактор навыков (0-100)
        # Чем больше совпадающих навыков, тем ниже стоимость
        skills_cost = self._calculate_skills_cost(task, user)
        
        # 3. Фактор приоритета (0-100)
        # Для задач с высоким приоритетом пользователи с низкой загрузкой получают преимущество
        priority_values = {
            models.TaskPriority.LOW: 25,
            models.TaskPriority.MEDIUM: 50,
            models.TaskPriority.HIGH: 75,
            models.TaskPriority.CRITICAL: 100
        }
        
        priority_value = priority_values.get(task.priority, 50)
        priority_cost = 100 - (priority_value * (1 - workload_ratio))
        
        # 4. Фактор дедлайна (0-100)
        # Чем ближе дедлайн, тем ниже стоимость для менее загруженных пользователей
        deadline_cost = 50  # по умолчанию
        if task.due_date:
            days_until_due = (task.due_date - datetime.utcnow()).days
            if days_until_due <= 0:
                deadline_cost = 0  # срочная задача
            else:
                deadline_cost = min(100, days_until_due * 10)
        
        # Итоговая взвешенная стоимость
        cost = (
            workload_weight * workload_cost +
            skills_weight * skills_cost +
            priority_weight * priority_cost +
            deadline_weight * deadline_cost
        )
        
        return cost
    
    def _calculate_skills_cost(self, task: models.Task, user: models.User) -> float:
        """
        Рассчитываем стоимость на основе соответствия навыков
        Чем больше навыков пользователя соответствует требованиям задачи, тем ниже стоимость
        """
        # Если у задачи нет требуемых навыков, возвращаем среднюю стоимость
        if not task.required_skills:
            return 50
        
        # Получаем ID требуемых навыков задачи
        required_skill_ids = {skill.id: skill for skill in task.required_skills}
        
        # Проверяем, сколько требуемых навыков есть у пользователя
        user_skill_map = {}
        for skill in user.skills:
            # Получаем уровень навыка пользователя
            user_skill_level = self.db.query(models.user_skill).filter(
                models.user_skill.c.user_id == user.id,
                models.user_skill.c.skill_id == skill.id
            ).first()
            
            if user_skill_level:
                user_skill_map[skill.id] = user_skill_level.level
        
        # Рассчитываем процент соответствия навыков
        total_match = 0
        total_required = len(required_skill_ids)
        
        for skill_id, skill in required_skill_ids.items():
            # Получаем требуемый уровень навыка для задачи
            required_level = self.db.query(models.task_skill).filter(
                models.task_skill.c.task_id == task.id,
                models.task_skill.c.skill_id == skill_id
            ).first()
            
            required_level_value = required_level.required_level if required_level else 1
            
            if skill_id in user_skill_map:
                user_level = user_skill_map[skill_id]
                # Если уровень пользователя выше или равен требуемому, полное соответствие
                if user_level >= required_level_value:
                    total_match += 1
                else:
                    # Частичное соответствие
                    total_match += user_level / required_level_value
        
        # Если нет навыков, стоимость высокая
        if total_required == 0:
            return 50
        
        # Процент соответствия от 0 до 1
        match_percentage = total_match / total_required
        
        # Инвертируем: 0% соответствия -> 100 стоимость, 100% соответствия -> 0 стоимость
        return 100 * (1 - match_percentage)
    
    def hungarian_algorithm(self, cost_matrix: List[List[float]]) -> List[Tuple[int, int]]:
        """
        Реализация венгерского алгоритма для задачи о назначениях
        Возвращает список пар (индекс_задачи, индекс_пользователя)
        """
        if not cost_matrix or not cost_matrix[0]:
            return []
        
        # Копируем матрицу, чтобы не изменять оригинал
        matrix = [row[:] for row in cost_matrix]
        n_tasks = len(matrix)
        n_users = len(matrix[0])
        
        # Для работы алгоритма матрица должна быть квадратной
        # Если задач больше чем пользователей, добавляем фиктивных пользователей
        # Если пользователей больше чем задач, добавляем фиктивные задачи
        max_dim = max(n_tasks, n_users)
        
        # Расширяем матрицу до квадратной
        for i in range(n_tasks):
            if len(matrix[i]) < max_dim:
                matrix[i].extend([float('inf')] * (max_dim - len(matrix[i])))
        
        while len(matrix) < max_dim:
            matrix.append([float('inf')] * max_dim)
        
        # Шаг 1: Вычитаем минимальный элемент из каждой строки
        for i in range(max_dim):
            min_val = min(matrix[i])
            for j in range(max_dim):
                matrix[i][j] -= min_val
        
        # Шаг 2: Вычитаем минимальный элемент из каждого столбца
        for j in range(max_dim):
            min_val = min(matrix[i][j] for i in range(max_dim))
            for i in range(max_dim):
                matrix[i][j] -= min_val
        
        # Шаг 3: Находим минимальное покрытие линиями всех нулей
        # и итеративно улучшаем решение, пока не найдем оптимальное назначение
        line_count = 0
        row_covered = [False] * max_dim
        col_covered = [False] * max_dim
        
        while line_count < max_dim:
            # Находим минимальное покрытие нулей линиями
            line_count = self._find_min_cover(matrix, row_covered, col_covered)
            
            if line_count >= max_dim:
                break
            
            # Находим минимальное значение среди непокрытых элементов
            min_val = float('inf')
            for i in range(max_dim):
                if not row_covered[i]:
                    for j in range(max_dim):
                        if not col_covered[j] and matrix[i][j] < min_val:
                            min_val = matrix[i][j]
            
            # Вычитаем минимальное значение из всех непокрытых элементов
            # и добавляем его ко всем элементам, покрытым дважды
            for i in range(max_dim):
                for j in range(max_dim):
                    if not row_covered[i] and not col_covered[j]:
                        matrix[i][j] -= min_val
                    elif row_covered[i] and col_covered[j]:
                        matrix[i][j] += min_val
        
        # Шаг 4: Находим оптимальное назначение
        assignments = []
        for i in range(max_dim):
            for j in range(max_dim):
                if matrix[i][j] == 0 and i < n_tasks and j < n_users:
                    # Проверяем, не назначена ли уже эта задача или пользователь
                    if not any(a[0] == i for a in assignments) and not any(a[1] == j for a in assignments):
                        assignments.append((i, j))
                        break
        
        return assignments
    
    def _find_min_cover(self, matrix, row_covered, col_covered):
        """
        Находит минимальное количество линий, покрывающих все нули в матрице
        """
        max_dim = len(matrix)
        
        # Сначала сбрасываем все покрытия
        for i in range(max_dim):
            row_covered[i] = False
            col_covered[i] = False
        
        # Шаг 1: Отмечаем каждую строку, у которой нет отмеченного нуля
        row_has_zero = [False] * max_dim
        col_has_zero = [False] * max_dim
        
        for i in range(max_dim):
            for j in range(max_dim):
                if matrix[i][j] == 0:
                    row_has_zero[i] = True
                    col_has_zero[j] = True
        
        # Пока есть непокрытый ноль, отмечаем строки и столбцы
        while True:
            # Покрываем строки без отмеченных нулей
            for i in range(max_dim):
                if not row_has_zero[i]:
                    row_covered[i] = True
            
            # Если все строки покрыты, выходим
            if all(row_covered):
                break
            
            # Покрываем столбцы с нулями в непокрытых строках
            for j in range(max_dim):
                for i in range(max_dim):
                    if matrix[i][j] == 0 and not row_covered[i]:
                        col_covered[j] = True
                        break
            
            # Если все столбцы покрыты, выходим
            if all(col_covered):
                break
            
            # Покрываем строки, у которых есть отмеченный ноль в покрытом столбце
            for i in range(max_dim):
                for j in range(max_dim):
                    if matrix[i][j] == 0 and col_covered[j]:
                        row_covered[i] = True
                        break
            
            # Если больше нечего покрывать, выходим
            break
        
        return sum(1 for covered in row_covered if covered) + sum(1 for covered in col_covered if covered)
    
    def optimize_assignments(self) -> List[schemas.TaskAssignmentResult]:
        """
        Основной метод, который выполняет оптимизацию назначений
        и возвращает список результатов назначения
        """
        if not self.tasks or not self.users:
            return []
        
        # Рассчитываем матрицу стоимости
        cost_matrix = self.calculate_cost_matrix()
        
        # Применяем венгерский алгоритм для поиска оптимальных назначений
        assignments = self.hungarian_algorithm(cost_matrix)
        
        # Преобразуем результаты в структуру TaskAssignmentResult
        result = []
        unassigned_tasks = []
        
        for task_idx, user_idx in assignments:
            if task_idx < len(self.tasks) and user_idx < len(self.users):
                task = self.tasks[task_idx]
                user = self.users[user_idx]
                
                # Вычисляем оценку соответствия (инвертируем стоимость)
                match_score = 100 - min(100, cost_matrix[task_idx][user_idx])
                
                result.append(schemas.TaskAssignmentResult(
                    task_id=task.id,
                    assignee_id=user.id,
                    assignee_username=user.username,
                    match_score=match_score
                ))
                
                # Применяем назначение в БД, если это не фиктивное назначение
                self._apply_assignment(task.id, user.id)
            
        # Проверяем незназначенные задачи
        assigned_task_indices = [i for i, _ in assignments]
        for i, task in enumerate(self.tasks):
            if i not in assigned_task_indices:
                unassigned_tasks.append(task.id)
        
        return result, unassigned_tasks
    
    def _apply_assignment(self, task_id: int, user_id: int):
        """
        Применяет назначение задачи пользователю в БД
        """
        # Обновляем задачу
        task_update = schemas.TaskUpdate(assignee_id=user_id)
        updated_task = crud.update_task(self.db, task_id, task_update)
        
        return updated_task


def assign_tasks(db: Session, project_id: int, optimize_for: str = "balanced") -> schemas.AutoAssignmentResponse:
    """
    Внешний API-метод для оптимизации назначений задач
    """
    try:
        optimizer = TaskAssignmentOptimizer(db, project_id, optimize_for)
        assignments, unassigned_tasks = optimizer.optimize_assignments()
        
        return schemas.AutoAssignmentResponse(
            assignments=assignments,
            unassigned_tasks=unassigned_tasks
        )
    except Exception as e:
        logger.error(f"Error during task assignment: {str(e)}")
        raise e 