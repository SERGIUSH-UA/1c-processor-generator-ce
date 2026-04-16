#!/usr/bin/env python3
"""
Оновлення версії у всіх файлах проекту

Підтримує dual versioning (DEV_VERSION та RELEASE_VERSION):
- DEV_VERSION: поточна версія розробки (в __init__.py, pyproject.toml, setup.py)
- RELEASE_VERSION: версія для релізної збірки (читається build_release.py)

Використання:
    python scripts/update_version.py 2.59.0             # Оновити DEV версію
    python scripts/update_version.py --release 2.57.0   # Оновити RELEASE версію
    python scripts/update_version.py --promote          # Копіювати DEV → RELEASE
    python scripts/update_version.py --show             # Показати поточні версії
"""

import argparse
import re
import sys
from pathlib import Path


VERSION_FILE_TEMPLATE = """# Version tracking for 1C Processor Generator
# ============================================
# DEV_VERSION: Current development version (in __init__.py)
# RELEASE_VERSION: Last published release version (used by build_release.py)
#
# Workflow:
# 1. During development, DEV_VERSION is updated in __init__.py
# 2. When ready to release, update RELEASE_VERSION here
# 3. Run build_release.py - it reads RELEASE_VERSION for dist/
#
# Commands:
#   python scripts/update_version.py 2.59.0           # Update DEV version
#   python scripts/update_version.py --release 2.57.0 # Update RELEASE version
#   python scripts/update_version.py --promote        # Copy DEV -> RELEASE

DEV_VERSION={dev_version}
RELEASE_VERSION={release_version}
"""


def get_root_dir() -> Path:
    """Отримує кореневий каталог проекту"""
    return Path(__file__).parent.parent


def get_version_file() -> Path:
    """Отримує шлях до VERSION файлу"""
    return get_root_dir() / "VERSION"


def read_version_file() -> tuple[str, str]:
    """
    Читає VERSION файл та повертає (DEV_VERSION, RELEASE_VERSION).
    Якщо файл не існує, повертає (None, None).
    """
    version_file = get_version_file()
    if not version_file.exists():
        return None, None

    dev_version = None
    release_version = None

    for line in version_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DEV_VERSION="):
            dev_version = line.split("=", 1)[1].strip()
        elif line.startswith("RELEASE_VERSION="):
            release_version = line.split("=", 1)[1].strip()

    return dev_version, release_version


def write_version_file(dev_version: str, release_version: str) -> bool:
    """Записує VERSION файл з новими версіями"""
    version_file = get_version_file()
    content = VERSION_FILE_TEMPLATE.format(
        dev_version=dev_version,
        release_version=release_version
    )
    version_file.write_text(content, encoding="utf-8")
    return True


def update_version_in_pyproject(root_dir: Path, new_version: str) -> bool:
    """Оновлює версію у pyproject.toml"""
    pyproject_file = root_dir / "pyproject.toml"
    if not pyproject_file.exists():
        print(f"❌ Файл не знайдено: {pyproject_file}")
        return False

    content = pyproject_file.read_text(encoding="utf-8")
    old_content = content

    # Замінюємо версію
    content = re.sub(
        r'^(version\s*=\s*["\'])([^"\']+)(["\'])',
        rf'\g<1>{new_version}\g<3>',
        content,
        flags=re.MULTILINE
    )

    if content == old_content:
        print(f"⚠️  Версія не знайдена у {pyproject_file}")
        return False

    pyproject_file.write_text(content, encoding="utf-8")
    print(f"✅ pyproject.toml → {new_version}")
    return True


def update_version_in_setup_py(root_dir: Path, new_version: str) -> bool:
    """Оновлює версію у setup.py"""
    setup_file = root_dir / "setup.py"
    if not setup_file.exists():
        print(f"❌ Файл не знайдено: {setup_file}")
        return False

    content = setup_file.read_text(encoding="utf-8")
    old_content = content

    # Замінюємо версію
    content = re.sub(
        r'(version\s*=\s*["\'])([^"\']+)(["\'])',
        rf'\g<1>{new_version}\g<3>',
        content
    )

    if content == old_content:
        print(f"⚠️  Версія не знайдена у {setup_file}")
        return False

    setup_file.write_text(content, encoding="utf-8")
    print(f"✅ setup.py → {new_version}")
    return True


def update_version_in_init(root_dir: Path, new_version: str) -> bool:
    """Оновлює версію у __init__.py"""
    init_file = root_dir / "1c_processor_generator" / "__init__.py"
    if not init_file.exists():
        print(f"❌ Файл не знайдено: {init_file}")
        return False

    content = init_file.read_text(encoding="utf-8")
    old_content = content

    # Замінюємо версію
    content = re.sub(
        r'^(__version__\s*=\s*["\'])([^"\']+)(["\'])',
        rf'\g<1>{new_version}\g<3>',
        content,
        flags=re.MULTILINE
    )

    if content == old_content:
        print(f"⚠️  Версія не знайдена у {init_file}")
        return False

    init_file.write_text(content, encoding="utf-8")
    print(f"✅ __init__.py → {new_version}")
    return True


def validate_version_format(version: str) -> bool:
    """Перевіряє формат версії (semver)"""
    # Базовий semver: MAJOR.MINOR.PATCH[-prerelease][+build]
    pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$'
    return re.match(pattern, version) is not None


