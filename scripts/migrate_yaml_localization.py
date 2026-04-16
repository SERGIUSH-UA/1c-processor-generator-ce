#!/usr/bin/env python3
"""
Migration script: Convert flat localization (title_ru/uk/en) to nested format (title: {ru, uk, en})

Usage:
    python scripts/migrate_yaml_localization.py path/to/config.yaml
    python scripts/migrate_yaml_localization.py examples/yaml/*.yaml

This is a BREAKING CHANGE migration for yaml_schema.json v2.42.0+ refactoring.
"""

import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("Error: PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)


LOCALIZED_FIELDS = ['title', 'synonym', 'tooltip', 'input_hint', 'presentation', 'progress_message']


def migrate_dict(d: Any) -> Any:
    """Recursively migrate flat localization to nested format."""
    if not isinstance(d, dict):
        return d

    # Process localized fields
    for base in LOCALIZED_FIELDS:
        nested = {}
        for lang in ['ru', 'uk', 'en']:
            key = f'{base}_{lang}'
            if key in d:
                nested[lang] = d.pop(key)
        if nested:
            # Only set if not already set as nested
            if base not in d or not isinstance(d.get(base), dict):
                d[base] = nested
            else:
                # Merge with existing nested
                d[base].update(nested)

    # Recurse into nested structures
    for key, value in list(d.items()):
        if isinstance(value, dict):
            d[key] = migrate_dict(value)
        elif isinstance(value, list):
            d[key] = [migrate_dict(item) if isinstance(item, dict) else item for item in value]

    return d


def migrate_file(path: Path, dry_run: bool = False) -> bool:
    """Migrate a single YAML file. Returns True if changes were made."""
    try:
        content = path.read_text(encoding='utf-8')
        data = yaml.safe_load(content)

        if data is None:
            print(f"  Skipped (empty): {path}")
            return False

        # Deep copy for comparison
        import copy
        original = copy.deepcopy(data)

        migrated = migrate_dict(data)

        if migrated == original:
            print(f"  No changes: {path}")
            return False

        if dry_run:
            print(f"  Would migrate: {path}")
            return True

        # Use ruamel.yaml if available for better formatting, otherwise pyyaml
        try:
            from ruamel.yaml import YAML
            yaml_writer = YAML()
            yaml_writer.preserve_quotes = True
            yaml_writer.indent(mapping=2, sequence=4, offset=2)
            with open(path, 'w', encoding='utf-8') as f:
                yaml_writer.dump(migrated, f)
        except ImportError:
            # Fallback to PyYAML
            output = yaml.dump(migrated, allow_unicode=True, default_flow_style=False, sort_keys=False, indent=2)
            path.write_text(output, encoding='utf-8')

        print(f"  Migrated: {path}")
        return True

    except Exception as e:
        print(f"  Error: {path} - {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nExamples:")
        print("  python scripts/migrate_yaml_localization.py examples/yaml/config.yaml")
        print("  python scripts/migrate_yaml_localization.py --dry-run examples/yaml/*.yaml")
        sys.exit(1)

    dry_run = '--dry-run' in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith('--')]

    if not args:
        print("Error: No files specified")
        sys.exit(1)

    print(f"{'[DRY RUN] ' if dry_run else ''}Migrating YAML files from flat to nested localization...")
    print()

    migrated_count = 0
    total_count = 0

    for pattern in args:
        # Handle glob patterns
        if '*' in pattern:
            files = list(Path('.').glob(pattern))
        else:
            files = [Path(pattern)]

        for path in files:
            if path.is_file() and path.suffix in ['.yaml', '.yml']:
                total_count += 1
                if migrate_file(path, dry_run):
                    migrated_count += 1

    print()
    print(f"{'Would migrate' if dry_run else 'Migrated'}: {migrated_count}/{total_count} files")


if __name__ == '__main__':
    main()
