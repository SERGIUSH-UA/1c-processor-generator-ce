"""
Designer Log Parser - парсинг логів 1C Designer.

v2.38.0 Technical Debt Refactoring - Phase 4.1

Централізований парсинг логів Designer для команд:
- /CheckModules (синтаксична перевірка BSL)
- /CheckConfig (семантична перевірка конфігурації)

Використання:
    >>> from designer_log_parser import DesignerLogParser, ValidationError
    >>> parser = DesignerLogParser()
    >>> errors, warnings = parser.parse_check_modules_log(Path("check.log"))
    >>> for error in errors:
    ...     print(f"{error.module}:{error.line}: {error.message}")
"""

import re
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """
    Результат валідації BSL модуля.

    Представляє одну помилку або попередження з Designer.

    Attributes:
        module: Назва модуля (e.g., 'Модуль объекта обработки "ProcessorName"')
        line: Номер рядка з помилкою
        column: Номер колонки
        message: Текст помилки
        severity: 'error' | 'warning'

    Example:
        >>> error = ValidationError(
        ...     module='Module.ObjectModule',
        ...     line=45,
        ...     column=12,
        ...     message='Неизвестный метод "Test"',
        ...     severity='error'
        ... )
    """
    module: str
    line: int
    column: int
    message: str
    severity: str  # 'error' | 'warning'

    def __str__(self) -> str:
        """Форматований вивід помилки."""
        return f"{self.module}:{self.line}:{self.column}: [{self.severity}] {self.message}"


