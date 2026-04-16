"""
EPF Tester - test execution for generated processors via COM (v2.17.0+)

Refactored with dependency injection (Phase 1: ABC Architecture):
- EPFTester receives connection object instead of creating it
- Connection types: ExternalConnection, AutomationServerConnection
- Clean separation of concerns

Supports:
- External Connection (fast, no UI)
- Automation Server (full connection with UI) - Phase 2
- Declarative tests (from YAML)
- Procedural tests (BSL files)
"""

import logging
from typing import Optional, List, Tuple
from dataclasses import dataclass

from .models import (
    DeclarativeTest,
    TestSetup,
    TestAssertion,
    MessageAssertion,
    TableAssertion,
    TestFixture,
)
from .connection_base import BaseConnection

# Import COM support flag from external_connection
# This is needed for conftest.py to check if pywin32 is available
try:
    from .external_connection import HAS_COM_SUPPORT
except ImportError:
    # Fallback if external_connection cannot be imported
    HAS_COM_SUPPORT = False

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Result of a single test execution."""
    test_name: str
    passed: bool
    error_message: Optional[str] = None
    execution_time: float = 0.0  # seconds
    module_type: str = "ObjectModule"  # "ObjectModule" or "FormModule"


class EPFTester:
    """
    Class for testing generated EPF files through COM.

    Architecture (v2.17.0+):
    - Dependency injection: receives connection object
    - Connection types: ExternalConnection, AutomationServerConnection
    - Delegates all COM operations to connection object

    Example:
        >>> from 1c_processor_generator.external_connection import ExternalConnection
        >>> conn = ExternalConnection(epf_path=Path("Calculator.epf"), ib_path=Path("temp_ib"))
        >>> tester = EPFTester(connection=conn)
        >>> tester.connect()
        >>> result = tester.run_declarative_test(test_config)
        >>> tester.disconnect()
    """

    def __init__(self, connection: BaseConnection, fixtures: Optional[dict] = None):
        """
        Args:
            connection: Connection object (ExternalConnection or AutomationServerConnection)
            fixtures: Dict of TestFixture objects (v2.20.0+)
        """
        self.connection = connection
        self.fixtures = fixtures or {}  # v2.20.0+ Fixtures support

    def connect(self) -> bool:
        """
        Establish connection to 1C infobase.

        Delegates to connection.connect().

        Returns:
            True if successful
        """
        return self.connection.connect()

    def disconnect(self):
        """Close connection."""
        self.connection.disconnect()

    def get_processor(self):
        """Get processor COM object."""
        return self.connection.get_processor()

    def set_attribute(self, attr_name: str, value):
        """Set processor attribute value."""
        self.connection.set_attribute(attr_name, value)

    def get_attribute(self, attr_name: str):
        """Get processor attribute value."""
        return self.connection.get_attribute(attr_name)

    def execute_command(self, command_name: str):
        """Execute processor command."""
        self.connection.execute_command(command_name)

    def execute_procedure(self, procedure_name: str):
        """Execute BSL procedure."""
        self.connection.execute_procedure(procedure_name)

    def start_message_recording(self):
        """Start message recording."""
        self.connection.start_message_recording()

    def get_test_messages(self) -> List[str]:
        """Get recorded messages."""
        return self.connection.get_test_messages()

    def apply_setup(self, setup: TestSetup):
        """Apply setup (set attributes, fill tables)."""
        # Set attributes
        for attr_name, value in setup.attributes.items():
            self.set_attribute(attr_name, value)

        # Fill tables
        for table_name, rows in setup.table_rows.items():
            self.connection.fill_table(table_name, rows)

    def apply_fixtures(self, fixture_names: List[str]):
        """Apply fixtures before test setup (v2.20.0+).

        Fixtures are applied in the order specified in use_fixtures.
        Each fixture's setup is applied using apply_setup().

        Args:
            fixture_names: List of fixture names to apply

        Raises:
            ValueError: If fixture name is not found in self.fixtures
        """
        for fixture_name in fixture_names:
            if fixture_name not in self.fixtures:
                raise ValueError(f"Fixture '{fixture_name}' not found. Available fixtures: {list(self.fixtures.keys())}")

            fixture = self.fixtures[fixture_name]
            logger.debug(f"Applying fixture: {fixture_name}")
            self.apply_setup(fixture.setup)

    def check_assertion(self, assertion: TestAssertion) -> Tuple[bool, Optional[str]]:
        """
        Check assertion (v2.19.0+: extended assertions support).

        Returns:
            (passed, error_message)
        """
        # Import extended assertion helper
        from .assertion_helper import check_extended_assertion, check_message_assertion_extended

        # Check attributes (with extended assertions support)
        for attr_name, expected in assertion.attributes.items():
            actual_value = self.get_attribute(attr_name)

            # Use extended assertion checker
            passed, error = check_extended_assertion(actual_value, expected, attr_name)
            if not passed:
                return False, error

        # Check messages (with extended assertions support v2.19.0+)
        if assertion.messages:
            messages = self.get_test_messages()
            for msg_assert in assertion.messages:
                # Use extended message assertion checker
                passed, error = check_message_assertion_extended(messages, msg_assert)
                if not passed:
                    return False, error

        # Check tables
        for table_assert in assertion.tables:
            if not self._check_table_assertion(table_assert):
                return False, f"Table {table_assert.table_name} does not match assertions"

        return True, None

    def _check_message_assertion(self, messages: List[str], assertion: MessageAssertion) -> bool:
        """Check message assertion."""
        if assertion.count is not None:
            if len(messages) != assertion.count:
                logger.error(f"Message count: expected {assertion.count}, got {len(messages)}")
                return False

        if assertion.contains:
            found = any(assertion.contains in msg for msg in messages)
            if not found:
                logger.error(f"Message does not contain '{assertion.contains}'. Received: {messages}")
                return False

        if assertion.equals:
            found = any(assertion.equals == msg for msg in messages)
            if not found:
                logger.error(f"Message does not equal '{assertion.equals}'. Received: {messages}")
                return False

        return True

    def _check_table_assertion(self, assertion: TableAssertion) -> bool:
        """Check table assertion."""
        try:
            processor = self.get_processor()
            obj = getattr(processor, "Объект", processor)
            table = getattr(obj, assertion.table_name)

            # Check row count
            if assertion.row_count is not None:
                actual_count = table.Количество()
                if actual_count != assertion.row_count:
                    logger.error(f"Table {assertion.table_name}: expected {assertion.row_count} rows, got {actual_count}")
                    return False

            # Check columns (verify they exist)
            for column in assertion.columns:
                try:
                    # Try to get column value from first row
                    if table.Количество() > 0:
                        first_row = table.Получить(0)
                        getattr(first_row, column)
                except:
                    logger.error(f"Table {assertion.table_name}: column {column} not found")
                    return False

            return True

        except Exception as e:
            logger.error(f"❌ Error checking table {assertion.table_name}: {e}")
            return False

    def run_declarative_test(self, test: DeclarativeTest) -> TestResult:
        """
        Execute declarative test.

        Returns:
            TestResult
        """
        import time
        start_time = time.time()

        try:
            logger.info(f"▶️  Running test: {test.name}")

            # 1. Start message recording
            self.start_message_recording()

            # 2. Apply fixtures (v2.20.0+)
            if test.use_fixtures:
                self.apply_fixtures(test.use_fixtures)

            # 3. Setup (applied AFTER fixtures)
            if test.setup:
                self.apply_setup(test.setup)

            # 4. Execute
            if test.execute_command:
                self.execute_command(test.execute_command)
            elif test.execute_procedure:
                self.execute_procedure(test.execute_procedure)

            # 5. Assert
            if test.assert_result:
                # Check for exception
                if test.assert_result.exception:
                    # If expecting exception but none occurred - fail
                    if test.assert_result.exception.raised:
                        return TestResult(
                            test_name=test.name,
                            passed=False,
                            error_message="Expected exception but none was raised",
                            execution_time=time.time() - start_time,
                        )
                else:
                    # Check assertions
                    passed, error = self.check_assertion(test.assert_result)
                    if not passed:
                        return TestResult(
                            test_name=test.name,
                            passed=False,
                            error_message=error,
                            execution_time=time.time() - start_time,
                        )

            # Test passed
            logger.info(f"✅ Test {test.name} passed")
            return TestResult(
                test_name=test.name,
                passed=True,
                execution_time=time.time() - start_time,
            )

        except Exception as e:
            # If expecting exception
            if test.assert_result and test.assert_result.exception:
                if test.assert_result.exception.raised:
                    error_text = str(e)

                    # Check if exception contains required text
                    if test.assert_result.exception.contains:
                        if test.assert_result.exception.contains in error_text:
                            logger.info(f"✅ Test {test.name} passed (exception expected)")
                            return TestResult(
                                test_name=test.name,
                                passed=True,
                                execution_time=time.time() - start_time,
                            )
                        else:
                            return TestResult(
                                test_name=test.name,
                                passed=False,
                                error_message=f"Exception does not contain '{test.assert_result.exception.contains}'. Got: {error_text}",
                                execution_time=time.time() - start_time,
                            )
                    else:
                        # Exception expected, got exception - OK
                        logger.info(f"✅ Test {test.name} passed (exception expected)")
                        return TestResult(
                            test_name=test.name,
                            passed=True,
                            execution_time=time.time() - start_time,
                        )

            # Exception not expected
            logger.error(f"❌ Test {test.name} failed: {e}")
            return TestResult(
                test_name=test.name,
                passed=False,
                error_message=str(e),
                execution_time=time.time() - start_time,
            )

    def run_procedural_test(self, procedure_name: str) -> TestResult:
        """
        Execute procedural test (BSL procedure Тест_*).

        Returns:
            TestResult
        """
        import time
        start_time = time.time()

        try:
            logger.info(f"▶️  Running BSL test: {procedure_name}")

            # Execute procedure
            self.execute_procedure(procedure_name)

            # If no exception - test passed
            logger.info(f"✅ Test {procedure_name} passed")
            return TestResult(
                test_name=procedure_name,
                passed=True,
                execution_time=time.time() - start_time,
            )

        except Exception as e:
            logger.error(f"❌ Test {procedure_name} failed: {e}")
            return TestResult(
                test_name=procedure_name,
                passed=False,
                error_message=str(e),
                execution_time=time.time() - start_time,
            )