def update_dev_version(new_version: str) -> bool:
    """Оновлює DEV версію у всіх файлах"""
    root_dir = get_root_dir()

    print(f"🔄 Оновлення DEV версії до {new_version}...")
    print(f"📁 Кореневий каталог: {root_dir}\n")

    # Оновлюємо версії у всіх файлах коду
    results = [
        update_version_in_pyproject(root_dir, new_version),
        update_version_in_setup_py(root_dir, new_version),
        update_version_in_init(root_dir, new_version),
    ]

    # Оновлюємо VERSION файл
    dev_ver, release_ver = read_version_file()
    if release_ver is None:
        release_ver = "2.56.0"  # Default release version
    write_version_file(new_version, release_ver)
    print(f"✅ VERSION (DEV_VERSION) → {new_version}")

    print()
    return all(results)


def update_release_version(new_version: str) -> bool:
    """Оновлює RELEASE версію у VERSION файлі"""
    print(f"🔄 Оновлення RELEASE версії до {new_version}...")

    dev_ver, release_ver = read_version_file()
    if dev_ver is None:
        # Читаємо поточну версію з __init__.py
        root_dir = get_root_dir()
        init_file = root_dir / "1c_processor_generator" / "__init__.py"
        content = init_file.read_text(encoding="utf-8")
        match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        dev_ver = match.group(1) if match else "2.58.0"

    write_version_file(dev_ver, new_version)
    print(f"✅ VERSION (RELEASE_VERSION) → {new_version}")
    print()
    print(f"📝 Тепер можна запустити build_release.py для створення релізу v{new_version}")
    return True


def promote_to_release() -> bool:
    """Копіює DEV версію в RELEASE версію"""
    dev_ver, release_ver = read_version_file()

    if dev_ver is None:
        print("❌ VERSION файл не знайдено або DEV_VERSION не вказано")
        return False

    print(f"🔄 Промоція: DEV_VERSION={dev_ver} → RELEASE_VERSION")

    write_version_file(dev_ver, dev_ver)
    print(f"✅ RELEASE_VERSION оновлено до {dev_ver}")
    print()
    print(f"📝 Тепер можна запустити build_release.py для створення релізу v{dev_ver}")
    return True


def show_versions():
    """Показує поточні версії"""
    dev_ver, release_ver = read_version_file()

    print("📊 Поточні версії:")
    print()

    if dev_ver:
        print(f"   DEV_VERSION:     {dev_ver}")
    else:
        print("   DEV_VERSION:     (не вказано)")

    if release_ver:
        print(f"   RELEASE_VERSION: {release_ver}")
    else:
        print("   RELEASE_VERSION: (не вказано)")

    print()

    # Перевіряємо версію в __init__.py
    root_dir = get_root_dir()
    init_file = root_dir / "1c_processor_generator" / "__init__.py"
    if init_file.exists():
        content = init_file.read_text(encoding="utf-8")
        match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
        if match:
            init_ver = match.group(1)
            print(f"   __init__.py:     {init_ver}")
            if dev_ver and init_ver != dev_ver:
                print(f"   ⚠️  __init__.py версія ({init_ver}) відрізняється від DEV_VERSION ({dev_ver})")


def main():
    """Головна функція з підтримкою CLI аргументів"""
    parser = argparse.ArgumentParser(
        description="Оновлення версії проекту 1C Processor Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Приклади:
  python scripts/update_version.py 2.59.0             # Оновити DEV версію
  python scripts/update_version.py --release 2.57.0   # Оновити RELEASE версію
  python scripts/update_version.py --promote          # Копіювати DEV → RELEASE
  python scripts/update_version.py --show             # Показати поточні версії
        """
    )

    parser.add_argument(
        "version",
        nargs="?",
        help="Нова DEV версія (наприклад: 2.59.0)"
    )
    parser.add_argument(
        "--release", "-r",
        metavar="VERSION",
        help="Оновити RELEASE версію"
    )
    parser.add_argument(
        "--promote", "-p",
        action="store_true",
        help="Копіювати DEV версію в RELEASE версію"
    )
    parser.add_argument(
        "--show", "-s",
        action="store_true",
        help="Показати поточні версії"
    )

    args = parser.parse_args()

    # Показати версії
    if args.show:
        show_versions()
        sys.exit(0)

    # Промоція DEV → RELEASE
    if args.promote:
        success = promote_to_release()
        sys.exit(0 if success else 1)

    # Оновити RELEASE версію
    if args.release:
        if not validate_version_format(args.release):
            print(f"❌ Неправильний формат версії: {args.release}")
            sys.exit(1)
        success = update_release_version(args.release)
        sys.exit(0 if success else 1)

    # Оновити DEV версію
    if args.version:
        if not validate_version_format(args.version):
            print(f"❌ Неправильний формат версії: {args.version}")
            print("\nВерсія має відповідати semantic versioning:")
            print("   MAJOR.MINOR.PATCH (наприклад: 2.59.0)")
            print("   MAJOR.MINOR.PATCH-prerelease (наприклад: 2.59.0-beta.1)")
            sys.exit(1)

        success = update_dev_version(args.version)

        if success:
            print(f"🎉 DEV версія успішно оновлена до {args.version}!")
            print("\n📝 Не забудьте:")
            print("   1. Оновити CHANGELOG.md")
            print("   2. Зробити commit:")
            print(f"      git add -A && git commit -m 'chore: bump version to {args.version}'")
            print(f"   3. Створити тег:")
            print(f"      git tag -a v{args.version} -m 'Release v{args.version}'")
        else:
            print("❌ Не вдалося оновити версію в деяких файлах")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
