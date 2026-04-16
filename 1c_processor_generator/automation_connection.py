"""
Automation Server Connection for 1C:Enterprise EPF testing (v2.18.0+)

❌ STATUS: NOT IMPLEMENTED - CANNOT BE IMPLEMENTED

After extensive investigation (2025-11-18), we determined that V83.Application
fundamentally cannot be accessed from Python or PowerShell.

INVESTIGATION FINDINGS:
- V83.Application.Connect() fails with RPC_E_DISCONNECTED from Python
- PowerShell Connect() succeeds but object is hollow (no ВнешниеОбработки/Обработки)
- Same connection string works perfectly from 1C BSL code
- V83.COMConnector.ПолучитьФорму() fails with "Интерактивные операции недоступны"

ROOT CAUSE:
- LocalServer32 COM architecture limitation
- Process lifecycle management issues
- External Connection is headless by design (no form access)
- Possibly intentional restriction by 1C platform

WHAT WORKS:
✅ ExternalConnection (V83.COMConnector) for ObjectModule tests
✅ Business logic testing, data manipulation, command execution
✅ Declarative and procedural tests (ObjectModule-style only)

WHAT DOESN'T WORK:
❌ Form tests (requires V83.Application)
❌ UI interaction testing
❌ Button click simulation
❌ Form field testing via Automation Server

ALTERNATIVES:
- Use ExternalConnection for ObjectModule tests
- Manual form testing through 1C Configurator
- Consider web client automation (Selenium) for future

FULL REPORT: docs/research/V83_INVESTIGATION_REPORT.md

This module is kept for documentation purposes only.
All methods raise NotImplementedError.
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


class AutomationServerConnection(BaseConnection):
    """
    ❌ NOT IMPLEMENTED - Automation Server Connection to 1C:Enterprise using V83.Application.

    This class cannot be implemented due to fundamental COM limitations.
    All methods raise NotImplementedError.

    See module docstring for full explanation and alternative approaches.

    INTENDED USE (not possible):
        Full UI connection for form testing and user interaction simulation.

    Example (does NOT work):
        >>> conn = AutomationServerConnection(...)  # doctest: +SKIP
        >>> conn.connect()  # Raises NotImplementedError
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.automation = None  # V83.Application object
        self.form = None  # Form object (if accessed)

    def connect(self) -> bool:
        """
        ❌ NOT IMPLEMENTED

        V83.Application cannot be accessed from Python.
        See module docstring for details.

        Raises:
            NotImplementedError: Always raised
        """
        raise NotImplementedError(
            "AutomationServerConnection cannot be implemented due to COM limitations.\n"
            "\n"
            "V83.Application is not accessible from Python/PowerShell:\n"
            "  - Python: RPC_E_DISCONNECTED error\n"
            "  - PowerShell: Connect() succeeds but object is hollow\n"
            "  - Only works from 1C BSL code\n"
            "\n"
            "Forms also unavailable via V83.COMConnector:\n"
            "  - ПолучитьФорму fails with 'Интерактивные операции недоступны'\n"
            "  - External Connection is headless by design\n"
            "\n"
            "Use ExternalConnection (V83.COMConnector) for ObjectModule tests.\n"
            "See docs/research/V83_INVESTIGATION_REPORT.md for technical details."
        )

    def disconnect(self):
        """Close Automation Server connection and cleanup."""
        if self.form:
            self.form = None
        if self.automation:
            # V83.Application doesn't need explicit cleanup
            self.automation = None
            self.connection = None
            self.processor = None
            logger.info("Connection closed")

    def set_attribute(self, attr_name: str, value: Any):
        """
        Set processor/form attribute value.

        For Automation Server, tries form.Объект first, then processor.Объект.
        """
        try:
            # Try form first (if available)
            if self.form:
                obj = getattr(self.form, "Объект", None)
                if obj:
                    setattr(obj, attr_name, value)
                    logger.debug(f"Set {attr_name} = {value} (via form)")
                    return

            # Fallback to processor
            obj = getattr(self.processor, "Объект", self.processor)
            setattr(obj, attr_name, value)
            logger.debug(f"Set {attr_name} = {value}")

        except Exception as e:
            logger.error(f"❌ Error setting {attr_name}: {e}")
            raise

    def get_attribute(self, attr_name: str) -> Any:
        """
        Get processor/form attribute value.

        For Automation Server, tries form.Объект first, then processor.Объект.
        """
        try:
            # Try form first (if available)
            if self.form:
                obj = getattr(self.form, "Объект", None)
                if obj:
                    return getattr(obj, attr_name)

            # Fallback to processor
            obj = getattr(self.processor, "Объект", self.processor)
            return getattr(obj, attr_name)

        except Exception as e:
            logger.error(f"❌ Error reading {attr_name}: {e}")
            raise

    def execute_command(self, command_name: str):
        """
        Execute command on form.

        For Automation Server, calls form command, NOT direct processor method.
        """
        try:
            if self.form:
                # Try to execute through form commands
                # Form commands usually call НаСервере handlers
                command_handler = f"{command_name}НаСервере"
                if hasattr(self.form, command_handler):
                    handler = getattr(self.form, command_handler)
                    handler()
                    logger.debug(f"Executed form command: {command_handler}")
                    return

                # Fallback: try client handler
                if hasattr(self.form, command_name):
                    handler = getattr(self.form, command_name)
                    handler()
                    logger.debug(f"Executed form command: {command_name}")
                    return

            # Fallback to processor method
            command_method = getattr(self.processor, command_name)
            command_method()
            logger.debug(f"Executed processor command: {command_name}")

        except Exception as e:
            logger.error(f"❌ Error executing command {command_name}: {e}")
            raise

    def execute_procedure(self, procedure_name: str):
        """Execute BSL procedure."""
        try:
            # Try form first
            if self.form and hasattr(self.form, procedure_name):
                procedure = getattr(self.form, procedure_name)
                procedure()
                logger.debug(f"Executed form procedure: {procedure_name}")
                return

            # Fallback to processor
            procedure = getattr(self.processor, procedure_name)
            procedure()
            logger.debug(f"Executed processor procedure: {procedure_name}")

        except Exception as e:
            logger.error(f"❌ Error executing procedure {procedure_name}: {e}")
            raise

    def fill_table(self, table_name: str, rows: List[Dict[str, Any]]):
        """Fill tabular section with rows."""
        try:
            # Try form.Объект first
            if self.form:
                obj = getattr(self.form, "Объект", None)
                if obj:
                    table = getattr(obj, table_name)
                    table.Очистить()

                    for row_data in rows:
                        row = table.Добавить()
                        for column, value in row_data.items():
                            setattr(row, column, value)

                    logger.debug(f"Filled {table_name}: {len(rows)} rows (via form)")
                    return

            # Fallback to processor.Объект
            obj = getattr(self.processor, "Объект", self.processor)
            table = getattr(obj, table_name)
            table.Очистить()

            for row_data in rows:
                row = table.Добавить()
                for column, value in row_data.items():
                    setattr(row, column, value)

            logger.debug(f"Filled {table_name}: {len(rows)} rows")

        except Exception as e:
            logger.error(f"❌ Error filling table {table_name}: {e}")
            raise

    def start_message_recording(self):
        """
        Start message recording through form.

        Automation Server can capture messages through form.НачатьЗаписьСообщений().
        """
        try:
            if self.form and hasattr(self.form, "НачатьЗаписьСообщений"):
                self.form.НачатьЗаписьСообщений()
                logger.debug("Message recording started (via form)")
                return

            # Fallback to processor (if method exists)
            if hasattr(self.processor, "НачатьЗаписьСообщений"):
                self.processor.НачатьЗаписьСообщений()
                logger.debug("Message recording started (via processor)")
                return

            logger.warning("⚠️  Method НачатьЗаписьСообщений not found")

        except Exception as e:
            logger.error(f"❌ Error starting message recording: {e}")

    def get_test_messages(self) -> List[str]:
        """
        Get recorded messages through form.

        Automation Server can get messages through form.ПолучитьТестовыеСообщения().

        Returns:
            List of message strings
        """
        try:
            # Try form first
            if self.form and hasattr(self.form, "ПолучитьТестовыеСообщения"):
                messages_array = self.form.ПолучитьТестовыеСообщения()

                # Convert 1C array to Python list
                messages = []
                for i in range(messages_array.Количество()):
                    messages.append(str(messages_array.Получить(i)))

                return messages

            # Fallback to processor
            if hasattr(self.processor, "ПолучитьТестовыеСообщения"):
                messages_array = self.processor.ПолучитьТестовыеСообщения()

                messages = []
                for i in range(messages_array.Количество()):
                    messages.append(str(messages_array.Получить(i)))

                return messages

            logger.warning("⚠️  Method ПолучитьТестовыеСообщения not found")
            return []

        except Exception as e:
            logger.error(f"❌ Error getting messages: {e}")
            return []

    # Additional UI interaction methods (Phase 2 specific)

    def get_form(self, form_name: str = "Форма"):
        """
        Get processor form.

        Args:
            form_name: Form name (default: "Форма")

        Returns:
            Form COM object
        """
        try:
            self.form = self.processor.ПолучитьФорму(form_name)
            logger.debug(f"Form '{form_name}' obtained")
            return self.form
        except Exception as e:
            logger.error(f"❌ Error getting form '{form_name}': {e}")
            raise

    def click_button(self, button_name: str):
        """
        Click button on form (simulates user clicking button).

        Args:
            button_name: Button element name or command name
        """
        if not self.form:
            raise RuntimeError("Form not loaded. Call get_form() first or use load_from_configuration=True")

        try:
            # Try to find and execute command
            # Method 1: Direct command handler
            if hasattr(self.form, button_name):
                handler = getattr(self.form, button_name)
                handler()
                logger.debug(f"Button '{button_name}' clicked (direct handler)")
                return

            # Method 2: Server handler
            server_handler = f"{button_name}НаСервере"
            if hasattr(self.form, server_handler):
                handler = getattr(self.form, server_handler)
                handler()
                logger.debug(f"Button '{button_name}' clicked (server handler)")
                return

            logger.error(f"❌ Button handler '{button_name}' not found on form")
            raise AttributeError(f"Button handler '{button_name}' not found")

        except Exception as e:
            logger.error(f"❌ Error clicking button '{button_name}': {e}")
            raise

    def set_field_value(self, field_name: str, value: Any):
        """
        Set form field value (through form.Elements).

        Args:
            field_name: Field element name
            value: Value to set
        """
        if not self.form:
            # Fallback to attribute
            self.set_attribute(field_name, value)
            return

        try:
            # Try form.Elements first
            if hasattr(self.form, "Elements"):
                element = getattr(self.form.Elements, field_name, None)
                if element:
                    element.Value = value
                    logger.debug(f"Field '{field_name}' set to {value} (via Elements)")
                    return

            # Fallback to form.Объект
            obj = getattr(self.form, "Объект", None)
            if obj:
                setattr(obj, field_name, value)
                logger.debug(f"Field '{field_name}' set to {value} (via Объект)")
                return

            logger.warning(f"⚠️  Field '{field_name}' not found, using set_attribute")
            self.set_attribute(field_name, value)

        except Exception as e:
            logger.error(f"❌ Error setting field '{field_name}': {e}")
            raise

    def get_field_value(self, field_name: str) -> Any:
        """
        Get form field value (through form.Elements).

        Args:
            field_name: Field element name

        Returns:
            Field value
        """
        if not self.form:
            # Fallback to attribute
            return self.get_attribute(field_name)

        try:
            # Try form.Elements first
            if hasattr(self.form, "Elements"):
                element = getattr(self.form.Elements, field_name, None)
                if element:
                    return element.Value

            # Fallback to form.Объект
            obj = getattr(self.form, "Объект", None)
            if obj:
                return getattr(obj, field_name)

            logger.warning(f"⚠️  Field '{field_name}' not found, using get_attribute")
            return self.get_attribute(field_name)

        except Exception as e:
            logger.error(f"❌ Error getting field '{field_name}': {e}")
            raise

    def get_table_element(self, table_name: str):
        """
        Get table form element (for UI interaction).

        Args:
            table_name: Table element name

        Returns:
            Table form element
        """
        if not self.form:
            raise RuntimeError("Form not loaded. Call get_form() first")

        try:
            if hasattr(self.form, "Elements"):
                return getattr(self.form.Elements, table_name)
            raise AttributeError(f"Form.Elements.{table_name} not found")
        except Exception as e:
            logger.error(f"❌ Error getting table element '{table_name}': {e}")
            raise
