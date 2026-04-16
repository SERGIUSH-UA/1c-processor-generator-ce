# Scripts

Цей каталог містить допоміжні скрипти для розробки та CI/CD.

## check_version_sync.py

Перевіряє синхронність версій між файлами проекту.

**Використання:**
```bash
python scripts/check_version_sync.py
```

**Перевіряє версії у:**
- `pyproject.toml`
- `setup.py`
- `1c_processor_generator/__init__.py`

**Exit codes:**
- `0` - всі версії синхронізовані ✅
- `1` - версії різняться або помилка читання ❌

**Використання в CI:**
Цей скрипт автоматично запускається в GitHub Actions на кожен push/PR для запобігання розсинхрону версій.

---

## update_version.py

Автоматично оновлює версію у всіх файлах проекту одночасно.

**Використання:**
```bash
python scripts/update_version.py <version>
```

**Приклади:**
```bash
# Релізна версія
python scripts/update_version.py 2.4.0

# Pre-release версія
python scripts/update_version.py 2.4.0-beta.1

# Build metadata
python scripts/update_version.py 2.4.0+build.123
```

**Оновлює версію у:**
- `pyproject.toml`
- `setup.py`
- `1c_processor_generator/__init__.py`

**Валідація:**
Скрипт перевіряє формат версії за стандартом Semantic Versioning (semver):
- `MAJOR.MINOR.PATCH` (наприклад: `2.4.0`)
- `MAJOR.MINOR.PATCH-prerelease` (наприклад: `2.4.0-beta.1`)
- `MAJOR.MINOR.PATCH+build` (наприклад: `2.4.0+build.123`)

**Після оновлення версії:**
1. Оновіть `CHANGELOG.md` вручну
2. Створіть commit:
   ```bash
   git add -A
   git commit -m "chore: bump version to 2.4.0"
   ```
3. Створіть тег:
   ```bash
   git tag -a v2.4.0 -m "Release v2.4.0"
   git push origin v2.4.0
   ```

---

## Workflow для релізу нової версії

1. **Оновіть версію:**
   ```bash
   python scripts/update_version.py 2.4.0
   ```

2. **Оновіть CHANGELOG.md:**
   Додайте новий розділ з описом змін:
   ```markdown
   ## [2.4.0] - 2025-10-15

   ### Added
   - Нова фіча...

   ### Fixed
   - Виправлення...
   ```

3. **Перевірте синхронність:**
   ```bash
   python scripts/check_version_sync.py
   ```

4. **Запустіть тести:**
   ```bash
   pytest tests/ -v
   ```

5. **Створіть commit та тег:**
   ```bash
   git add -A
   git commit -m "chore: bump version to 2.4.0"
   git tag -a v2.4.0 -m "Release v2.4.0"
   ```

6. **Запуште зміни:**
   ```bash
   git push origin master
   git push origin v2.4.0
   ```

7. **Опублікуйте на PyPI (опціонально):**
   ```bash
   python -m build
   python -m twine upload dist/*
   ```
