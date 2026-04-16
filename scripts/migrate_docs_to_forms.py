#!/usr/bin/env python3
"""
Скрипт для міграції документації з старого формату form: на новий forms:

Старий формат:
```yaml
form:
  elements:
    - type: InputField
      ...
commands:
  - name: MyCommand
    ...
```

Новий формат:
```yaml
forms:
  - name: Форма
    default: true
    elements:
      - type: InputField
        ...
    commands:
      - name: MyCommand
        ...
```
"""

import re
import sys
from pathlib import Path


def migrate_yaml_block(content: str) -> str:
    """
    Migrate a YAML code block from old format to new format.
    This is a simple regex-based approach that handles common patterns.
    """
    # Pattern 1: Simple form: with elements
    # Replace form:\n  elements: with forms:\n  - name: Форма\n    default: true\n    elements:

    result = content

    # Pattern for standalone form: blocks (not inside forms:)
    # This is a simplified approach - manual review may be needed
    patterns = [
        # form: at start of line followed by content
        (r'^form:\n(  (?:properties|events|elements):)', r'forms:\n  - name: Форма\n    default: true\n\1'),
    ]

    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result, flags=re.MULTILINE)

    return result


def find_old_format_files(docs_dir: Path) -> list[tuple[Path, int]]:
    """Find all markdown files with old form: format."""
    results = []

    for md_file in docs_dir.rglob("*.md"):
        if "archive" in str(md_file):
            continue

        content = md_file.read_text(encoding='utf-8')

        # Count occurrences of ^form: pattern
        matches = re.findall(r'^form:', content, re.MULTILINE)
        if matches:
            results.append((md_file, len(matches)))

    return results


def main():
    docs_dir = Path(__file__).parent.parent / "docs"

    print("=" * 60)
    print("Documentation Migration: form: -> forms:")
    print("=" * 60)
    print()

    files_with_old_format = find_old_format_files(docs_dir)

    if not files_with_old_format:
        print("✅ No files with old format found!")
        return 0

    print(f"Found {len(files_with_old_format)} files with old format:\n")

    total = 0
    for file_path, count in sorted(files_with_old_format, key=lambda x: -x[1]):
        rel_path = file_path.relative_to(docs_dir.parent)
        print(f"  {rel_path}: {count} occurrences")
        total += count

    print(f"\nTotal: {total} occurrences to migrate")
    print()
    print("These files need manual review:")
    print("- Replace `form:` blocks with `forms:` array format")
    print("- Move `commands:`, `value_tables:`, `dynamic_lists:` inside forms")
    print("- Add `name: Форма` and `default: true` to form entries")
    print()

    return 1


if __name__ == "__main__":
    sys.exit(main())
