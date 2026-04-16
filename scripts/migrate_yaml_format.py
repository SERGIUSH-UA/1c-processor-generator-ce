#!/usr/bin/env python3
"""
Скрипт міграції YAML з старого формату (form:) на новий (forms:).

Використання:
    python scripts/migrate_yaml_format.py path/to/file.yaml
    python scripts/migrate_yaml_format.py path/to/directory --recursive
    python scripts/migrate_yaml_format.py tests/ --dry-run

Що конвертує:
- form: → forms: [- name: Форма, default: true, ...]
- commands: (root) → forms[0].commands
- value_tables: (root) → forms[0].value_tables
- dynamic_lists: (root) → forms[0].dynamic_lists
- form_attributes: (root) → forms[0].form_attributes
"""

import sys
import re
from pathlib import Path
from typing import Optional
import argparse


def migrate_yaml_content(content: str) -> tuple[str, bool]:
    """
    Мігрує YAML контент зі старого формату на новий.

    Returns:
        (new_content, was_changed)
    """
    # Перевіряємо чи вже новий формат
    if re.search(r'^forms:\s*$', content, re.MULTILINE):
        return content, False

    # Перевіряємо чи є старий формат
    if not re.search(r'^form:\s*$', content, re.MULTILINE):
        return content, False

    lines = content.split('\n')
    result_lines = []

    # Секції які переносяться всередину форми
    root_sections_to_move = {
        'commands': [],
        'value_tables': [],
        'dynamic_lists': [],
        'form_attributes': [],
    }

    form_content = {
        'properties': [],
        'events': [],
        'elements': [],
        'auto_command_bar': [],
    }

    current_section = None
    current_indent = 0
    in_form_section = False
    form_subsection = None
    skip_until_next_root = False

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        # Порожній рядок або коментар
        if not stripped or stripped.startswith('#'):
            if not skip_until_next_root and not in_form_section:
                result_lines.append(line)
            elif in_form_section and form_subsection:
                form_content[form_subsection].append(line)
            elif current_section in root_sections_to_move:
                root_sections_to_move[current_section].append(line)
            i += 1
            continue

        # Root-level секція (indent == 0)
        if indent == 0 and stripped.endswith(':'):
            section_name = stripped[:-1]

            # Секції які переносяться в форму
            if section_name in root_sections_to_move:
                current_section = section_name
                skip_until_next_root = True
                i += 1
                continue

            # form: секція
            if section_name == 'form':
                in_form_section = True
                current_section = 'form'
                i += 1
                continue

            # Інші root секції залишаємо
            current_section = section_name
            skip_until_next_root = False
            in_form_section = False
            form_subsection = None
            result_lines.append(line)
            i += 1
            continue

        # Всередині root секції яку переносимо
        if skip_until_next_root and indent > 0 and current_section in root_sections_to_move:
            root_sections_to_move[current_section].append(line)
            i += 1
            continue

        # Всередині form: секції
        if in_form_section:
            if indent == 2 and stripped.endswith(':'):
                subsection = stripped[:-1]
                if subsection in form_content:
                    form_subsection = subsection
                    i += 1
                    continue

            if form_subsection and indent >= 2:
                # Зменшуємо indent на 2 (бо form: зникає)
                form_content[form_subsection].append(line)
            i += 1
            continue

        # Звичайний рядок
        if not skip_until_next_root:
            result_lines.append(line)
        i += 1

    # Будуємо нову структуру forms:
    forms_lines = ['forms:']
    forms_lines.append('  - name: Форма')
    forms_lines.append('    default: true')

    # Properties
    if form_content['properties']:
        forms_lines.append('    properties:')
        for line in form_content['properties']:
            if line.strip():
                # Додаємо +2 indent
                forms_lines.append('  ' + line)
            else:
                forms_lines.append(line)

    # Events
    if form_content['events']:
        forms_lines.append('    events:')
        for line in form_content['events']:
            if line.strip():
                forms_lines.append('  ' + line)
            else:
                forms_lines.append(line)

    # Commands (з root рівня)
    if root_sections_to_move['commands']:
        forms_lines.append('    commands:')
        for line in root_sections_to_move['commands']:
            if line.strip():
                forms_lines.append('  ' + line)
            else:
                forms_lines.append(line)

    # form_attributes
    if root_sections_to_move['form_attributes']:
        forms_lines.append('    form_attributes:')
        for line in root_sections_to_move['form_attributes']:
            if line.strip():
                forms_lines.append('  ' + line)
            else:
                forms_lines.append(line)

    # value_tables
    if root_sections_to_move['value_tables']:
        forms_lines.append('    value_tables:')
        for line in root_sections_to_move['value_tables']:
            if line.strip():
                forms_lines.append('  ' + line)
            else:
                forms_lines.append(line)

    # dynamic_lists
    if root_sections_to_move['dynamic_lists']:
        forms_lines.append('    dynamic_lists:')
        for line in root_sections_to_move['dynamic_lists']:
            if line.strip():
                forms_lines.append('  ' + line)
            else:
                forms_lines.append(line)

    # auto_command_bar
    if form_content['auto_command_bar']:
        forms_lines.append('    auto_command_bar:')
        for line in form_content['auto_command_bar']:
            if line.strip():
                forms_lines.append('  ' + line)
            else:
                forms_lines.append(line)

    # Elements
    if form_content['elements']:
        forms_lines.append('    elements:')
        for line in form_content['elements']:
            if line.strip():
                forms_lines.append('  ' + line)
            else:
                forms_lines.append(line)

    # Збираємо результат
    result_lines.append('')
    result_lines.extend(forms_lines)

    new_content = '\n'.join(result_lines)

    # Cleanup: видаляємо зайві порожні рядки
    new_content = re.sub(r'\n{3,}', '\n\n', new_content)

    return new_content, True


