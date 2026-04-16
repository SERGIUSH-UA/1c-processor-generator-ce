"""
External Connection implementation for 1C:Enterprise EPF testing (v2.17.0+)

Fast connection type without UI. Uses V83.COMConnector.

Advantages:
- Fast (no UI overhead)
- Headless (can run on CI/CD)
- Direct processor access

Limitations:
- No form access (ПолучитьФорму unavailable)
- No modal dialogs
- No UI interaction
"""

import logging
import threading
import traceback
from typing import Any, List, Dict
from pathlib import Path

from .connection_base import BaseConnection

# COM support check
try:
    import win32com.client
    import pythoncom
    HAS_COM_SUPPORT = True
except ImportError:
    HAS_COM_SUPPORT = False

logger = logging.getLogger(__name__)


class ExternalConnection(BaseConnection):
    """
    External Connection to 1C:Enterprise using V83.COMConnector.

    Fast, headless connection for processor testing without UI.

    Example:
        >>> conn = ExternalConnection(epf_path=Path("Calculator.epf"), ib_path=Path("temp_ib"))
        >>> conn.connect()
        >>> conn.set_attribute("Number1", 10)
        >>> conn.execute_command("Calculate")
        >>> result = conn.get_attribute("Result")
        >>> conn.disconnect()
    """

    def connect(self) -> bool:
        """
        Establish External Connection to 1C infobase.

        Uses V83.COMConnector -> connector.Connect() -> ExternalDataProcessors.Create()

        Returns:
            True if successful
        """
        if not HAS_COM_SUPPORT:
            logger.error("❌ pywin32 not installed. COM connections unavailable.")
            logger.info("   Install: pip install pywin32")
            raise ImportError("pywin32 required for COM connections")

        try:
            logger.info(f"Connecting to {self.ib_path} via External Connection...")

            # DEBUG: Diagnostic info BEFORE connection
            if self.debug:
                import sys as _sys
                thread_id = threading.get_ident()
                logger.debug(f"🔍 DEBUG: Thread ID: {thread_id}")
                logger.debug(f"🔍 DEBUG: Python version: {_sys.version}")
                logger.debug(f"🔍 DEBUG: pywin32 version: {win32com.__version__ if hasattr(win32com, '__version__') else 'unknown'}")

                try:
                    com_count = pythoncom._GetInterfaceCount()
                    logger.debug(f"🔍 DEBUG: COM Interface Count (before): {com_count}")
                except Exception as e:
                    logger.debug(f"🔍 DEBUG: COM Interface Count unavailable: {e}")

            # Create COM connector
            logger.debug("Creating V83.COMConnector...")
            connector = win32com.client.Dispatch("V83.COMConnector")

            if self.debug:
                logger.debug(f"✅ V83.COMConnector created: {type(connector)}")
                try:
                    com_count = pythoncom._GetInterfaceCount()
                    logger.debug(f"🔍 DEBUG: COM Interface Count (after Dispatch): {com_count}")
                except:
                    pass

            # Build connection string
            conn_string = f"File='{self.ib_path}';Usr='';Pwd=''"
            if self.debug:
                logger.debug(f"🔍 DEBUG: Connection string: {conn_string}")

            # Connect
            logger.debug("Calling connector.Connect()...")
            self.connection = connector.Connect(conn_string)

            if self.debug:
                logger.debug(f"✅ connector.Connect() successful: {type(self.connection)}")
                try:
                    com_count = pythoncom._GetInterfaceCount()
                    logger.debug(f"🔍 DEBUG: COM Interface Count (after Connect): {com_count}")
                except:
                    pass

            logger.info("✅ External Connection established")

            # Load processor (from configuration or as external)
            # v2.20.1+: Methods inherited from BaseConnection (DRY refactoring)
            if self.load_from_configuration:
                return self._load_from_configuration()
            else:
                return self._load_processor_external()

        except Exception as e:
            logger.error(f"❌ External Connection error: {e}")

            # DEBUG: Detailed traceback
            if self.debug:
                logger.error(f"🔍 DEBUG: Exception type: {type(e).__name__}")
                logger.error(f"🔍 DEBUG: Exception args: {e.args}")
                logger.error(f"🔍 DEBUG: Detailed traceback:")
                logger.error(traceback.format_exc())

                try:
                    com_count = pythoncom._GetInterfaceCount()
                    logger.error(f"🔍 DEBUG: COM Interface Count (on error): {com_count}")
                except:
                    pass

            return False

    def disconnect(self):
        """Close connection and cleanup resources."""
        if self.connection:
            self.connection = None
            self.processor = None
            logger.info("Connection closed")

    def set_attribute(self, attr_name: str, value: Any):
        """Set processor attribute value."""
        try:
            # Access through Объект for processor attributes
            obj = getattr(self.processor, "Объект", self.processor)
            setattr(obj, attr_name, value)
            logger.debug(f"Set {attr_name} = {value}")
        except Exception as e:
            logger.error(f"❌ Error setting {attr_name}: {e}")
            raise

    def get_attribute(self, attr_name: str) -> Any:
        """Get processor attribute value."""
        try:
            obj = getattr(self.processor, "Объект", self.processor)
            return getattr(obj, attr_name)
        except Exception as e:
            logger.error(f"❌ Error reading {attr_name}: {e}")
            raise

    def execute_command(self, command_name: str):
        """Execute processor command."""
        try:
            # Call command handler method
            command_method = getattr(self.processor, command_name)
            command_method()
            logger.debug(f"Executed command: {command_name}")
        except Exception as e:
            logger.error(f"❌ Error executing command {command_name}: {e}")
            raise

    def execute_procedure(self, procedure_name: str):
        """Execute BSL procedure."""
        try:
            procedure = getattr(self.processor, procedure_name)
            procedure()
            logger.debug(f"Executed procedure: {procedure_name}")
        except Exception as e:
            logger.error(f"❌ Error executing procedure {procedure_name}: {e}")
            raise

    def fill_table(self, table_name: str, rows: List[Dict[str, Any]]):
        """Fill tabular section with rows."""
        try:
            obj = getattr(self.processor, "Объект", self.processor)
            table = getattr(obj, table_name)

            # Clear table
            table.Очистить()

            # Add rows
            for row_data in rows:
                row = table.Добавить()
                for column, value in row_data.items():
                    setattr(row, column, value)

            logger.debug(f"Filled {table_name}: {len(rows)} rows")

        except Exception as e:
            logger.error(f"❌ Error filling table {table_name}: {e}")
            raise

    def start_message_recording(self):
        """Start message recording (calls НачатьЗаписьСообщений)."""
        try:
            if hasattr(self.processor, "НачатьЗаписьСообщений"):
                self.processor.НачатьЗаписьСообщений()
                logger.debug("Message recording started")
            else:
                logger.warning("⚠️  Method НачатьЗаписьСообщений not found in processor")
        except Exception as e:
            logger.error(f"❌ Error starting message recording: {e}")

    def get_test_messages(self) -> List[str]:
        """
        Get recorded messages (calls ПолучитьТестовыеСообщения).

        Returns:
            List of message strings
        """
        try:
            if hasattr(self.processor, "ПолучитьТестовыеСообщения"):
                messages_array = self.processor.ПолучитьТестовыеСообщения()

                # Convert 1C array to Python list
                messages = []
                for i in range(messages_array.Количество()):
                    messages.append(str(messages_array.Получить(i)))

                return messages
            else:
                logger.warning("⚠️  Method ПолучитьТестовыеСообщения not found in processor")
                return []

        except Exception as e:
            logger.error(f"❌ Error getting messages: {e}")
            return []
