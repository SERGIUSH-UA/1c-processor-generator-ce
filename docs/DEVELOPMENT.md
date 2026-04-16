# 🛠️ Development Guide

Інструкції для розробників проекту 1c-processor-generator.

## 🚀 Швидкий старт для розробки

```bash
# 1. Клонувати репозиторій
git clone https://github.com/SERGIUSH-UA/1c-processor-generator.git
cd 1c-processor-generator

# 2. Встановити залежності для розробки
pip install -r requirements-dev.txt

# 3. Встановити pre-commit hooks
pre-commit install

# 4. Запустити тести
pytest tests/ -v
```

## 🧪 Тестування

### Запуск тестів

```bash
# Всі тести
pytest tests/ -v

# Конкретний файл
pytest tests/test_validators.py -v

# Конкретний тест
pytest tests/test_validators.py::TestValidateUUID::test_valid_uuids -v

# З coverage
pytest tests/ --cov=1c_processor_generator --cov-report=html

# Швидкий запуск (зупинка на першій помилці)
pytest tests/ -x --maxfail=1
```

### Auto-reload тестів (під час розробки)

```bash
# Встановити pytest-watch (якщо ще не встановлено)
pip install pytest-watch

# Запустити в окремому терміналі
ptw tests/

# Тепер при кожній зміні .py файлу тести автоматично перезапускаються
```

### Покриття коду

```bash
# Згенерувати HTML звіт
pytest tests/ --cov=1c_processor_generator --cov-report=html

# Відкрити в браузері
start htmlcov/index.html  # Windows
open htmlcov/index.html   # macOS
xdg-open htmlcov/index.html  # Linux
```

## 🔄 Pre-commit Hooks

Pre-commit hooks автоматично запускаються перед кожним комітом:

```bash
# Встановити hooks (один раз)
pre-commit install

# Запустити вручну на всіх файлах
pre-commit run --all-files

# Оновити версії hooks
pre-commit autoupdate

# Тимчасово пропустити hooks (не рекомендується)
git commit --no-verify
```

### Що перевіряють hooks:

1. **Trailing whitespace** - видаляє пробіли в кінці рядків
2. **End of file fixer** - додає новий рядок в кінці файлу
3. **YAML syntax** - перевіряє синтаксис YAML
4. **TOML syntax** - перевіряє синтаксис TOML
5. **Large files** - блокує файли > 1MB
6. **Merge conflicts** - перевіряє на конфлікти злиття
7. **Black** - форматує Python код
8. **isort** - сортує імпорти
9. **flake8** - лінтинг коду
10. **pytest** - запускає швидкі тести

## 🏗️ Tox - Тестування на різних Python версіях

```bash
# Встановити tox
pip install tox

# Запустити тести на всіх версіях Python (3.8, 3.9, 3.10, 3.11)
tox

# Тільки на Python 3.11
tox -e py311

# Coverage звіт
tox -e coverage

# Code quality перевірки
tox -e lint

# Автоматичне форматування
tox -e format

# Очистити згенеровані файли
tox -e clean
```

## 🎨 Форматування коду

```bash
# Форматувати всі файли
black 1c_processor_generator/ tests/
isort 1c_processor_generator/ tests/

# Перевірити без змін
black --check 1c_processor_generator/ tests/
isort --check-only 1c_processor_generator/ tests/

# Через tox
tox -e format
```

## 🔍 Лінтинг

```bash
# flake8
flake8 1c_processor_generator/ tests/ --max-line-length=120

# Через tox
tox -e lint
```

## 🚢 CI/CD

### GitHub Actions

При кожному push/PR автоматично запускаються:

1. **Tests** (.github/workflows/tests.yml)
   - Тестування на Python 3.8, 3.9, 3.10, 3.11
   - Тестування на Ubuntu та Windows
   - Coverage звіти на Codecov

2. **Lint** (.github/workflows/tests.yml)
   - black formatting check
   - isort import sorting
   - flake8 linting

### Перевірка перед push

```bash
# Запустити локально всі перевірки які виконуються в CI
tox

# Або швидша версія (тільки поточна Python версія)
pytest tests/ -v
black --check 1c_processor_generator/ tests/
isort --check-only 1c_processor_generator/ tests/
flake8 1c_processor_generator/ tests/
```

## 📝 Додавання нових тестів

### Структура

1. Створити новий файл в `tests/test_*.py`
2. Додати fixtures в `tests/conftest.py` (якщо потрібно)
3. Використовувати pytest конвенції

### Приклад

```python
# tests/test_new_feature.py
import pytest

def test_new_feature():
    """Опис тесту"""
    # Arrange
    input_data = "test"

    # Act
    result = my_function(input_data)

    # Assert
    assert result == expected_output
```

### Fixtures

```python
# tests/conftest.py
import pytest

@pytest.fixture
def my_fixture():
    """Fixture для тестів"""
    return SomeObject()
```

## 🏷️ Маркери тестів

```bash
# Slow тести (позначити @pytest.mark.slow)
pytest tests/ -m "not slow"  # Пропустити повільні

# Integration тести
pytest tests/ -m integration
```

## 📊 Coverage цілі

- **Мінімум:** 80% покриття коду
- **Ціль:** 90%+ покриття
- **Критичні модулі:** 95%+ (validators.py, generator.py)

## 🐛 Debugging

### VSCode

Створіть `.vscode/launch.json`:

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Current File",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal"
        },
        {
            "name": "Python: Pytest",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": [
                "tests/",
                "-v"
            ],
            "console": "integratedTerminal"
        }
    ]
}
```

### PyCharm

1. Run → Edit Configurations
2. Add New Configuration → Python tests → pytest
3. Target: `tests/`
4. Options: `-v`

## 📦 Публікація нової версії

```bash
# 1. Оновити версію в pyproject.toml
# 2. Оновити CHANGELOG.md
# 3. Запустити всі тести
tox

# 4. Створити git tag
git tag -a v2.4.0 -m "Release v2.4.0"
git push origin v2.4.0

# 5. GitHub Actions автоматично створить release
```

## 🔧 Корисні команди

```bash
# Знайти TODO в коді
grep -r "TODO" 1c_processor_generator/

# Переглянути покриття конкретного модуля
pytest tests/test_validators.py --cov=1c_processor_generator.validators

# Benchmark тестів
pytest tests/ --durations=10

# Паралельне виконання (якщо встановлено pytest-xdist)
pytest tests/ -n auto
```

## 📚 Додаткові ресурси

- [pytest документація](https://docs.pytest.org/)
- [black документація](https://black.readthedocs.io/)
- [pre-commit документація](https://pre-commit.com/)
- [tox документація](https://tox.wiki/)
