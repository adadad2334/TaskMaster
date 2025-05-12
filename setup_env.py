#!/usr/bin/env python3
"""
Скрипт для настройки среды разработки TaskMaster.

Этот скрипт создает виртуальную среду (если она не существует),
устанавливает или обновляет зависимости и создает базу данных.
"""

import os
import sys
import subprocess
import platform
import venv
from pathlib import Path


def run_command(command, cwd=None):
    """Запускает команду и возвращает её вывод."""
    print(f"Выполнение: {command}")
    result = subprocess.run(command, shell=True, cwd=cwd, 
                           capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Ошибка ({result.returncode}):")
        print(result.stderr)
        return False, result.stderr
    return True, result.stdout


def get_python_version():
    """Получает версию Python."""
    major = sys.version_info.major
    minor = sys.version_info.minor
    return f"{major}.{minor}"


def create_venv():
    """Создает виртуальную среду, если она не существует."""
    venv_path = Path("taskmaster_env")
    if venv_path.exists():
        print("Виртуальная среда уже существует.")
        return True
    
    print("Создание виртуальной среды...")
    try:
        venv.create(venv_path, with_pip=True)
        print("Виртуальная среда успешно создана.")
        return True
    except Exception as e:
        print(f"Ошибка при создании виртуальной среды: {e}")
        return False


def install_dependencies():
    """Устанавливает зависимости из requirements.txt."""
    if platform.system() == "Windows":
        pip_path = Path("taskmaster_env/Scripts/pip")
    else:
        pip_path = Path("taskmaster_env/bin/pip")
        
    # Убедимся, что pip установлен и обновлен
    success, _ = run_command(f"{pip_path} install --upgrade pip")
    if not success:
        return False
        
    # Устанавливаем зависимости из requirements.txt
    success, _ = run_command(f"{pip_path} install -r requirements.txt")
    if not success:
        return False
        
    # Проверяем версию Python и при необходимости обновляем библиотеки
    python_version = get_python_version()
    major, minor = map(int, python_version.split('.'))
    if major >= 3 and minor >= 13:
        print("Обнаружена версия Python 3.13+. Обновление библиотек до совместимых версий...")
        success, _ = run_command(
            f"{pip_path} install fastapi>=0.104.1 uvicorn>=0.24.0 "
            f"sqlalchemy>=2.0.27 pydantic>=2.4.0"
        )
        if not success:
            return False
    
    return True


def setup_database():
    """Создает базу данных и таблицы."""
    # Создаем базу данных, если она не существует
    db_file = Path("taskmaster.db")
    if not db_file.exists():
        print("Создание базы данных...")
        # Создаем пустой файл базы данных
        db_file.touch()
    
    # Создаем .env файл, если он не существует
    env_file = Path(".env")
    if not env_file.exists():
        print("Создание файла .env...")
        with open(env_file, "w") as f:
            f.write("DATABASE_URL=sqlite:///./taskmaster.db\n")
            f.write("SECRET_KEY=your-secret-key-here\n")
    
    # Запускаем скрипт для создания таблиц
    create_tables_script = """
from app.database import engine, Base
Base.metadata.create_all(bind=engine)
print("Таблицы базы данных успешно созданы.")
"""
    with open("create_tables.py", "w") as f:
        f.write(create_tables_script)
    
    # Выполняем скрипт через виртуальное окружение Python
    if platform.system() == "Windows":
        python_path = Path("taskmaster_env/Scripts/python")
    else:
        python_path = Path("taskmaster_env/bin/python")
    
    success, output = run_command(f"{python_path} create_tables.py")
    if success:
        print(output)
        # Удаляем временный скрипт
        os.remove("create_tables.py")
        return True
    return False


def main():
    """Основная функция скрипта."""
    print("Настройка среды TaskMaster")
    print("=" * 50)
    
    # Создаем виртуальную среду
    if not create_venv():
        sys.exit(1)
    
    # Устанавливаем зависимости
    if not install_dependencies():
        sys.exit(1)
    
    # Настраиваем базу данных
    if not setup_database():
        sys.exit(1)
    
    print("=" * 50)
    print("Настройка среды успешно завершена!")
    print("\nДля запуска приложения:")
    if platform.system() == "Windows":
        print("  1. Активируйте виртуальную среду: .\\taskmaster_env\\Scripts\\activate")
    else:
        print("  1. Активируйте виртуальную среду: source taskmaster_env/bin/activate")
    print("  2. Запустите приложение: uvicorn app.main:app --reload")
    print("  3. Откройте в браузере: http://localhost:8000/docs")


if __name__ == "__main__":
    main() 