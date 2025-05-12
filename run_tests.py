#!/usr/bin/env python3
import subprocess
import sys


def run_tests():
    """Запускает тесты и генерирует отчет о покрытии"""
    print("Запуск тестов с проверкой покрытия...")
    
    try:
        # Устанавливаем pytest-cov если он не установлен
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest-cov"], check=True)
        
        # Запускаем тесты с покрытием
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "--cov=app", 
            "--cov-report=term", 
            "--cov-report=html:coverage_html"
        ], check=False)
        
        if result.returncode == 0:
            print("\n✅ Все тесты пройдены успешно!")
        else:
            print("\n❌ Некоторые тесты не прошли.")
            
        # Проверяем покрытие
        cov_result = subprocess.run([
            sys.executable, "-m", "coverage", "report", "--fail-under=70"
        ], check=False)
        
        if cov_result.returncode == 0:
            print("✅ Покрытие тестами достаточное (>= 70%)")
        else:
            print("❌ Покрытие тестами недостаточное (< 70%)")
            
        print("\nПодробный отчет о покрытии сохранен в директории 'coverage_html'")
        
        # Запускаем pylint
        print("\nЗапуск проверки кода с pylint...")
        pylint_result = subprocess.run([
            sys.executable, "-m", "pip", "install", "pylint"
        ], check=True)
        
        pylint_result = subprocess.run([
            sys.executable, "-m", "pylint", "app", "--output-format=text", "--reports=y"
        ], check=False, capture_output=True, text=True)
        
        # Сохраняем результат в файл
        with open('pylint.txt', 'w') as f:
            f.write(pylint_result.stdout)
        
        print(f"Результаты проверки pylint сохранены в файле 'pylint.txt'")
        
        # Выводим общую оценку pylint
        score_line = next((line for line in pylint_result.stdout.split('\n') if 'Your code has been rated at' in line), None)
        if score_line:
            print(score_line)
        
        return result.returncode
        
    except Exception as e:
        print(f"Ошибка при запуске тестов: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests())