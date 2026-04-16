"""
Test Generator - генератор pytest файлів для тестування EPF (v2.16.0+)

Генерує:
- test_*.py файли з pytest тестами
- conftest.py з fixtures для COM підключення
- Копіює BSL процедурні тести
"""

import logging
from pathlib import Path
from typing import Optional
from jinja2 import Environment, FileSystemLoader

from .models import TestsConfig, Processor

logger = logging.getLogger(__name__)


class TestGenerator:
    """
    Генератор pytest тестів для EPF файлів.

    Example:
        >>> generator = TestGenerator(
        ...     processor=processor,
        ...     tests_config=tests_config,
        ...     output_dir="output/Calculator/tests"
        ... )
        >>> generator.generate()
    """

    def __init__(
        self,
        processor: Processor,
        tests_config: TestsConfig,
        output_dir: Path,
        epf_path: Path,
        persistent_ib_path: Optional[Path] = None,
    ):
        """
        Args:
            processor: Processor object
            tests_config: TestsConfig object
            output_dir: Директорія для згенерованих тестів
            epf_path: Шлях до EPF файлу
            persistent_ib_path: Шлях до persistent IB (опціонально)
        """
        self.processor = processor
        self.tests_config = tests_config
        self.output_dir = Path(output_dir)
        self.epf_path = Path(epf_path)
        self.persistent_ib_path = persistent_ib_path

        # Jinja2 environment
        templates_dir = Path(__file__).parent / "templates"
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        # Додаємо Python функції в Jinja2 globals
        self.jinja_env.globals["repr"] = repr

    def generate(self) -> bool:
        """
        Генерує всі тестові файли

        Returns:
            True якщо успішно
        """
        try:
            # Створюємо output директорію
            self.output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Генерація тестів в {self.output_dir}...")

            # 1. Генеруємо conftest.py
            self._generate_conftest()

            # 2. Генеруємо test_<ProcessorName>.py
            self._generate_test_file()

            # 3. Копіюємо BSL процедурні тести (якщо є)
            if self.tests_config.procedural_tests:
                self._copy_procedural_tests()

            # 4. Створюємо __init__.py
            (self.output_dir / "__init__.py").write_text("# Auto-generated tests\n")

            logger.info("✅ Тести згенеровано успішно")
            return True

        except Exception as e:
            logger.error(f"❌ Помилка генерації тестів: {e}")
            return False

    def _generate_conftest(self):
        """Генерує conftest.py з fixtures"""
        logger.info("Генерація conftest.py...")

        template = self.jinja_env.get_template("conftest.py.j2")
        content = template.render(
            processor_name=self.processor.name,
            epf_path=str(self.epf_path.absolute()),
            persistent_ib_path=str(self.persistent_ib_path.absolute()) if self.persistent_ib_path else None,
            use_external_connection=self.tests_config.use_external_connection,
            use_automation_server=self.tests_config.use_automation_server,
            load_from_configuration=True,  # v2.16.0+: завантажуємо обробку з конфігурації
        )

        output_file = self.output_dir / "conftest.py"
        output_file.write_text(content, encoding="utf-8")
        logger.info(f"✅ {output_file}")

    def _generate_test_file(self):
        """Генерує test_<ProcessorName>.py"""
        logger.info(f"Генерація test_{self.processor.name}.py...")

        template = self.jinja_env.get_template("test_file.py.j2")
        content = template.render(
            processor_name=self.processor.name,
            tests_config=self.tests_config,
            declarative_tests=self.tests_config.declarative_tests,
            procedural_tests=self.tests_config.procedural_tests,
        )

        output_file = self.output_dir / f"test_{self.processor.name}.py"
        output_file.write_text(content, encoding="utf-8")
        logger.info(f"✅ {output_file}")

    def _copy_procedural_tests(self):
        """Копіює BSL файл з процедурними тестами"""
        if not self.tests_config.procedural_tests:
            return

        logger.info("Копіювання процедурних тестів...")

        source = Path(self.tests_config.procedural_tests.file)
        if not source.exists():
            logger.warning(f"⚠️  BSL файл не знайдено: {source}")
            return

        # Копіюємо файл в tests директорію
        dest = self.output_dir / source.name
        dest.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        logger.info(f"✅ Скопійовано {source} -> {dest}")

    def inject_procedural_tests_into_objectmodule(
        self,
        objectmodule_path: Path,
        output_path: Path
    ) -> bool:
        """
        Інжектує procedural tests в ObjectModule для створення test-ready EPF.

        Args:
            objectmodule_path: Шлях до чистого ObjectModule.bsl
            output_path: Шлях для збереження ObjectModule_WithTests.bsl

        Returns:
            True якщо успішно інжектовано

        Architecture (v2.23.0):
        - Reads clean ObjectModule.bsl
        - Parses procedural tests from BSL file
        - Injects test procedures with Экспорт keyword
        - Saves to ObjectModule_WithTests.bsl
        - Original ObjectModule stays clean
        """
        if not self.tests_config.procedural_tests:
            logger.info("⏭️  Немає procedural tests для інжекту")
            return False

        try:
            logger.info("💉 Інжектування procedural tests в ObjectModule...")

            # 1. Read clean ObjectModule
            if not objectmodule_path.exists():
                logger.error(f"❌ ObjectModule не знайдено: {objectmodule_path}")
                return False

            objectmodule_content = objectmodule_path.read_text(encoding="utf-8-sig")

            # 2. Read procedural tests BSL file
            tests_bsl_path = Path(self.tests_config.procedural_tests.file)
            if not tests_bsl_path.exists():
                logger.error(f"❌ Procedural tests BSL не знайдено: {tests_bsl_path}")
                return False

            tests_content = tests_bsl_path.read_text(encoding="utf-8-sig")

            # 3. Extract test procedures
            test_procedures = self._extract_test_procedures(tests_content)

            if not test_procedures:
                logger.warning("⚠️  Не знайдено test procedures в BSL файлі")
                return False

            logger.info(f"📋 Знайдено {len(test_procedures)} test procedure(s)")

            # 4. Inject test procedures into ObjectModule
            injected_content = self._inject_procedures(objectmodule_content, test_procedures)

            # 5. Save to output path
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(injected_content, encoding="utf-8-sig")

            logger.info(f"✅ ObjectModule з тестами: {output_path}")
            logger.info(f"📊 Інжектовано процедур: {len(test_procedures)}")

            return True

        except Exception as e:
            logger.error(f"❌ Помилка інжекту procedural tests: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _extract_test_procedures(self, bsl_content: str) -> list:
        """
        Витягує test procedures з BSL файлу.

        Returns:
            List of procedure strings with full signature and body

        NOTE (v2.23.0): Procedural tests are injected AS-IS into ObjectModule.
        User must write tests in ObjectModule style (no Объект., no &НаСервере).
        For form module tests with Объект. / &НаСервере, use --use-automation-server flag.
        """
        import re

        procedures = []

        # Pattern для процедур: &НаСервере Процедура Name() ... КонецПроцедуры
        # Supports both Процедура and Функция
        pattern = r'(&НаСервере\s+)?(Процедура|Функция)\s+([А-Яа-яA-Za-z0-9_]+)\s*\([^)]*\).*?Конец(Процедуры|Функции)'

        matches = re.finditer(pattern, bsl_content, re.DOTALL | re.IGNORECASE)

        for match in matches:
            procedure_text = match.group(0)
            procedure_name = match.group(3)

            # Check if it's a test procedure (starts with Тест_)
            if procedure_name.startswith("Тест_"):
                # Ensure it has Экспорт keyword
                if "Экспорт" not in procedure_text:
                    # Add Экспорт before procedure body
                    procedure_text = procedure_text.replace(
                        f"{match.group(2)} {procedure_name}",
                        f"{match.group(2)} {procedure_name}() Экспорт",
                        1
                    )

                procedures.append({
                    "name": procedure_name,
                    "text": procedure_text,
                    "type": match.group(2)  # Процедура or Функция
                })

                logger.debug(f"  ✓ Extracted: {procedure_name}")

        return procedures

    def _inject_procedures(self, objectmodule_content: str, test_procedures: list) -> str:
        """
        Інжектує test procedures в ObjectModule.

        Strategy:
        - Add #Область Тестування at the end (before closing regions if any)
        - Add all test procedures inside this region
        - Keep original ObjectModule clean and readable
        """
        # Build injection content
        injection = "\n\n#Область Тестування\n\n"
        injection += "// ========================================================================\n"
        injection += "// AUTO-GENERATED TEST PROCEDURES (v2.23.0+)\n"
        injection += "// \n"
        injection += "// ⚠️ WARNING: This ObjectModule contains test procedures.\n"
        injection += "//            For production EPF, use clean ObjectModule without tests.\n"
        injection += "//            This version is used ONLY for test_runner.py\n"
        injection += "// ========================================================================\n\n"

        for proc in test_procedures:
            injection += proc["text"] + "\n\n"

        injection += "#КонецОбласти // Тестування\n"

        # Inject at the end of ObjectModule (before any closing regions)
        # Simple approach: append at the end
        result = objectmodule_content.rstrip() + "\n" + injection

        return result
