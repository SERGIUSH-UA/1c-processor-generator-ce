#!/usr/bin/env python3
"""
Перевірка синхронності версій між файлами проекту

Перевіряє, що версія однакова у:
- pyproject.toml
- setup.py
- 1c_processor_generator/__init__.py

Використовується в CI/CD для автоматичної перевірки.
"""

import re
import sys
from pathlib import Path


def get_version_from_pyproject(root_dir: Path) -> str:
    """Читає версію з pyproject.toml"""
    pyproject_file = root_dir / "pyproject.toml"
    if not pyproject_file.exists():
        print(f"❌ Файл не знайдено: {pyproject_file}")
        return None

    content = pyproject_file.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)

    if match:
        return match.group(1)

    print(f"⚠️  Версія не знайдена у {pyproject_file}")
    return None


def get_version_from_setup_py(root_dir: Path) -> str:
    """Читає версію з setup.py"""
    setup_file = root_dir / "setup.py"
    if not setup_file.exists():
        print(f"❌ Файл не знайдено: {setup_file}")
        return None

    content = setup_file.read_text(encoding="utf-8")
    match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)

    if match:
        return match.group(1)

    print(f"⚠️  Версія не знайдена у {setup_file}")
    return None


def get_version_from_init(root_dir: Path) -> str:
    """Читає версію з __init__.py"""
    init_file = root_dir / "1c_processor_generator" / "__init__.py"
    if not init_file.exists():
        print(f"❌ Файл не знайдено: {init_file}")
        return None

    content = init_file.read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)

    if match:
        return match.group(1)

    print(f"⚠️  Версія не знайдена у {init_file}")
    return None


def main():
    """Перевіряє синхронність версій"""
    root_dir = Path(__file__).parent.parent

    print("🔍 Перевірка синхронності версій...")
    print(f"📁 Кореневий каталог: {root_dir}\n")

    # Читаємо версії з усіх файлів
    versions = {
        "pyproject.toml": get_version_from_pyproject(root_dir),
        "setup.py": get_version_from_setup_py(root_dir),
        "__init__.py": get_version_from_init(root_dir),
    }

    # Перевіряємо чи всі версії прочитано
    missing_versions = [file for file, version in versions.items() if version is None]
    if missing_versions:
        print(f"❌ Не вдалося прочитати версії з файлів: {', '.join(missing_versions)}")
        sys.exit(1)

    # Виводимо знайдені версії
    print("📋 Знайдені версії:")
    for file, version in versions.items():
        print(f"   {file:20s} → {version}")

    print()

    # Перевіряємо чи всі версії однакові
    unique_versions = set(versions.values())

    if len(unique_versions) == 1:
        version = unique_versions.pop()
        print(f"✅ Всі версії синхронізовані: {version}")
        sys.exit(0)
    else:
        print("❌ ПОМИЛКА: Версії не синхронізовані!")
        print("\nВерсії різняться між файлами:")
        for file, version in versions.items():
            print(f"   {file:20s} → {version}")
        print("\n💡 Синхронізуйте версії вручну або запустіть скрипт оновлення версії.")
        sys.exit(1)


if __name__ == "__main__":
    main()
