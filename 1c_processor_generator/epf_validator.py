"""
EPF Validator - перевірка синтаксису зовнішніх обробок (EPF файлів)

Модуль забезпечує автоматичну валідацію згенерованих EPF файлів
через запуск validator.epf в 1С:Підприємство.

Приклад використання:
    validator = EPFValidator()
    result = validator.validate_epf(Path("MyProcessor.epf"))

    if result.success:
        print("✓ Syntax OK")
    else:
        print(f"✗ Errors found: {result.error_count}")
"""

from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
import logging

# Налаштування логування
logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """Одна помилка валідації EPF файлу."""
    line: int
    column: int
    message: str
    severity: str  # 'error', 'warning', 'info'
    module: str = "Unknown"  # ObjectModule, FormModule, etc.

    def __str__(self) -> str:
        return f"[{self.severity.upper()}] Line {self.line}, Col {self.column}: {self.message}"


@dataclass
class ValidationResult:
    """Результат валідації EPF файлу."""
    success: bool
    epf_path: Path

    # Статистика
    error_count: int
    warning_count: int

    # Детальні помилки
    errors: List[ValidationError]

    # Додаткова інформація
    elapsed_time: float  # секунди
    log_content: str
    log_file: Optional[Path] = None

    def __str__(self) -> str:
        if self.success:
            return f"✓ Validation passed ({self.elapsed_time:.1f}s)"
        else:
            return (f"✗ Validation failed: {self.error_count} errors, "
                   f"{self.warning_count} warnings ({self.elapsed_time:.1f}s)")


class EPFValidator:
    """
    Валідатор синтаксису EPF файлів через validator.epf.

    Використовує validator.epf для базової перевірки синтаксису:
    - Критичні синтаксичні помилки
    - Помилки компіляції BSL коду

    Приклад використання:
        validator = EPFValidator()
        result = validator.validate_epf(
            epf_path=Path("MyProcessor.epf"),
            timeout=60
        )

        if result.success:
            print("✓ Syntax is correct")
        else:
            for error in result.errors:
                print(f"  {error}")
    """

    def __init__(self, platform_path: Optional[str] = None):
        """
        Ініціалізація EPF валідатора.

        Args:
            platform_path: Явний шлях до 1C platform.
                          Якщо не вказано - виконується автоматичний пошук.
        """
        self.platform_path = platform_path
        self.validator_epf = Path(__file__).parent / "resources" / "validator.epf"
        logger.debug("EPFValidator initialized")

    def validate_epf(
        self,
        epf_path: Path,
        timeout: int = 60,
        keep_log: bool = False
    ) -> ValidationResult:
        """
        Перевірка синтаксису EPF файлу.

        Args:
            epf_path: Шлях до EPF файлу для перевірки
            timeout: Таймаут виконання в секундах (за замовчуванням 60)
            keep_log: Зберегти лог файл після валідації

        Returns:
            ValidationResult з детальним звітом

        Raises:
            FileNotFoundError: Якщо epf_path не існує
            RuntimeError: Якщо 1C platform або validator.epf не знайдено
        """
        raise NotImplementedError(
            "EPF validation requires PRO license. "
            "Contact support for licensing options."
        )
