# Version Update Checklist

Інструкція для оновлення версії проекту 1C Processor Generator.

---

## Коли оновлювати версію?

Дотримуйтесь [Semantic Versioning](https://semver.org/):
- **MAJOR** (x.0.0) - Breaking changes (несумісні зміни API)
- **MINOR** (0.x.0) - Нові функції (зворотно сумісні)
- **PATCH** (0.0.x) - Bug fixes (зворотно сумісні)

---

## Checklist оновлення версії

### 1. Оновити CHANGELOG.md

```bash
# Додати новий розділ на початку файлу
## [2.X.X] - YYYY-MM-DD

### Added
- Нова функція 1
- Нова функція 2

### Changed
- Зміна 1

### Fixed
- Виправлення 1
```

### 2. Оновити версію в коді (3 файли)

**Основні файли:**
```bash
# 1. 1c_processor_generator/__init__.py
__version__ = "2.X.X"

# 2. setup.py
version="2.X.X"

# 3. pyproject.toml
version = "2.X.X"
```

**Автоматично (рекомендовано):**
```bash
python scripts/update_version.py 2.X.X
```

### 3. Оновити версії в документації

**Основна документація (5 файлів):**

```bash
# docs/CHEATSHEET.md
# Line 3: заголовок
**One-page cheatsheet for fast development** | Version 2.X.X

# Line ~290: футер
**Last updated:** YYYY-MM-DD | **Version:** 2.X.X
```

```bash
# docs/QUICK_REFERENCE.md
# Line ~449-454: футер з історією версій
**Version:** 2.X.X (YYYY-MM-DD)
**New in 2.X.X:** Основна нова фіча
**New in 2.Y.Y:** Попередня фіча
...
```

```bash
# docs/IMPLEMENTATION_REPORT.md
# Line ~3-4: метадані
**Version:** 2.X.X
**Date:** YYYY-MM-DD
```

```bash
# docs/UI_PATTERNS.md
# Line ~645: футер
**Version:** 2.X.X (YYYY-MM-DD)
```

```bash
# docs/VALID_PICTURES.md
# Line 6-7: метадані
**Last updated:** YYYY-MM-DD
**Version:** 2.X.X
```

### 4. Оновити приклади (якщо потрібно)

Якщо версія додає нову функцію, яка демонструється в прикладах:

```bash
# examples/yaml/*/README.md
**Version:** 2.X.X
**Last updated:** YYYY-MM-DD
```

**Поточні приклади:**
- `examples/yaml/unlimited_string_example/README.md`
- `examples/yaml/data_import/README.md`
- `examples/yaml/sales_report/README.md`
- `examples/yaml/ddg_search/README.md` (якщо є)

### 5. Перевірити версії

**Швидка перевірка основних файлів:**
```bash
echo "=== Core files ===" && \
grep "__version__" 1c_processor_generator/__init__.py && \
grep "version=" setup.py | head -1 && \
grep "version = " pyproject.toml && \
echo "" && \
echo "=== Documentation ===" && \
grep "Version.*2\." docs/QUICK_REFERENCE.md | tail -1 && \
grep "Version.*2\." docs/CHEATSHEET.md | tail -1 && \
grep "Version.*2\." docs/UI_PATTERNS.md && \
grep "Version.*2\." docs/VALID_PICTURES.md
```

**Знайти всі застарілі версії:**
```bash
# Шукати старі версії (змінити 2.[0-6] на актуальний діапазон)
grep -rn "version.*2\.[0-6]\." \
  --include="*.py" \
  --include="*.yaml" \
  --include="*.md" \
  --exclude-dir=.git \
  --exclude-dir=__pycache__ \
  --exclude-dir=tmp \
  --exclude="CHANGELOG.md" \
  --exclude="scripts/update_version.py" \
  --exclude="scripts/README.md" \
  . | grep -v "Version 2\." | grep -v "version 2\.[0-6]\.0"
```

### 6. Оновити CLAUDE.md (якщо потрібно)

Якщо є архітектурні зміни, оновити розділ **Version Info** в `CLAUDE.md`:

```markdown
## Version Info

Current version: **2.X.X**
- Added: Нова фіча 1
- Added: Нова фіча 2
- Changed: Зміна

Previous major: **2.Y.Y**
- ...
```

---

## Файли, які НЕ потрібно оновлювати

**Історичні записи (залишити як є):**
- `CHANGELOG.md` - історичні розділи про старі версії
- `docs/LLM_PROMPT.md` - розділ Version History (історичні записи)
- `scripts/update_version.py` - приклади використання (2.4.0 як приклад)
- `scripts/README.md` - приклади використання
- `.git/logs/` - git історія

---

## Повний процес оновлення (крок за кроком)

### Крок 1: Підготовка
```bash
# Переконатися, що на master і все закоммічено
git status

# Створити гілку для оновлення версії (опційно)
git checkout -b release/2.X.X
```

### Крок 2: Оновити CHANGELOG.md
```bash
# Вручну відредагувати CHANGELOG.md
# Додати розділ [2.X.X] з датою і змінами
```

### Крок 3: Оновити версію в коді
```bash
# Автоматично оновити __init__.py, setup.py, pyproject.toml
python scripts/update_version.py 2.X.X
```

### Крок 4: Оновити документацію
```bash
# Вручну оновити 5 файлів документації:
# 1. docs/CHEATSHEET.md (заголовок + футер)
# 2. docs/QUICK_REFERENCE.md (футер з історією)
# 3. docs/IMPLEMENTATION_REPORT.md (метадані)
# 4. docs/UI_PATTERNS.md (футер)
# 5. docs/VALID_PICTURES.md (метадані)
```

### Крок 5: Оновити приклади (якщо потрібно)
```bash
# Якщо версія додає нову функцію в приклади
# Оновити examples/yaml/*/README.md
```

### Крок 6: Перевірити
```bash
# Виконати перевірочні команди з розділу 5
# Переконатися, що всі версії синхронізовані
```

### Крок 7: Commit і tag
```bash
# Закоммітити зміни
git add .
git commit -m "chore: bump version to 2.X.X"

# Створити git tag
git tag -a v2.X.X -m "Release version 2.X.X"

# Влити в master
git checkout master
git merge release/2.X.X

# Запушити з тегами
git push origin master
git push origin v2.X.X
```

---

## Швидкий чеклист

- [ ] Оновити `CHANGELOG.md` (новий розділ)
- [ ] Запустити `python scripts/update_version.py 2.X.X`
- [ ] Оновити `docs/CHEATSHEET.md` (2 місця: заголовок + футер)
- [ ] Оновити `docs/QUICK_REFERENCE.md` (футер з історією версій)
- [ ] Оновити `docs/IMPLEMENTATION_REPORT.md` (метадані)
- [ ] Оновити `docs/UI_PATTERNS.md` (футер)
- [ ] Оновити `docs/VALID_PICTURES.md` (метадані)
- [ ] Оновити приклади `examples/yaml/*/README.md` (якщо потрібно)
- [ ] Оновити `CLAUDE.md` розділ Version Info (якщо потрібно)
- [ ] Перевірити версії (grep команди)
- [ ] Commit: `git commit -m "chore: bump version to 2.X.X"`
- [ ] Tag: `git tag -a v2.X.X -m "Release version 2.X.X"`
- [ ] Push: `git push origin master && git push origin v2.X.X`

---

## Приклади команд для різних сценаріїв

### Знайти всі файли з версією проекту
```bash
grep -rn "2\.[0-9]\.[0-9]" \
  --include="*.py" \
  --include="*.md" \
  --exclude-dir=.git \
  --exclude-dir=tmp \
  . | grep -i version | head -20
```

### Оновити дату в документації
```bash
# Знайти всі файли з датою оновлення
grep -rn "Last updated.*2025" docs/
```

### Перевірити, чи всі версії однакові
```bash
# Має вивести одну і ту ж версію у всіх файлах
echo "Core:" && \
grep "__version__" 1c_processor_generator/__init__.py && \
grep "version=" setup.py | head -1 && \
grep "^version = " pyproject.toml
```

---

## Історія версій (для довідки)

- **2.7.3** (2025-10-14) - Recursive element processing
- **2.7.2** (2025-10-14) - Helper functions duplication fix
- **2.7.1** (2025-10-14) - Nested UsualGroup support
- **2.7.0** (2025-10-14) - Single file BSL approach (`--handlers-file`)
- **2.6.0** (2025-10-13) - DynamicList support
- **2.2.0** (2025-10-10) - RadioButtonField, CheckBoxField, ChoiceList
- **2.1.0** (2025-01-09) - Table events support
- **2.0.0** (2025-10-07) - YAML API + BSL injection

---

**Останнє оновлення чеклісту:** 2025-10-14
**Версія чеклісту:** 1.0
