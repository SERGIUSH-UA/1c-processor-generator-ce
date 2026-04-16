# 🎯 Автоматизація Тестування - Інструкції

Цей документ описує всі способи автоматичного запуску тестів після внесення змін.

## ✅ Що було налаштовано

### 1. ☁️ GitHub Actions (CI/CD на сервері)

**Файл:** `.github/workflows/tests.yml`

**Автоматично запускається при:**
- Push в гілки: master, main, develop
- Створенні Pull Request
- Ручному запуску (workflow_dispatch)

**Що робить:**
- ✅ Запускає всі 138 тестів
- ✅ Тестує на Python 3.8, 3.9, 3.10, 3.11
- ✅ Тестує на Ubuntu та Windows
- ✅ Генерує coverage звіт
- ✅ Завантажує coverage на Codecov
- ✅ Перевіряє code quality (black, isort, flake8)

**Як переглянути:**
- Відкрийте GitHub → Actions
- Або клікніть на бейдж ![Tests](https://github.com/SERGIUSH-UA/1c-processor-generator/workflows/Tests/badge.svg)

### 2. 🔒 Pre-commit Hooks (перед кожним комітом)

**Файл:** `.pre-commit-config.yaml`

**Встановлення:**
```bash
pip install pre-commit
pre-commit install
```

**Що перевіряє автоматично перед комітом:**
1. Trailing whitespace (видалення зайвих пробілів)
2. End of file fixer (новий рядок в кінці файлу)
3. YAML синтаксис
4. TOML синтаксис
5. Великі файли (>1MB)
6. Merge конфлікти
7. **Black** - форматування коду
8. **isort** - сортування імпортів
9. **flake8** - лінтинг
10. **pytest** - швидкі тести (зупиняється на першій помилці)

**Як використовувати:**
```bash
# Hooks запускаються автоматично при git commit
git add .
git commit -m "My changes"  # <-- hooks спрацюють тут

# Запустити вручну на всіх файлах
pre-commit run --all-files

# Тимчасово пропустити (не рекомендується)
git commit --no-verify
```

### 3. 🔄 pytest-watch (під час розробки)

**Автоматично перезапускає тести при зміні файлів**

**Встановлення:**
```bash
pip install pytest-watch
```

**Використання:**
```bash
# Запустити в окремому терміналі
ptw tests/

# Тепер кожна зміна .py файлу автоматично перезапускає тести!
# Ви пишете код → тести запускаються автоматично
```

**Корисні опції:**
```bash
# Тільки швидкі тести
ptw tests/ -- -x --maxfail=1

# З конкретним файлом
ptw tests/test_validators.py

# З verbose виводом
ptw tests/ -- -v
```

### 4. 🧪 Tox (локальне тестування на всіх Python версіях)

**Файл:** `tox.ini`

**Встановлення:**
```bash
pip install tox
```

**Використання:**
```bash
# Запустити на всіх Python версіях (3.8, 3.9, 3.10, 3.11)
tox

# Тільки на конкретній версії
tox -e py311

# Coverage звіт
tox -e coverage

# Code quality
tox -e lint

# Автоформатування
tox -e format

# Очистити
tox -e clean
```

### 5. 🛡️ Конфігурація pytest (автоматичний coverage)

**Файл:** `pyproject.toml` (секція [tool.pytest.ini_options])

**Що налаштовано:**
- Автоматичний coverage при кожному запуску pytest
- HTML та XML звіти
- Маркери для slow та integration тестів

**Використання:**
```bash
# Просто запустіть pytest - coverage автоматичний
pytest tests/

# Coverage звіти генеруються в:
# - htmlcov/index.html (HTML)
# - coverage.xml (XML для CI/CD)
```

## 🚀 Рекомендований Workflow

### Під час розробки:

1. **Запустіть pytest-watch в окремому терміналі:**
   ```bash
   ptw tests/
   ```
   Тепер тести автоматично перезапускаються при кожній зміні

2. **Пишіть код**
   - Змінюєте файл → тести автоматично запускаються
   - Бачите результат одразу
   - Швидкий фідбек

3. **Перед комітом:**
   ```bash
   git add .
   git commit -m "Add new feature"
   ```
   Pre-commit hooks автоматично:
   - Форматують код
   - Перевіряють синтаксис
   - Запускають швидкі тести
   - Якщо щось не так - комміт не пройде

### Перед push:

```bash
# Запустіть всі тести локально
pytest tests/ -v

# Або через tox (на всіх Python версіях)
tox

# Якщо все ОК - робіть push
git push
```

### Після push:

- GitHub Actions автоматично запустить CI/CD
- Тести пройдуть на всіх Python версіях і OS
- Coverage завантажиться на Codecov
- Результат побачите в GitHub Actions tab

## 📊 Моніторинг

### Бейджі в README.md:

```markdown
[![Tests](https://github.com/SERGIUSH-UA/1c-processor-generator/workflows/Tests/badge.svg)](https://github.com/SERGIUSH-UA/1c-processor-generator/actions)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
```

### Coverage звіти:

- **Локально:** `htmlcov/index.html` після `pytest tests/ --cov`
- **CI/CD:** Codecov (автоматично після push)

## 🔧 Налаштування IDE

### VSCode

Додайте в `.vscode/settings.json`:
```json
{
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests"],
    "python.formatting.provider": "black",
    "editor.formatOnSave": true,
    "python.linting.flake8Enabled": true
}
```

### PyCharm

1. Settings → Tools → Python Integrated Tools → Testing → pytest
2. Settings → Tools → Black → Enable on save
3. Settings → Editor → Inspections → Enable flake8

## 📝 Додаткові команди

```bash
# Запустити тільки швидкі тести
pytest tests/ -m "not slow"

# Запустити integration тести
pytest tests/ -m integration

# Benchmark найповільніших тестів
pytest tests/ --durations=10

# Паралельне виконання (якщо є pytest-xdist)
pip install pytest-xdist
pytest tests/ -n auto

# Coverage для конкретного модуля
pytest tests/ --cov=1c_processor_generator.validators

# Fail на першій помилці
pytest tests/ -x

# Детальний вивід
pytest tests/ -vv

# Показати print() в тестах
pytest tests/ -s
```

## ✅ Чеклист перед release

- [ ] Всі локальні тести проходять: `pytest tests/ -v`
- [ ] Tox на всіх версіях: `tox`
- [ ] Code quality: `tox -e lint`
- [ ] Coverage > 80%: `pytest tests/ --cov`
- [ ] Pre-commit hooks встановлені: `pre-commit install`
- [ ] GitHub Actions зелені
- [ ] README.md оновлено
- [ ] CHANGELOG.md оновлено

## 🎓 Навчальні ресурси

- [pytest документація](https://docs.pytest.org/)
- [pre-commit документація](https://pre-commit.com/)
- [tox документація](https://tox.wiki/)
- [pytest-watch на GitHub](https://github.com/joeyespo/pytest-watch)
- [GitHub Actions документація](https://docs.github.com/en/actions)

## 🆘 Troubleshooting

### pytest-watch не працює
```bash
pip uninstall pytest-watch
pip install pytest-watch
```

### Pre-commit hooks не встановлюються
```bash
pip install --upgrade pre-commit
pre-commit clean
pre-commit install
```

### Tox не знаходить Python версії
```bash
# Встановіть потрібні версії Python
# Або використовуйте pyenv
pyenv install 3.8.10 3.9.7 3.10.5 3.11.2
```

### GitHub Actions падають але локально працює
- Перевірте різницю в OS (Windows vs Linux)
- Подивіться логи в GitHub Actions tab
- Запустіть tox локально для перевірки всіх версій

---

**Готово!** Тепер тести автоматично запускаються на всіх рівнях розробки! 🎉
