"""
Base Connection interface for 1C:Enterprise EPF testing (v2.17.0+)

Defines abstract interface for different connection types:
- ExternalConnection (fast, no UI) ✅ WORKS
- AutomationServerConnection (slow, with UI, form access) ❌ NOT IMPLEMENTED (COM limitation)

v2.20.1+: Extracted common code (_load_from_configuration, _load_processor_external) to reduce duplication
v2.24.0+: AutomationServerConnection cannot be implemented (see automation_connection.py)
"""

from abc import ABC, abstractmethod
from typing import Any, List, Dict, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class BaseConnection(ABC):
    """
    Abstract base class for 1C:Enterprise connections.

    Implementations:
    - ExternalConnection: Uses V83.COMConnector (fast, no UI) ✅ WORKS
    - AutomationServerConnection: Uses V83.Application (slow, UI, forms) ❌ NOT IMPLEMENTED
      (Cannot be implemented due to COM limitations - see automation_connection.py)

    Connection lifecycle:
    1. __init__() - configure connection parameters
    2. connect() - establish connection and load processor
    3. execute_*() - run tests
    4. disconnect() - cleanup
    """

    def __init__(
        self,
        epf_path: Path,
        ib_path: Path,
        load_from_configuration: bool = False,
        processor_name: Optional[str] = None,
        debug: bool = False,
    ):
        """
        Args:
            epf_path: Path to EPF file
            ib_path: Path to test infobase
            load_from_configuration: Load processor from configuration metadata (v2.16.0+)
            processor_name: Processor name for configuration mode
            debug: Enable debug logging
        """
        self.epf_path = epf_path
        self.ib_path = ib_path
        self.load_from_configuration = load_from_configuration
        self.processor_name = processor_name
        self.debug = debug

        # COM objects (initialized by connect())
        self.connection = None
        self.processor = None

    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to 1C infobase and load processor.

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    def disconnect(self):
        """Close connection and cleanup resources."""
        pass

    def get_processor(self):
        """
        Get processor object.

        Returns:
            COM processor object
        """
        return self.processor

    @abstractmethod
    def set_attribute(self, attr_name: str, value: Any):
        """
        Set processor attribute value.

        Args:
            attr_name: Attribute name
            value: Value to set
        """
        pass

    @abstractmethod
    def get_attribute(self, attr_name: str) -> Any:
        """
        Get processor attribute value.

        Args:
            attr_name: Attribute name

        Returns:
            Attribute value
        """
        pass

    @abstractmethod
    def execute_command(self, command_name: str):
        """
        Execute processor command.

        Args:
            command_name: Command handler name (e.g., "Calculate")
        """
        pass

    @abstractmethod
    def execute_procedure(self, procedure_name: str):
        """
        Execute BSL procedure.

        Args:
            procedure_name: Procedure name (e.g., "Тест_Addition")
        """
        pass

    @abstractmethod
    def fill_table(self, table_name: str, rows: List[Dict[str, Any]]):
        """
        Fill tabular section with rows.

        Args:
            table_name: Tabular section name
            rows: List of row data (dict with column names -> values)
        """
        pass

    @abstractmethod
    def start_message_recording(self):
        """Start message recording (calls НачатьЗаписьСообщений)."""
        pass

    @abstractmethod
    def get_test_messages(self) -> List[str]:
        """
        Get recorded messages (calls ПолучитьТестовыеСообщения).

        Returns:
            List of message strings
        """
        pass

    # Common implementation methods (v2.20.1+ DRY refactoring)

    def _load_processor_external(self) -> bool:
        """
        Load processor as external data processor.

        Common implementation for both ExternalConnection and AutomationServerConnection.
        Uses self.connection.ExternalDataProcessors.Create().

        Returns:
            True if successful
        """
        try:
            logger.info(f"Loading processor: {self.epf_path}...")

            # Load EPF as external processor
            self.processor = self.connection.ExternalDataProcessors.Create(str(self.epf_path))

            logger.info("✅ Processor loaded")
            return True

        except Exception as e:
            logger.error(f"❌ Processor loading error: {e}")
            return False

    def _load_from_configuration(self) -> bool:
        """
        Load processor from configuration metadata (v2.16.0+).

        Used when processor is already loaded INTO configuration via /LoadConfigFromFiles.
        This solves security warning when loading external processor.

        Common implementation for both ExternalConnection and AutomationServerConnection.

        Returns:
            True if successful
        """
        try:
            logger.info(f"Loading processor from configuration: {self.processor_name}_Validation...")

            # Load processor from configuration metadata
            # During compilation, processor is added with "_Validation" suffix
            processor_full_name = f"{self.processor_name}_Validation"

            # Call: connection.DataProcessors.ProcessorName_Validation.Create()
            self.processor = getattr(
                self.connection.DataProcessors,
                processor_full_name
            ).Create()

            logger.info("✅ Processor loaded from configuration (no security warning)")
            return True

        except AttributeError:
            logger.error(f"❌ Processor '{processor_full_name}' not found in configuration")
            logger.error(f"   Ensure temp_ib contains Configuration with processor")
            return False

        except Exception as e:
            logger.error(f"❌ Configuration processor loading error: {e}")
            return False
