"""
Test Parser для генератора зовнішніх обробок 1C (v2.16.0+)

Парсить tests.yaml конфігурацію та створює TestsConfig об'єкт
"""

import yaml
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from .models import (
    TestsConfig,
    ObjectModuleTestsConfig,
    FormTestsConfig,
    DeclarativeTest,
    ProceduralTests,
    TestSetup,
    TestAssertion,
    MessageAssertion,
    TableAssertion,
    ExceptionAssertion,
    TestFixture,
)


class TestParser:
    """Парсер tests.yaml конфігурації в TestsConfig об'єкт"""

    def __init__(self, tests_yaml_path: Path):
        """
        Args:
            tests_yaml_path: Шлях до tests.yaml файлу
        """
        self.tests_yaml_path = Path(tests_yaml_path)
        self.config: Dict = {}

    def load_yaml(self) -> bool:
        """
        Load tests.yaml file

        Returns:
            True if successful, False on error
        """
        try:
            with open(self.tests_yaml_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
            return True
        except Exception as e:
            print(f"❌ Error reading tests.yaml: {e}")
            return False

    def validate_schema(self) -> bool:
        """
        Validate tests.yaml against JSON Schema

        Returns:
            True if valid, False on errors
        """
        try:
            # Load schema
            schema_path = Path(__file__).parent / "test_schema.json"
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = json.load(f)

            # Validation requires jsonschema library
            try:
                import jsonschema
            except ImportError:
                print("⚠️  jsonschema not installed, skipping schema validation")
                print("   Install with: pip install jsonschema")
                return True  # Skip validation but continue

            # Validate
            jsonschema.validate(instance=self.config, schema=schema)
            return True

        except jsonschema.ValidationError as e:
            print(f"❌ Error validating tests.yaml:")
            print(f"   {e.message}")
            if e.path:
                print(f"   Path: {' -> '.join(str(p) for p in e.path)}")
            return False
        except Exception as e:
            print(f"❌ Schema validation error: {e}")
            return False

    def parse_message_assertion(self, data: Dict[str, Any]) -> MessageAssertion:
        """Парсить MessageAssertion з YAML"""
        return MessageAssertion(
            contains=data.get("contains"),
            equals=data.get("equals"),
            count=data.get("count"),
        )

    def parse_table_assertion(self, data: Dict[str, Any]) -> TableAssertion:
        """Парсить TableAssertion з YAML"""
        return TableAssertion(
            table_name=data["table_name"],
            row_count=data.get("row_count"),
            columns=data.get("columns", []),
            row_data=data.get("row_data"),
        )

    def parse_exception_assertion(self, data: Dict[str, Any]) -> ExceptionAssertion:
        """Парсить ExceptionAssertion з YAML"""
        return ExceptionAssertion(
            raised=data.get("raised", True),
            contains=data.get("contains"),
        )

    def parse_test_setup(self, data: Dict[str, Any]) -> TestSetup:
        """Парсить TestSetup з YAML"""
        return TestSetup(
            attributes=data.get("attributes", {}),
            table_rows=data.get("table_rows", {}),
        )

    def parse_test_fixture(self, name: str, data: Dict[str, Any]) -> TestFixture:
        """Парсить TestFixture з YAML (v2.20.0+)

        Args:
            name: Ім'я фікстури (ключ з fixtures секції)
            data: Дані фікстури з YAML

        Returns:
            TestFixture об'єкт
        """
        setup = self.parse_test_setup(data)
        return TestFixture(name=name, setup=setup)

    def parse_test_assertion(self, data: Dict[str, Any]) -> TestAssertion:
        """Парсить TestAssertion з YAML"""
        messages = []
        if "messages" in data:
            messages = [self.parse_message_assertion(m) for m in data["messages"]]

        tables = []
        if "tables" in data:
            tables = [self.parse_table_assertion(t) for t in data["tables"]]

        exception = None
        if "exception" in data:
            exception = self.parse_exception_assertion(data["exception"])

        return TestAssertion(
            attributes=data.get("attributes", {}),
            messages=messages,
            tables=tables,
            exception=exception,
        )

    def parse_declarative_test(self, data: Dict[str, Any]) -> DeclarativeTest:
        """Парсить DeclarativeTest з YAML (v2.20.0+ with validation)"""
        test_name = data["name"]

        # Validate execute_command XOR execute_procedure
        execute_command = data.get("execute_command")
        execute_procedure = data.get("execute_procedure")

        if execute_command and execute_procedure:
            raise ValueError(
                f"Test '{test_name}' has both execute_command and execute_procedure. "
                "Only one is allowed."
            )

        if not execute_command and not execute_procedure:
            raise ValueError(
                f"Test '{test_name}' must have either execute_command or execute_procedure."
            )

        # Validate fixture references (v2.20.0+)
        use_fixtures = data.get("use_fixtures", [])
        available_fixtures = self.config.get("fixtures", {})

        for fixture_name in use_fixtures:
            if fixture_name not in available_fixtures:
                raise ValueError(
                    f"Test '{test_name}' references unknown fixture '{fixture_name}'. "
                    f"Available fixtures: {list(available_fixtures.keys())}"
                )

        setup = None
        if "setup" in data:
            setup = self.parse_test_setup(data["setup"])

        assert_result = None
        if "assert" in data:
            assert_result = self.parse_test_assertion(data["assert"])

        return DeclarativeTest(
            name=test_name,
            description=data.get("description"),
            use_fixtures=use_fixtures,  # v2.20.0+ (validated)
            setup=setup,
            execute_command=execute_command,
            execute_procedure=execute_procedure,
            assert_result=assert_result,
        )

    def parse_procedural_tests(self, data: Dict[str, Any]) -> ProceduralTests:
        """Парсить ProceduralTests з YAML (v2.20.1+: with path traversal protection)"""
        file_path = data["file"]

        # Resolve path relative to tests.yaml directory
        base_dir = self.tests_yaml_path.parent.resolve()  # Normalize base directory

        if Path(file_path).is_absolute():
            # Absolute paths: resolve and validate
            resolved_path = Path(file_path).resolve()
        else:
            # Relative paths: resolve from tests.yaml directory
            resolved_path = (base_dir / file_path).resolve()

        # Path traversal protection (v2.20.1+)
        # Ensure resolved path is within base directory (or subdirectory)
        try:
            resolved_path.relative_to(base_dir)
        except ValueError:
            # Path is outside base directory - security risk
            raise ValueError(
                f"Security error: Procedural test file '{file_path}' resolves to '{resolved_path}' "
                f"which is outside the allowed directory '{base_dir}'. "
                f"Path traversal attacks (../) are not allowed."
            )

        return ProceduralTests(
            file=str(resolved_path),
            procedures=data.get("procedures", []),
        )

    def parse(self) -> Optional[TestsConfig]:
        """
        Парсить tests.yaml в TestsConfig об'єкт (v2.23.2+ new architecture)

        Returns:
            TestsConfig або None якщо помилка
        """
        # 1. Завантажуємо YAML
        if not self.load_yaml():
            return None

        # 2. Валідуємо schema
        if not self.validate_schema():
            return None

        # 3. Парсимо fixtures (v2.20.0+)
        fixtures = {}
        if "fixtures" in self.config:
            for fixture_name, fixture_data in self.config["fixtures"].items():
                fixtures[fixture_name] = self.parse_test_fixture(fixture_name, fixture_data)

        # 4. Парсимо objectmodule_tests (v2.23.2+)
        objectmodule_tests = None
        if "objectmodule_tests" in self.config:
            om_config = self.config["objectmodule_tests"]

            # Declarative tests
            declarative = []
            if "declarative" in om_config:
                for test_data in om_config["declarative"]:
                    declarative.append(self.parse_declarative_test(test_data))

            # Procedural tests
            procedural = None
            if "procedural" in om_config:
                procedural = self.parse_procedural_tests(om_config["procedural"])

            objectmodule_tests = ObjectModuleTestsConfig(
                declarative=declarative,
                procedural=procedural
            )

        # 5. Парсимо per-form tests (v2.23.2+)
        forms = []
        if "forms" in self.config:
            for form_data in self.config["forms"]:
                form_name = form_data["name"]

                # Declarative tests
                declarative = []
                if "declarative" in form_data:
                    for test_data in form_data["declarative"]:
                        declarative.append(self.parse_declarative_test(test_data))

                # Procedural tests
                procedural = None
                if "procedural" in form_data:
                    procedural = self.parse_procedural_tests(form_data["procedural"])

                forms.append(FormTestsConfig(
                    name=form_name,
                    declarative=declarative,
                    procedural=procedural
                ))

        # 6. Створюємо TestsConfig (v2.23.2+)
        tests_config = TestsConfig(
            objectmodule_tests=objectmodule_tests,
            forms=forms,
            fixtures=fixtures,
            persistent_ib_path=self.config.get("persistent_ib_path"),
            timeout=self.config.get("timeout", 300),
        )

        return tests_config


def parse_tests_yaml(tests_yaml_path: Path) -> Optional[TestsConfig]:
    """
    Функція-helper для парсингу tests.yaml

    Args:
        tests_yaml_path: Шлях до tests.yaml файлу

    Returns:
        TestsConfig або None якщо помилка
    """
    parser = TestParser(tests_yaml_path)
    return parser.parse()