def migrate_file(file_path: Path, dry_run: bool = False) -> bool:
    """Мігрує один файл."""
    try:
        content = file_path.read_text(encoding='utf-8')
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return False

    new_content, changed = migrate_yaml_content(content)

    if not changed:
        print(f"⏭️  {file_path} - already new format or no form: section")
        return False

    if dry_run:
        print(f"🔍 {file_path} - would be migrated")
        print("--- Preview ---")
        print(new_content[:500] + "..." if len(new_content) > 500 else new_content)
        print("---------------")
        return True

    try:
        file_path.write_text(new_content, encoding='utf-8')
        print(f"✅ {file_path} - migrated")
        return True
    except Exception as e:
        print(f"❌ Error writing {file_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Migrate YAML files from old format (form:) to new format (forms:)'
    )
    parser.add_argument('path', help='File or directory to migrate')
    parser.add_argument('--recursive', '-r', action='store_true',
                        help='Recursively process directories')
    parser.add_argument('--dry-run', '-n', action='store_true',
                        help='Show what would be changed without making changes')
    parser.add_argument('--pattern', '-p', default='*.yaml',
                        help='File pattern for directory mode (default: *.yaml)')

    args = parser.parse_args()
    path = Path(args.path)

    if not path.exists():
        print(f"❌ Path not found: {path}")
        sys.exit(1)

    files_to_process = []

    if path.is_file():
        files_to_process.append(path)
    else:
        if args.recursive:
            files_to_process.extend(path.rglob(args.pattern))
        else:
            files_to_process.extend(path.glob(args.pattern))

    if not files_to_process:
        print(f"No files matching '{args.pattern}' found in {path}")
        sys.exit(0)

    print(f"Found {len(files_to_process)} file(s) to process")
    if args.dry_run:
        print("DRY RUN - no changes will be made\n")

    migrated = 0
    for file_path in sorted(files_to_process):
        if migrate_file(file_path, args.dry_run):
            migrated += 1

    print(f"\n{'Would migrate' if args.dry_run else 'Migrated'}: {migrated}/{len(files_to_process)} files")


if __name__ == '__main__':
    main()
