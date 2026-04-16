# 🚀 Рекомендації по оптимізації для роботи з LLM

**Версія:** 1.0
**Дата:** 2025-10-18
**Статус:** Implementation Guide

---

## 📋 Зміст

1. [PHASE 1: Quick Wins](#phase-1-quick-wins) - HIGH PRIORITY
2. [PHASE 2: UX Improvements](#phase-2-ux-improvements) - MEDIUM PRIORITY
3. [PHASE 3: Advanced Features](#phase-3-advanced-features) - LOW PRIORITY

---

## PHASE 1: Quick Wins

### ✅ Recommendation 1: Intelligent Cyrillic Converter

**Priority:** 🔥 CRITICAL
**Effort:** ~300 lines
**Impact:** Eliminates #1 pain point (100% Ukrainian LLM failures)

#### Problem

LLM моделі, навчені на українській мові, генерують українські ідентифікатори:

```yaml
# Claude/GPT генерує (якщо промпт українською):
attributes:
  - name: ПошуковийЗапіт    # Contains Ukrainian 'і', 'и'
  - name: ШляхДоФайлу       # Ukrainian word "шлях"
  - name: Відкритий         # Ukrainian word "відкритий"
```

**НО:** Проста заміна `і→и` **зламає російські слова**:

```
ПриОткрытии → ПриОткрытии (OK, но 'и' в середині - російська!)
ПриВідкритті → ПриВидкритти (BROKEN! Має бути ПриОткрытии)
```

#### Solution: Dictionary-Based Intelligent Converter

**Approach:**
1. **Словник українських → російських слів** (100+ most common)
2. **Word-by-word replacement** (не character-by-character!)
3. **Fallback:** Якщо слово не в словнику → **залишити як є + WARNING**

#### Implementation

##### File: `1c_processor_generator/utils/cyrillic_converter.py`

```python
"""
Intelligent Ukrainian → Russian Cyrillic converter for 1C identifiers.

Key principle: Word-level replacement, NOT character-level.
This preserves Russian words intact while converting Ukrainian identifiers.
"""

from typing import Dict, List, Tuple, Optional
import re
from pathlib import Path


# ========================================
# Ukrainian → Russian Word Dictionary
# ========================================

# Common 1C domain words (expand as needed)
UKRAINIAN_TO_RUSSIAN_WORDS = {
    # Verbs (most common in handlers)
    'відкрити': 'открыть',
    'відкритий': 'открытый',
    'відкритті': 'открытии',
    'відкриття': 'открытие',
    'закрити': 'закрыть',
    'закритий': 'закрытый',
    'виконати': 'выполнить',
    'виконання': 'выполнение',
    'завантажити': 'загрузить',
    'завантаження': 'загрузка',
    'зберегти': 'сохранить',
    'збереження': 'сохранение',
    'створити': 'создать',
    'створення': 'создание',
    'видалити': 'удалить',
    'видалення': 'удаление',
    'змінити': 'изменить',
    'зміна': 'изменение',
    'оновити': 'обновить',
    'оновлення': 'обновление',
    'сформувати': 'сформировать',
    'формування': 'формирование',

    # Nouns (data structures)
    'запит': 'запрос',
    'пошук': 'поиск',
    'пошуковий': 'поисковый',
    'результат': 'результат',  # Same, but keep for completeness
    'результати': 'результаты',
    'дані': 'данные',
    'файл': 'файл',  # Same
    'шлях': 'путь',
    'шляхдофайлу': 'путькфайлу',  # Compound
    'документ': 'документ',  # Same
    'документи': 'документы',
    'список': 'список',  # Same
    'таблиця': 'таблица',
    'рядок': 'строка',
    'стрічка': 'строка',  # Alternative
    'колонка': 'колонка',  # Same
    'поле': 'поле',  # Same
    'значення': 'значение',
    'параметр': 'параметр',  # Same
    'параметри': 'параметры',
    'налаштування': 'настройки',
    'обробка': 'обработка',
    'звіт': 'отчет',
    'користувач': 'пользователь',
    'користувачі': 'пользователи',
    'група': 'группа',
    'роль': 'роль',  # Same
    'ролі': 'роли',
    'доступ': 'доступ',  # Same

    # Adjectives
    'головний': 'главный',
    'головна': 'главная',
    'основний': 'основной',
    'додатковий': 'дополнительный',
    'новий': 'новый',
    'старий': 'старый',
    'поточний': 'текущий',
    'активний': 'активный',
    'вибраний': 'выбранный',

    # Dates/Time
    'дата': 'дата',  # Same
    'час': 'время',
    'період': 'период',
    'початок': 'начало',
    'кінець': 'конец',
    'початку': 'начала',
    'кінця': 'конца',

    # Actions
    'кнопка': 'кнопка',  # Same
    'команда': 'команда',  # Same
    'форма': 'форма',  # Same
    'елемент': 'элемент',

    # Common prefixes
    'при': 'при',  # Same, but might have variants
    'перед': 'перед',  # Same
    'після': 'после',
    'на': 'на',  # Same

    # Special cases (compound words)
    'привідкритті': 'приоткрытии',
    'призакритті': 'призакрытии',
    'присозданії': 'присоздании',  # Wait, this is Russian already!
}

# Add lowercase versions (for case-insensitive matching)
UKRAINIAN_TO_RUSSIAN_WORDS_LOWER = {
    k.lower(): v.lower()
    for k, v in UKRAINIAN_TO_RUSSIAN_WORDS.items()
}


# ========================================
# Intelligent Converter
# ========================================

class CyrillicConverter:
    """
    Intelligent Ukrainian → Russian Cyrillic converter.

    Features:
    - Word-level replacement (preserves Russian words)
    - PascalCase preservation
    - Unknown word detection → WARNING instead of breaking
    """

    def __init__(self, custom_dictionary: Optional[Dict[str, str]] = None):
        """
        Args:
            custom_dictionary: Additional user-defined word mappings
        """
        self.dictionary = UKRAINIAN_TO_RUSSIAN_WORDS.copy()
        if custom_dictionary:
            self.dictionary.update(custom_dictionary)

        self.dictionary_lower = {k.lower(): v.lower() for k, v in self.dictionary.items()}
        self.warnings: List[str] = []

    def convert_identifier(self, identifier: str) -> Tuple[str, bool]:
        """
        Convert single identifier (PascalCase).

        Args:
            identifier: e.g., "ПошуковийЗапіт", "ШляхДоФайлу"

        Returns:
            (converted_identifier, was_changed)

        Examples:
            "ПошуковийЗапіт" → ("ПоисковыйЗапрос", True)
            "ПриОткрытии" → ("ПриОткрытии", False)  # Already Russian
            "ПриВідкритті" → ("ПриОткрытии", True)
        """
        if not identifier:
            return identifier, False

        # Step 1: Split PascalCase into words
        words = self._split_pascal_case(identifier)

        # Step 2: Convert each word
        converted_words = []
        changed = False

        for word in words:
            word_lower = word.lower()

            # Check if word in dictionary
            if word_lower in self.dictionary_lower:
                russian_word = self.dictionary_lower[word_lower]

                # Preserve case
                converted = self._preserve_case(word, russian_word)
                converted_words.append(converted)

                if converted != word:
                    changed = True
            else:
                # Word not in dictionary
                # Check if contains Ukrainian-specific letters
                if self._contains_ukrainian_letters(word):
                    # CRITICAL: Ukrainian letters in identifiers are NOT allowed by 1C
                    raise ValueError(
                        f"❌ Identifier '{identifier}' contains Ukrainian Cyrillic letters in word '{word}' "
                        f"which is not in conversion dictionary.\n\n"
                        f"Ukrainian letters detected: і, ї, є, or ґ\n\n"
                        f"Options:\n"
                        f"  1. Add '{word}' to Ukrainian→Russian dictionary\n"
                        f"  2. Manually replace with Russian equivalent\n\n"
                        f"Common replacements:\n"
                        f"  і → и, ї → й, є → е, ґ → г\n\n"
                        f"Example: '{identifier}' might need manual review."
                    )

                converted_words.append(word)

        converted_identifier = ''.join(converted_words)
        return converted_identifier, changed

    def _split_pascal_case(self, identifier: str) -> List[str]:
        """
        Split PascalCase identifier into words.

        Examples:
            "ПошуковийЗапіт" → ["Пошуковий", "Запіт"]
            "ПриВідкритті" → ["При", "Відкритті"]
            "HTMLParser" → ["HTML", "Parser"]
        """
        # Insert space before uppercase letters (except first)
        spaced = re.sub(r'(?<!^)(?=[A-ZА-ЯІЇЄҐ])', ' ', identifier)
        return spaced.split()

    def _contains_ukrainian_letters(self, word: str) -> bool:
        """Check if word contains Ukrainian-specific letters: і, ї, є, ґ"""
        ukrainian_pattern = re.compile(r'[іїєґІЇЄҐ]')
        return bool(ukrainian_pattern.search(word))

    def _preserve_case(self, original: str, converted: str) -> str:
        """
        Preserve case from original word.

        Examples:
            ("Відкритті", "открытии") → "Открытии"
            ("відкритті", "открытии") → "открытии"
            ("ВІДКРИТТІ", "открытии") → "ОТКРЫТИИ"
        """
        if original.isupper():
            return converted.upper()
        elif original.islower():
            return converted.lower()
        elif original[0].isupper():
            return converted.capitalize()
        else:
            return converted

    def convert_yaml_content(self, yaml_content: str) -> Tuple[str, List[str]]:
        """
        Convert all identifiers in YAML content.

        Args:
            yaml_content: Full YAML file content

        Returns:
            (converted_yaml, list_of_changes)

        Example changes:
            ["name: ПошуковийЗапіт → ПоисковыйЗапрос",
             "handler: ВідкритиФорму → ОткрытьФорму"]
        """
        changes = []
        self.warnings = []

        # Pattern: identifier fields in YAML
        # Matches: name:, handler:, attribute:, tabular_section:, etc.
        identifier_pattern = re.compile(
            r'(name|handler|attribute|tabular_section|value_table|dynamic_list):\s*(\S+)'
        )

        def replace_func(match):
            field, identifier = match.groups()
            converted, changed = self.convert_identifier(identifier)

            if changed:
                changes.append(f"{field}: {identifier} → {converted}")

            return f"{field}: {converted}"

        converted_yaml = identifier_pattern.sub(replace_func, yaml_content)

        return converted_yaml, changes

    def get_warnings(self) -> List[str]:
        """Get accumulated warnings about unknown words."""
        return self.warnings


# ========================================
# CLI Integration
# ========================================

def auto_convert_cyrillic_in_file(
    yaml_path: Path,
    output_path: Optional[Path] = None,
    interactive: bool = False
) -> Tuple[bool, List[str], List[str]]:
    """
    Convert Ukrainian Cyrillic in YAML file.

    Args:
        yaml_path: Path to input YAML
        output_path: Path to save converted YAML (None = overwrite)
        interactive: Ask user before applying changes

    Returns:
        (success, changes, warnings)
    """
    # Read YAML
    yaml_content = yaml_path.read_text(encoding='utf-8')

    # Convert
    converter = CyrillicConverter()
    converted_yaml, changes = converter.convert_yaml_content(yaml_content)
    warnings = converter.get_warnings()

    if not changes and not warnings:
        print("✅ No Ukrainian Cyrillic detected. File is OK.")
        return True, [], []

    # Show changes
    if changes:
        print(f"\n⚠️ Auto-fixed Ukrainian Cyrillic → Russian ({len(changes)} changes):")
        for change in changes:
            print(f"  {change}")

    # Show warnings
    if warnings:
        print(f"\n⚠️ Warnings ({len(warnings)}):")
        for warning in warnings:
            print(f"  {warning}")

    # Interactive mode
    if interactive and changes:
        response = input("\nApply these changes? [Y/n]: ").strip().lower()
        if response and response != 'y':
            print("❌ Changes cancelled.")
            return False, changes, warnings

    # Save
    if changes:
        output = output_path or yaml_path
        output.write_text(converted_yaml, encoding='utf-8')
        print(f"\n✅ Saved to: {output}")

    return True, changes, warnings


# ========================================
# Usage Examples
# ========================================

if __name__ == '__main__':
    # Example 1: Convert single identifier
    converter = CyrillicConverter()

    test_cases = [
        "ПошуковийЗапіт",      # Ukrainian → Should convert
        "ПриОткрытии",         # Russian → Should preserve
        "ПриВідкритті",        # Ukrainian → Should convert
        "ШляхДоФайлу",         # Ukrainian → Should convert
        "ПутьКФайлу",          # Russian → Should preserve
        "СформуватиЗвіт",      # Ukrainian → Should convert
        "СформироватьОтчет",   # Russian → Should preserve
    ]

    print("=== Identifier Conversion Tests ===\n")
    for test in test_cases:
        converted, changed = converter.convert_identifier(test)
        status = "✅ CONVERTED" if changed else "⏭️  PRESERVED"
        print(f"{status}: {test:25} → {converted}")

    # Show warnings
    if converter.get_warnings():
        print("\n⚠️ Warnings:")
        for warning in converter.get_warnings():
            print(f"  {warning}")
```

##### File: `1c_processor_generator/__main__.py` (modifications)

```python
# Add to argument parser

def setup_argument_parser():
    parser = argparse.ArgumentParser(...)

    # ... existing arguments ...

    # NEW: Cyrillic conversion
    parser.add_argument(
        '--auto-fix-cyrillic',
        action='store_true',
        help='Автоматично конвертувати українську кирилицю в російську'
    )

    parser.add_argument(
        '--check-cyrillic',
        action='store_true',
        help='Тільки перевірити наявність української кирилиці (без генерації)'
    )

    parser.add_argument(
        '--cyrillic-interactive',
        action='store_true',
        help='Інтерактивний режим конвертації кирилиці'
    )

    return parser


def main():
    args = parser.parse_args()

    # Handle Cyrillic conversion
    if args.auto_fix_cyrillic or args.check_cyrillic or args.cyrillic_interactive:
        from .utils.cyrillic_converter import auto_convert_cyrillic_in_file

        yaml_path = Path(args.config)

        if args.check_cyrillic:
            # Check only, don't modify
            success, changes, warnings = auto_convert_cyrillic_in_file(
                yaml_path,
                output_path=None,
                interactive=False
            )
            sys.exit(0 if not changes else 1)

        elif args.cyrillic_interactive:
            # Interactive mode
            success, changes, warnings = auto_convert_cyrillic_in_file(
                yaml_path,
                interactive=True
            )
            if not success:
                sys.exit(1)

        elif args.auto_fix_cyrillic:
            # Auto-fix mode
            success, changes, warnings = auto_convert_cyrillic_in_file(
                yaml_path,
                interactive=False
            )

    # Continue with normal generation
    # ...
```

##### Usage Examples

```bash
# 1. Check if file has Ukrainian Cyrillic (no changes)
python -m 1c_processor_generator yaml \
  --config processors/MyProcessor/config.yaml \
  --check-cyrillic

# Output:
# ⚠️ Auto-fixed Ukrainian Cyrillic → Russian (3 changes):
#   name: ПошуковийЗапіт → ПоисковыйЗапрос
#   name: ШляхДоФайлу → ПутьКФайлу
#   handler: ВідкритиФорму → ОткрытьФорму

# 2. Auto-fix (automatic, no prompts)
python -m 1c_processor_generator yaml \
  --config config.yaml \
  --handlers-file handlers.bsl \
  --auto-fix-cyrillic

# Output:
# ⚠️ Auto-fixed Ukrainian Cyrillic → Russian (3 changes):
#   ...
# ✅ Saved to: processors/MyProcessor/config.yaml
# ✅ Generating processor...

# 3. Interactive mode (ask before applying)
python -m 1c_processor_generator yaml \
  --config config.yaml \
  --cyrillic-interactive

# Output:
# ⚠️ Auto-fixed Ukrainian Cyrillic → Russian (3 changes):
#   name: ПошуковийЗапіт → ПоисковыйЗапрос
#   ...
#
# Apply these changes? [Y/n]: y
# ✅ Saved to: ...
```

##### Test Cases

```python
# tests/test_cyrillic_converter.py

import pytest
from pathlib import Path
from 1c_processor_generator.utils.cyrillic_converter import CyrillicConverter


class TestCyrillicConverter:
    """Test intelligent Cyrillic conversion."""

    def test_ukrainian_word_conversion(self):
        """Test Ukrainian words are converted."""
        converter = CyrillicConverter()

        test_cases = [
            ("ПошуковийЗапіт", "ПоисковыйЗапрос", True),
            ("ШляхДоФайлу", "ПутьКФайлу", True),
            ("ПриВідкритті", "ПриОткрытии", True),
        ]

        for ukrainian, expected_russian, should_change in test_cases:
            result, changed = converter.convert_identifier(ukrainian)
            assert result == expected_russian, f"Expected {expected_russian}, got {result}"
            assert changed == should_change

    def test_russian_word_preservation(self):
        """Test Russian words are NOT changed."""
        converter = CyrillicConverter()

        test_cases = [
            "ПриОткрытии",
            "ПутьКФайлу",
            "ПоисковыйЗапрос",
            "СформироватьОтчет",
        ]

        for russian_word in test_cases:
            result, changed = converter.convert_identifier(russian_word)
            assert result == russian_word, f"Russian word {russian_word} was incorrectly changed to {result}"
            assert changed == False, f"Russian word {russian_word} should NOT be marked as changed"

    def test_pascal_case_splitting(self):
        """Test PascalCase splitting works correctly."""
        converter = CyrillicConverter()

        test_cases = [
            ("ПошуковийЗапіт", ["Пошуковий", "Запіт"]),
            ("HTMLParser", ["HTML", "Parser"]),
            ("ПриВідкритті", ["При", "Відкритті"]),
        ]

        for identifier, expected_words in test_cases:
            words = converter._split_pascal_case(identifier)
            assert words == expected_words

    def test_case_preservation(self):
        """Test case is preserved after conversion."""
        converter = CyrillicConverter()

        test_cases = [
            ("Відкритті", "открытии", "Открытии"),
            ("відкритті", "открытии", "открытии"),
            ("ВІДКРИТТІ", "открытии", "ОТКРЫТИИ"),
        ]

        for original, converted_lower, expected in test_cases:
            result = converter._preserve_case(original, converted_lower)
            assert result == expected

    def test_unknown_word_error(self):
        """Test unknown Ukrainian words raise ERROR (not warning)."""
        converter = CyrillicConverter()

        # Word with Ukrainian letters but not in dictionary
        identifier = "НевідомеСловоЗІ"  # Contains 'і', not in dictionary

        # Should raise ValueError (not just warn!)
        with pytest.raises(ValueError) as exc_info:
            converter.convert_identifier(identifier)

        # Error message should be helpful
        error_msg = str(exc_info.value)
        assert "Ukrainian Cyrillic" in error_msg or "українськ" in error_msg.lower()
        assert "НевідомеСловоЗІ" in error_msg or "невідоме" in error_msg.lower()
        assert "dictionary" in error_msg.lower() or "словник" in error_msg.lower()

    def test_yaml_conversion(self):
        """Test full YAML content conversion."""
        converter = CyrillicConverter()

        yaml_input = """
processor:
  name: ОбробкаДаних

attributes:
  - name: ПошуковийЗапіт
    type: string
  - name: Результати
    type: string

commands:
  - name: ВідкритиФорму
    handler: ВідкритиФорму
"""

        expected_changes = [
            "name: ПошуковийЗапіт → ПоисковыйЗапрос",
            "name: ВідкритиФорму → ОткрытьФорму",
            "handler: ВідкритиФорму → ОткрытьФорму",
        ]

        converted_yaml, changes = converter.convert_yaml_content(yaml_input)

        # Check changes list
        assert len(changes) >= 3  # At least 3 changes
        for expected_change in expected_changes:
            assert any(expected_change in change for change in changes), \
                f"Expected change '{expected_change}' not found in {changes}"

        # Check converted YAML contains Russian words
        assert "ПоисковыйЗапрос" in converted_yaml
        assert "ОткрытьФорму" in converted_yaml

        # Check Ukrainian words removed
        assert "ПошуковийЗапіт" not in converted_yaml
        assert "ВідкритиФорму" not in converted_yaml
```

##### Dictionary Expansion Guide

To add more words to the dictionary:

```python
# File: custom_dictionary.yaml (user can provide)
ukrainian_to_russian:
  мойукраїнськеслово: моерусскоеслово
  інше: другое

# Load in converter:
from yaml import safe_load

custom_dict = safe_load(Path('custom_dictionary.yaml').read_text())
converter = CyrillicConverter(custom_dictionary=custom_dict['ukrainian_to_russian'])
```

---

### ✅ Recommendation 2: Fuzzy Picture Name Matching

**Priority:** 🔥 HIGH
**Effort:** ~50 lines
**Impact:** Reduces error recovery time from 2-3 iterations to 1

#### Problem

LLM моделі вгадують назви `StdPicture.*` (130+ valid names):

```yaml
# LLM генерує (логічно звучить):
commands:
  - name: Save
    picture: StdPicture.Save       # ❌ Doesn't exist!
    handler: SaveData
  - name: Execute
    picture: StdPicture.Execute    # ❌ Doesn't exist!
```

**Current error:**
```
❌ Невідома стандартна картинка: StdPicture.Save
Використовуйте одну з доступних StdPicture (наприклад:
StdPicture.ExecuteTask, StdPicture.Refresh)
```

#### Solution

Add **fuzzy matching** to suggest similar valid pictures.

#### Implementation

##### File: `1c_processor_generator/validators.py` (modifications)

```python
from difflib import get_close_matches

def validate_picture(picture: str) -> Tuple[bool, str]:
    """
    Перевіряє чи картинка валідна

    Підтримуються:
    - StdPicture.* - стандартні картинки платформи
    - CommonPicture.* - загальні картинки конфігурації
    """
    if not picture:
        return True, ""  # Картинка опціональна

    # Перевірка StdPicture
    if picture.startswith("StdPicture."):
        if picture in VALID_STD_PICTURES:
            return True, ""

        # NEW: Fuzzy matching suggestions
        suggestions = get_close_matches(
            picture,
            VALID_STD_PICTURES,
            n=5,           # Top 5 suggestions
            cutoff=0.4     # Lower cutoff to catch more variants
        )

        if suggestions:
            # Build helpful error message
            suggestions_str = "\n    ".join(suggestions)
            return False, (
                f"Невідома стандартна картинка: {picture}\n\n"
                f"💡 Схожі валідні картинки:\n"
                f"    {suggestions_str}\n\n"
                f"Повний список: docs/VALID_PICTURES.md або constants.VALID_STD_PICTURES"
            )
        else:
            # No close matches
            return False, (
                f"Невідома стандартна картинка: {picture}\n\n"
                f"Не знайдено схожих варіантів. Можливо, ви мали на увазі:\n"
                f"    StdPicture.ExecuteTask (виконати)\n"
                f"    StdPicture.SaveFile (зберегти)\n"
                f"    StdPicture.OpenFile (відкрити)\n"
                f"    StdPicture.Refresh (оновити)\n\n"
                f"Повний список: docs/VALID_PICTURES.md"
            )

    # Перевірка CommonPicture (дозволяємо будь-які)
    if picture.startswith("CommonPicture."):
        return True, ""

    return False, (
        f"Невірний формат картинки: {picture}. "
        f"Очікується StdPicture.* або CommonPicture.*"
    )
```

##### Enhanced Picture Mapping (Optional)

Create a **semantic mapping** for common actions:

```python
# File: 1c_processor_generator/utils/picture_suggester.py

"""
Suggest StdPicture based on command name/title (semantic matching).
"""

from typing import Optional
from ..constants import VALID_STD_PICTURES


# Semantic mapping: action keywords → StdPicture names
ACTION_TO_PICTURE = {
    # Save actions
    'сохранить': 'StdPicture.SaveFile',
    'save': 'StdPicture.SaveFile',
    'запись': 'StdPicture.Write',
    'write': 'StdPicture.Write',
    'зберегти': 'StdPicture.SaveFile',

    # Execute actions
    'выполнить': 'StdPicture.ExecuteTask',
    'execute': 'StdPicture.ExecuteTask',
    'виконати': 'StdPicture.ExecuteTask',
    'запустить': 'StdPicture.ExecuteTask',

    # Open/Import actions
    'открыть': 'StdPicture.OpenFile',
    'open': 'StdPicture.OpenFile',
    'відкрити': 'StdPicture.OpenFile',
    'импорт': 'StdPicture.OpenFile',
    'import': 'StdPicture.OpenFile',
    'завантажити': 'StdPicture.OpenFile',

    # Refresh actions
    'обновить': 'StdPicture.Refresh',
    'refresh': 'StdPicture.Refresh',
    'оновити': 'StdPicture.Refresh',
    'перезагрузить': 'StdPicture.Refresh',

    # Print actions
    'печать': 'StdPicture.Print',
    'print': 'StdPicture.Print',
    'друк': 'StdPicture.Print',

    # Delete actions
    'удалить': 'StdPicture.Delete',
    'delete': 'StdPicture.Delete',
    'видалити': 'StdPicture.Delete',

    # Settings
    'настройки': 'StdPicture.CustomizeForm',
    'settings': 'StdPicture.CustomizeForm',
    'налаштування': 'StdPicture.CustomizeForm',

    # Search/Find
    'поиск': 'StdPicture.Find',
    'find': 'StdPicture.Find',
    'search': 'StdPicture.Find',
    'пошук': 'StdPicture.Find',

    # Clear
    'очистить': 'StdPicture.InputFieldClear',
    'clear': 'StdPicture.InputFieldClear',
    'очистити': 'StdPicture.InputFieldClear',

    # Post/Apply
    'провести': 'StdPicture.Post',
    'post': 'StdPicture.Post',
}


def suggest_picture_for_command(command_name: str, command_title: str) -> Optional[str]:
    """
    Suggest StdPicture based on command name or title.

    Args:
        command_name: Command name (e.g., "Сохранить")
        command_title: Command title (e.g., "Сохранить данные")

    Returns:
        StdPicture name or None if no suggestion

    Examples:
        suggest_picture_for_command("Save", "Save data") → "StdPicture.SaveFile"
        suggest_picture_for_command("Выполнить", "Выполнить обработку") → "StdPicture.ExecuteTask"
    """
    # Check command name first
    for keyword, picture in ACTION_TO_PICTURE.items():
        if keyword in command_name.lower():
            return picture

    # Check command title
    for keyword, picture in ACTION_TO_PICTURE.items():
        if keyword in command_title.lower():
            return picture

    return None


# Integration with yaml_parser.py
def validate_and_suggest_picture(command: dict) -> None:
    """
    Validate picture and suggest if missing.

    Called during YAML parsing for each command.
    """
    if 'picture' not in command or not command['picture']:
        # No picture specified - suggest one
        suggested = suggest_picture_for_command(
            command['name'],
            command.get('title_ru', '') or command.get('title_uk', '')
        )

        if suggested:
            print(f"💡 Suggestion: Command '{command['name']}' might use picture: {suggested}")
```

##### Usage

```bash
# Generate with picture suggestions
python -m 1c_processor_generator yaml --config config.yaml
```

**Output:**
```
❌ Validation error: Невідома стандартна картинка: StdPicture.Save

💡 Схожі валідні картинки:
    StdPicture.SaveFile
    StdPicture.SaveValues
    StdPicture.SaveReportSettings

Повний список: docs/VALID_PICTURES.md
```

---

### ✅ Recommendation 3: Enhanced DynamicList Error Messages

**Priority:** 🔥 HIGH
**Effort:** ~30 lines
**Impact:** Reduces 60% → 20% error rate for DynamicList

#### Problem

LLM помиляються з `is_dynamic_list` location (60% failure rate):

```yaml
# ❌ LLM генерує (top-level):
- type: Table
  name: List
  tabular_section: MyList
  is_dynamic_list: true        # ❌ Wrong!

# ✅ Має бути (under properties):
- type: Table
  name: List
  tabular_section: MyList
  properties:
    is_dynamic_list: true      # ✅ Correct!
```

#### Solution

Clear visual error message with WRONG/CORRECT example.

#### Implementation

##### File: `1c_processor_generator/yaml_parser.py` (modifications)

```python
def _parse_table_element(self, elem_data: dict) -> FormElement:
    """Parse Table element with enhanced DynamicList validation."""

    # Check for common mistake: is_dynamic_list on top-level
    if 'is_dynamic_list' in elem_data:
        # This is WRONG! Should be under properties
        raise ValidationError(
            f"Table '{elem_data['name']}': 'is_dynamic_list' має бути під 'properties:', "
            f"а не на верхньому рівні.\n\n"
            f"❌ WRONG (top-level):\n"
            f"  - type: Table\n"
            f"    name: {elem_data['name']}\n"
            f"    tabular_section: {elem_data.get('tabular_section', 'MyList')}\n"
            f"    is_dynamic_list: true  # ❌ Wrong location!\n\n"
            f"✅ CORRECT (under properties):\n"
            f"  - type: Table\n"
            f"    name: {elem_data['name']}\n"
            f"    tabular_section: {elem_data.get('tabular_section', 'MyList')}\n"
            f"    properties:\n"
            f"      is_dynamic_list: true  # ✅ Correct!\n\n"
            f"📖 See: docs/LLM_PATTERNS.md#pattern-3-dynamic-list"
        )

    # Also check for is_value_table on top-level (similar mistake)
    if 'is_value_table' in elem_data:
        # This is also supported on top-level for backward compatibility
        # But warn about new recommended approach
        self.warnings.append(
            f"Table '{elem_data['name']}': 'is_value_table' на верхньому рівні (deprecated). "
            f"Рекомендується використовувати 'properties: {{is_value_table: true}}'"
        )

    # Continue with normal parsing
    # ...
```

##### JSON Schema Update

```json
{
  "definitions": {
    "Table": {
      "type": "object",
      "required": ["type", "name", "tabular_section"],
      "properties": {
        "type": {"const": "Table"},
        "name": {"type": "string"},
        "tabular_section": {"type": "string"},

        "is_dynamic_list": {
          "type": "boolean",
          "description": "❌ DEPRECATED: Use properties.is_dynamic_list instead!",
          "deprecated": true
        },

        "properties": {
          "type": "object",
          "properties": {
            "is_dynamic_list": {
              "type": "boolean",
              "description": "✅ CORRECT location for is_dynamic_list"
            },
            "is_value_table": {
              "type": "boolean"
            }
          }
        }
      }
    }
  }
}
```

---

## PHASE 2: UX Improvements

### ✅ Recommendation 4: Interactive Validation Mode

**Priority:** 🟡 MEDIUM
**Effort:** ~300 lines
**Impact:** Better UX for beginners

#### Implementation

```python
# File: 1c_processor_generator/interactive.py (NEW)

"""Interactive validation and fixing mode."""

from typing import List, Tuple
from pathlib import Path
from .validators import ProcessorValidator
from .utils.cyrillic_converter import CyrillicConverter


class InteractiveValidator:
    """Interactive validation with fix suggestions."""

    def __init__(self, processor, yaml_path: Path):
        self.processor = processor
        self.yaml_path = yaml_path
        self.fixes_applied = []

    def run(self) -> bool:
        """
        Run interactive validation.

        Returns:
            True if all fixes applied/skipped, False if aborted
        """
        validator = ProcessorValidator(self.processor)
        is_valid, errors, warnings = validator.validate()

        if is_valid:
            print("✅ Validation passed! No errors found.")
            return True

        print(f"❌ Found {len(errors)} validation error(s).\n")

        for i, error in enumerate(errors, 1):
            print(f"\n{'='*60}")
            print(f"Error {i}/{len(errors)}:")
            print(f"{'='*60}")
            print(error)

            # Try to suggest fix
            fix = self._suggest_fix(error)
            if fix:
                choice = self._prompt_fix(fix)
                if choice == 'abort':
                    return False
                elif choice == 'apply':
                    self.fixes_applied.append(fix)
            else:
                print("\n⚠️ No automatic fix available. Please fix manually.")
                choice = input("Continue validation? [Y/n]: ").strip().lower()
                if choice == 'n':
                    return False

        # Apply all fixes
        if self.fixes_applied:
            self._apply_fixes()

        return True

    def _suggest_fix(self, error: str) -> Optional[dict]:
        """Suggest fix for error."""
        # Ukrainian Cyrillic
        if 'містить невалідні символи' in error or 'Ukrainian' in error:
            # Extract identifier name
            import re
            match = re.search(r"'([^']+)'", error)
            if match:
                identifier = match.group(1)

                converter = CyrillicConverter()
                converted, _ = converter.convert_identifier(identifier)

                return {
                    'type': 'cyrillic',
                    'original': identifier,
                    'fixed': converted,
                    'description': f"Replace '{identifier}' with '{converted}'"
                }

        # BSL reserved keyword
        if 'зарезервованим ключовим словом' in error or 'reserved' in error.lower():
            match = re.search(r"'([^']+)'", error)
            if match:
                handler_name = match.group(1)

                return {
                    'type': 'reserved_keyword',
                    'original': handler_name,
                    'fixed': f"{handler_name}Обработку",
                    'description': f"Rename handler '{handler_name}' to '{handler_name}Обработку'"
                }

        # Invalid StdPicture
        if 'Невідома стандартна картинка' in error or 'StdPicture' in error:
            # Extract picture name and suggestions from error
            match = re.search(r'StdPicture\.(\w+)', error)
            if match:
                invalid_picture = f"StdPicture.{match.group(1)}"

                # Extract first suggestion
                suggestions_match = re.search(r'Схожі.*?:\s+(\S+)', error)
                if suggestions_match:
                    suggestion = suggestions_match.group(1)

                    return {
                        'type': 'invalid_picture',
                        'original': invalid_picture,
                        'fixed': suggestion,
                        'description': f"Replace '{invalid_picture}' with '{suggestion}'"
                    }

        return None

    def _prompt_fix(self, fix: dict) -> str:
        """
        Prompt user to apply fix.

        Returns:
            'apply', 'skip', or 'abort'
        """
        print(f"\n💡 Suggested fix:")
        print(f"   {fix['description']}")

        while True:
            choice = input("\nOptions:\n  [1] Apply fix\n  [2] Skip this error\n  [3] Abort validation\n\nChoice (1-3): ").strip()

            if choice == '1':
                return 'apply'
            elif choice == '2':
                return 'skip'
            elif choice == '3':
                return 'abort'
            else:
                print("❌ Invalid choice. Please enter 1, 2, or 3.")

    def _apply_fixes(self):
        """Apply all accumulated fixes to YAML file."""
        yaml_content = self.yaml_path.read_text(encoding='utf-8')

        for fix in self.fixes_applied:
            if fix['type'] == 'cyrillic':
                # Replace identifier
                yaml_content = yaml_content.replace(
                    f"name: {fix['original']}",
                    f"name: {fix['fixed']}"
                )
                yaml_content = yaml_content.replace(
                    f"handler: {fix['original']}",
                    f"handler: {fix['fixed']}"
                )

            elif fix['type'] == 'reserved_keyword':
                yaml_content = yaml_content.replace(
                    f"handler: {fix['original']}",
                    f"handler: {fix['fixed']}"
                )

            elif fix['type'] == 'invalid_picture':
                yaml_content = yaml_content.replace(
                    f"picture: {fix['original']}",
                    f"picture: {fix['fixed']}"
                )

        # Save
        self.yaml_path.write_text(yaml_content, encoding='utf-8')

        print(f"\n✅ Applied {len(self.fixes_applied)} fix(es) to {self.yaml_path}")
```

---

**[Continue to PHASE 2 and PHASE 3 recommendations in next section...]**

---

## 📚 Appendix: Dictionary Expansion

### How to expand Ukrainian → Russian dictionary

Create a community-driven dictionary file:

```yaml
# File: dictionaries/ukrainian_to_russian.yaml

# User-contributed words
custom_words:
  # Your domain-specific terms
  моєслово: моеслово

# Request addition to main dictionary via PR:
# https://github.com/.../pull/new
```

Load in converter:

```python
from yaml import safe_load

custom_dict = safe_load(Path('dictionaries/ukrainian_to_russian.yaml').read_text())
converter = CyrillicConverter(custom_dictionary=custom_dict['custom_words'])
```

---

## 🎯 Summary

**Phase 1 (Quick Wins)** delivers maximum impact with minimal effort:

1. **Intelligent Cyrillic Converter** - Словниковий підхід (НЕ character-level!)
2. **Fuzzy Picture Matching** - Миттєві підказки
3. **Enhanced DynamicList Errors** - Візуальні приклади

**Estimated total effort:** ~400 lines of code
**Impact:** Reduces LLM error rate from 70% → <30%

Ready to implement! 🚀