class DesignerLogParser:
    """
    Парсер логів Designer для /CheckModules і /CheckConfig.

    Підтримує два формати виводу помилок Designer:
    1. "Строка 45, Колонка 12: Неизвестный метод..."
    2. "{Module.Path(45,25)}: Message"

    Класифікує помилки за ключовими словами на errors та warnings.

    Example:
        >>> parser = DesignerLogParser()
        >>> errors, warnings = parser.parse_check_modules_log(Path("log.txt"))
        >>> print(f"Errors: {len(errors)}, Warnings: {len(warnings)}")
    """

    # Ключові слова для класифікації помилок
    ERROR_KEYWORDS = [
        'ошибка', 'error',
        'неизвестн', 'unknown',
        'несуществ', 'not found', 'does not exist',
        'не найден', 'не определ',
        'недопустим', 'invalid',
        'нельзя', 'cannot',
        'ожидается', 'expected',  # "Ожидается символ ';'"
        'неопознан', 'unrecognized',  # "Неопознанный оператор"
    ]

    # Regex патерни для парсингу
    # Формат 1: "Строка 45, Колонка 12: Неизвестный метод..."
    PATTERN_RU = re.compile(
        r'[Сс]трока\s+(\d+)[,\s]+[Кк]олонка\s+(\d+):\s*(.+?)(?:\n|$)'
    )
    # Формат 2: "{Module.Path(45,25)}: Message"
    PATTERN_PATH = re.compile(
        r'\{([^\}]+)\((\d+),(\d+)\)\}:\s*(.+?)(?:\n|$)'
    )

    def parse_check_modules_log(
        self,
        log_file: Path,
        result_file: Optional[Path] = None
    ) -> Tuple[List[ValidationError], List[ValidationError]]:
        """
        Парсить лог /CheckModules або /CheckConfig.

        Args:
            log_file: Шлях до лог файлу Designer (/Out)
            result_file: Шлях до файлу результату (/DumpResult) - опціонально

        Returns:
            Tuple (errors, warnings) - списки ValidationError

        Example:
            >>> parser = DesignerLogParser()
            >>> errors, warnings = parser.parse_check_modules_log(Path("check.log"))
            >>> for e in errors:
            ...     print(f"Line {e.line}: {e.message}")
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []

        # Читаємо основний лог
        if not log_file.exists():
            logger.warning(f"Check modules log not found: {log_file}")
            return errors, warnings

        try:
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                log_content = f.read()
        except Exception as e:
            logger.error(f"Failed to read log file: {e}")
            return errors, warnings

        # Парсимо вміст
        errors, warnings = self._parse_content(log_content)

        logger.debug(
            f"Parsed check modules log: {len(errors)} errors, {len(warnings)} warnings"
        )

        return errors, warnings

    def parse_log_content(self, content: str) -> Tuple[List[ValidationError], List[ValidationError]]:
        """
        Парсить вміст логу напряму (для тестування).

        Args:
            content: Текстовий вміст логу

        Returns:
            Tuple (errors, warnings)
        """
        return self._parse_content(content)

    def _parse_content(
        self,
        content: str
    ) -> Tuple[List[ValidationError], List[ValidationError]]:
        """
        Внутрішній метод парсингу контенту.

        Args:
            content: Текст логу Designer

        Returns:
            Tuple (errors, warnings)
        """
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []
        current_module = "Unknown"

        for line in content.split('\n'):
            # Визначаємо поточний модуль
            if "Модуль" in line or "Module" in line:
                # Приклад: "Модуль объекта обработки \"ProcessorName\":"
                current_module = line.strip().rstrip(':')

            # Шукаємо помилки/попередження
            validation_entry = self._parse_line(line, current_module)

            if validation_entry:
                # Оновлюємо current_module якщо парсер знайшов шлях модуля
                if validation_entry.module != current_module:
                    current_module = validation_entry.module

                if validation_entry.severity == 'error':
                    errors.append(validation_entry)
                else:
                    warnings.append(validation_entry)

        return errors, warnings

    def _parse_line(self, line: str, current_module: str) -> Optional[ValidationError]:
        """
        Парсить один рядок логу.

        Args:
            line: Рядок логу
            current_module: Поточний модуль для контексту

        Returns:
            ValidationError або None якщо рядок не містить помилки
        """
        line_num = 0
        column = 0
        message = ""
        module = current_module

        # Формат 1: "Строка 45, Колонка 12: message"
        match = self.PATTERN_RU.search(line)
        if match:
            line_num = int(match.group(1))
            column = int(match.group(2))
            message = match.group(3).strip()
        else:
            # Формат 2: "{Module(line,col)}: message"
            match = self.PATTERN_PATH.search(line)
            if match:
                module = match.group(1)
                line_num = int(match.group(2))
                column = int(match.group(3))
                message = match.group(4).strip()

        if not match:
            return None

        # Класифікація: error vs warning
        severity = self._classify_severity(message)

        return ValidationError(
            module=module,
            line=line_num,
            column=column,
            message=message,
            severity=severity
        )

    def _classify_severity(self, message: str) -> str:
        """
        Класифікує повідомлення як error або warning.

        Args:
            message: Текст повідомлення

        Returns:
            'error' або 'warning'
        """
        message_lower = message.lower()
        is_error = any(keyword in message_lower for keyword in self.ERROR_KEYWORDS)
        return 'error' if is_error else 'warning'

    def format_errors(
        self,
        errors: List[ValidationError],
        max_count: int = 10
    ) -> str:
        """
        Форматує список помилок для виводу.

        Args:
            errors: Список помилок
            max_count: Максимальна кількість для виводу

        Returns:
            Форматований рядок

        Example:
            >>> formatted = parser.format_errors(errors, max_count=5)
            >>> print(formatted)
        """
        if not errors:
            return "No errors"

        lines = []
        for i, error in enumerate(errors[:max_count], 1):
            lines.append(
                f"  {i}. {error.module}\n"
                f"     Line {error.line}, Col {error.column}: {error.message}"
            )

        if len(errors) > max_count:
            lines.append(f"  ... and {len(errors) - max_count} more errors")

        return '\n'.join(lines)

    def to_dict_list(
        self,
        validation_errors: List[ValidationError]
    ) -> List[dict]:
        """
        Конвертує список ValidationError у список словників.

        Для зворотної сумісності з існуючим кодом epf_compiler.

        Args:
            validation_errors: Список ValidationError

        Returns:
            Список словників з ключами: line, column, message, module
        """
        return [
            {
                'line': e.line,
                'column': e.column,
                'message': e.message,
                'module': e.module
            }
            for e in validation_errors
        ]
