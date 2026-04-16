"""
Generation context provider for 1C Processor Generator.

Contains critical constants for XML/BSL generation:
- Element ID increments
- Form and element event signatures
- BSL code templates

SPDX-License-Identifier: GPL-3.0-or-later
Copyright (c) 2024-2025 ITDEO
This file is part of 1C Processor Generator Community Edition.
"""

from typing import Dict, Optional
import random
import hashlib

try:
    pass  # No external imports needed in community edition
except ImportError:
    pass


# ============================================================================
# ELEMENT ID INCREMENTS
# Each element type uses specific number of ID slots
# ============================================================================

_ELEMENT_ID_INCREMENTS: Dict[str, int] = {
    "InputField": 3,        # Element + ContextMenu + ExtendedTooltip
    "LabelField": 3,        # Element + ContextMenu + ExtendedTooltip
    "LabelDecoration": 3,   # Element + ContextMenu + ExtendedTooltip
    "PictureDecoration": 3, # Element + ContextMenu + ExtendedTooltip
    "PictureField": 3,      # Element + ContextMenu + ExtendedTooltip
    "RadioButtonField": 3,  # Element + ContextMenu + ExtendedTooltip
    "CheckBoxField": 3,     # Element + ContextMenu + ExtendedTooltip
    "SpreadSheetDocumentField": 3,  # Element + ContextMenu + ExtendedTooltip
    "HTMLDocumentField": 3,  # Element + ContextMenu + ExtendedTooltip
    "CalendarField": 3,     # Element + ContextMenu + ExtendedTooltip
    "ChartField": 3,        # Element + ContextMenu + ExtendedTooltip
    "PlannerField": 3,      # Element + ContextMenu + ExtendedTooltip
    "Button": 2,            # Element + ExtendedTooltip
    "ButtonGroup": 2,       # Element + ExtendedTooltip
    "ColumnGroup": 2,       # Element + ExtendedTooltip
    "Popup": 2,             # Element + ExtendedTooltip
    "UsualGroup": 2,        # Element + ExtendedTooltip
    "Pages": 2,             # Element + ExtendedTooltip
    "Page": 2,              # Element + ExtendedTooltip
    "Table": 4,             # Element + ContextMenu + CommandBar + ExtendedTooltip
    "TableColumn": 3,       # Column + ContextMenu + ExtendedTooltip
}

# ============================================================================
# FORM EVENT SIGNATURES
# Parameters and directives for form events
# ============================================================================

_FORM_EVENT_SIGNATURES: Dict[str, Dict[str, str]] = {
    "OnCreateAtServer": {
        "handler": "ПриСозданииНаСервере",
        "directive": "НаСервере",
        "params": "Отказ, СтандартнаяОбработка",
    },
    "OnOpen": {
        "handler": "ПриОткрытии",
        "directive": "НаКлиенте",
        "params": "Отказ",
        "server_call": "ПриОткрытииНаСервере",
    },
    "OnClose": {
        "handler": "ПриЗакрытии",
        "directive": "НаКлиенте",
        "params": "ЗавершениеРаботы",
    },
    "BeforeClose": {
        "handler": "ПередЗакрытием",
        "directive": "НаКлиенте",
        "params": "Отказ, ЗавершениеРаботы, ТекстПредупреждения, СтандартнаяОбработка",
    },
}

# ============================================================================
# ELEMENT EVENT SIGNATURES
# Parameters and directives for element events
# ============================================================================

_ELEMENT_EVENT_SIGNATURES: Dict[str, Dict[str, str]] = {
    "OnChange": {
        "handler": "ПриИзменении",
        "directive": "НаКлиенте",
        "params": "Элемент",
        "server_call_suffix": "НаСервере",
    },
    "Click": {
        "handler": "Нажатие",
        "directive": "НаКлиенте",
        "params": "Элемент",
    },
    "StartChoice": {
        "handler": "НачалоВыбора",
        "directive": "НаКлиенте",
        "params": "Элемент, ДанныеВыбора, СтандартнаяОбработка",
    },
    "ChoiceProcessing": {
        "handler": "ОбработкаВыбора",
        "directive": "НаКлиенте",
        "params": "Элемент, ВыбранноеЗначение, СтандартнаяОбработка",
    },
    "Clearing": {
        "handler": "Очистка",
        "directive": "НаКлиенте",
        "params": "Элемент, СтандартнаяОбработка",
    },
    "OnActivateRow": {
        "handler": "ПриАктивизацииСтроки",
        "directive": "НаКлиенте",
        "params": "Элемент",
        "server_call_suffix": "НаСервере",
    },
    "Selection": {
        "handler": "Выбор",
        "directive": "НаКлиенте",
        "params": "Элемент, ВыбраннаяСтрока, Поле, СтандартнаяОбработка",
    },
    "OnStartEdit": {
        "handler": "ПриНачалеРедактирования",
        "directive": "НаКлиенте",
        "params": "Элемент, НоваяСтрока, Копирование",
    },
    "BeforeAddRow": {
        "handler": "ПередДобавлениемСтроки",
        "directive": "НаКлиенте",
        "params": "Элемент, Отказ, Копирование, Родитель, Группа",
    },
    "BeforeDeleteRow": {
        "handler": "ПередУдалениемСтроки",
        "directive": "НаКлиенте",
        "params": "Элемент, Отказ",
    },
    "BeforeRowChange": {
        "handler": "ПередИзменениемСтроки",
        "directive": "НаКлиенте",
        "params": "Элемент, Отказ",
    },
    "DetailProcessing": {
        "handler": "ОбработкаРасшифровки",
        "directive": "НаКлиенте",
        "params": "Элемент, Расшифровка, СтандартнаяОбработка",
    },
    "OnClick": {
        "handler": "ПриНажатии",
        "directive": "НаКлиенте",
        "params": "Элемент, ДанныеСобытия, СтандартнаяОбработка",
    },
    "OnActivateDate": {
        "handler": "ПриАктивизацииДаты",
        "directive": "НаКлиенте",
        "params": "Элемент",
    },
    "ChartSelection": {
        "handler": "ВыборДиаграммы",
        "directive": "НаКлиенте",
        "params": "Элемент, ТочкаСерии, СерияДиаграммы, СтандартнаяОбработка",
    },
    "Drag": {
        "handler": "Перетаскивание",
        "directive": "НаКлиенте",
        "params": "Элемент, ПараметрыПеретаскивания, СтандартнаяОбработка",
    },
    "DragCheck": {
        "handler": "ПроверкаПеретаскивания",
        "directive": "НаКлиенте",
        "params": "Элемент, ПараметрыПеретаскивания, СтандартнаяОбработка",
    },
    "BeforeCreate": {
        "handler": "ПередСозданием",
        "directive": "НаКлиенте",
        "params": "Элемент, НовыйЭлемент, Копирование, СтандартнаяОбработка",
    },
    "OnEditEnd": {
        "handler": "ПриОкончанииРедактирования",
        "directive": "НаКлиенте",
        "params": "Элемент, НоваяСтрока, ОтменаРедактирования",
    },
    # v2.65.0: Подія динамічного списку для оформлення рядків (8.3.10+)
    "OnGetDataAtServer": {
        "handler": "ПриПолученииДанныхНаСервере",
        "directive": "НаСервереБезКонтекста",
        "params": "ИмяЭлемента, Настройки, Строки",
        # Немає server_call_suffix - це вже серверна подія без контексту
    },
}

# ============================================================================
# BSL TEMPLATES
# Code generation templates for handlers
# ============================================================================

_EVENT_HANDLER_TEMPLATE: str = """
&{directive}
Процедура {handler_name}({params})
\t{body}
КонецПроцедуры
""".strip()

_SERVER_CALL_TEMPLATE: str = """
&НаКлиенте
Процедура {client_handler}({params})
\t{server_handler}();
КонецПроцедуры
""".strip()

_SERVER_PROCEDURE_TEMPLATE: str = """
&НаСервере
Процедура {server_handler}()
\t// Вставить содержимое обработчика.
КонецПроцедуры
""".strip()

# ============================================================================
# LONG OPERATION TEMPLATES
# Background jobs / long operations templates
# ============================================================================

_LONG_OPERATION_CLIENT_BUTTON_TEMPLATE: str = """
&НаКлиенте
Процедура {command_name}Кнопка(Команда)
\t{validation_call}РезультатДлОперации = {command_name}ЗапуститьВФоне();
\t
\tПараметрыОжидания = ДлительныеОперацииКлиент.ПараметрыОжидания(ЭтотОбъект);
\t{waiting_params_code}
\t
\tОбработчик = Новый ОписаниеОповещения("{command_name}Завершение", ЭтотОбъект);
\tДлительныеОперацииКлиент.ОжидатьЗавершение(РезультатДлОперации, Обработчик, ПараметрыОжидания);
КонецПроцедуры
""".strip()

_LONG_OPERATION_SERVER_START_TEMPLATE: str = """
&НаСервере
Функция {command_name}ЗапуститьВФоне()
\t
\t// Подготовка параметров для фонового задания
\tПараметрыЗадания = Новый Структура;
\t{parameters_code}
\t
\t// Настройка параметров выполнения
\tПараметрыВыполнения = ДлительныеОперации.ПараметрыВыполненияВФоне(УникальныйИдентификатор);
\tПараметрыВыполнения.НаименованиеФоновогоЗадания = "{job_title}";
\tПараметрыВыполнения.ЗапуститьВФоне = Истина;
\t{wait_initial_code}
\t
\t// Запуск фонового задания
\tВозврат ДлительныеОперации.ВыполнитьВФоне(
\t\t"Обработки.{processor_name}.{command_name}НаСервере",
\t\tПараметрыЗадания,
\t\tПараметрыВыполнения
\t);
\t
КонецФункции
""".strip()

_LONG_OPERATION_CLIENT_COMPLETION_TEMPLATE: str = """
&НаКлиенте
Процедура {command_name}Завершение(Результат, ДополнительныеПараметры) Экспорт
\t
\t// Проверка отмены операции
\tЕсли Результат = Неопределено Тогда
\t\tСообщить("Операция отменена пользователем");
\t\tВозврат;
\tКонецЕсли;
\t
\t// Проверка ошибок
\tЕсли Результат.Статус = "Ошибка" Тогда
\t\tПоказатьПредупреждение(, Результат.КраткоеПредставлениеОшибки);
\t\tВозврат;
\tКонецЕсли;
\t
\tСообщить("Операция успешно завершена!");
\t
КонецПроцедуры
""".strip()


# ============================================================================
# GENERATION CONTEXT FUNCTION
# This is the main entry point - watermark is integrated here
# ============================================================================

_cached_context: Optional[Dict] = None


def get_generation_context() -> Dict:
    """
    Get generation context with all critical constants.

    Returns dict with element_id_increments, event signatures,
    BSL templates, and generation metadata.
    """
    global _cached_context

    if _cached_context is not None:
        return _cached_context

    _cached_context = {
        # ID increments
        "element_id_increments": _ELEMENT_ID_INCREMENTS,
        # Event signatures
        "form_event_signatures": _FORM_EVENT_SIGNATURES,
        "element_event_signatures": _ELEMENT_EVENT_SIGNATURES,
        # BSL templates
        "event_handler_template": _EVENT_HANDLER_TEMPLATE,
        "server_call_template": _SERVER_CALL_TEMPLATE,
        "server_procedure_template": _SERVER_PROCEDURE_TEMPLATE,
        # Long operation templates
        "long_operation_client_button_template": _LONG_OPERATION_CLIENT_BUTTON_TEMPLATE,
        "long_operation_server_start_template": _LONG_OPERATION_SERVER_START_TEMPLATE,
        "long_operation_client_completion_template": _LONG_OPERATION_CLIENT_COMPLETION_TEMPLATE,
        # Community edition: no watermark
        "module_preamble": "",
        "is_pro": True,
        "purchase_url": "",
    }

    return _cached_context

def clear_context_cache() -> None:
    """Clear cached context (useful for testing)."""
    global _cached_context
    _cached_context = None


def print_generation_status() -> None:
    """Print generation status."""
    print("   [Community Edition] Generation without watermark")


# ============================================================================
# HELPER FUNCTIONS
# These provide convenient access to specific constants
# ============================================================================

def get_element_increment(element_type: str, default: int = 3) -> int:
    """Get ID increment for element type."""
    ctx = get_generation_context()
    return ctx["element_id_increments"].get(element_type, default)


def get_form_event_signature(event: str) -> Optional[Dict[str, str]]:
    """Get signature for form event."""
    ctx = get_generation_context()
    return ctx["form_event_signatures"].get(event)


def get_element_event_signature(event: str) -> Optional[Dict[str, str]]:
    """Get signature for element event."""
    ctx = get_generation_context()
    return ctx["element_event_signatures"].get(event)


def get_module_preamble() -> str:
    """Always empty in community edition."""
    return ""


# ============================================================================
# MODULE FINALIZATION
# ============================================================================


def _count_procedures(module_code: str) -> int:
    """Count procedures/functions in module for ID calculation."""
    import re
    # Count procedure/function declarations
    proc_pattern = r'(?:Процедура|Функция|Procedure|Function)\s+\w+'
    return len(re.findall(proc_pattern, module_code, re.IGNORECASE))


def _count_regions(module_code: str) -> int:
    """Count regions in module."""
    import re
    return len(re.findall(r'#(?:Область|Region)\s+', module_code, re.IGNORECASE))


def _calculate_module_id_offset(module_code: str) -> int:
    """
    Calculate ID offset based on module content.

    This is CRITICAL for XML generation - each procedure/region affects ID allocation.
    Without correct offset, form XML will have wrong IDs = broken EPF.
    """
    base_offset = 1  # Module itself

    # Each procedure adds to offset (for potential event handlers)
    proc_count = _count_procedures(module_code)
    base_offset += proc_count * 2  # Each proc may have client+server pair

    # Each region adds small offset
    region_count = _count_regions(module_code)
    base_offset += region_count

    return base_offset


def _generate_validation_token(code: str, offset: int, seed: str) -> str:
    """
    Generate validation token for XML generation.

    This token is checked during XML generation - without it, generator fails.
    """
    import hashlib

    # Create deterministic token from code characteristics
    token_data = f"{len(code)}:{offset}:{seed}:1cpg"
    return hashlib.md5(token_data.encode()).hexdigest()[:16]


def finalize_module(
    module_code: str,
    seed: str,
    current_element_id: int,
    module_type: str = "form"
) -> dict:
    """
    Finalize module code and return critical generation data.

    Calculates next element ID offset (critical for XML generation)
    and returns validation token.

    Args:
        module_code: Raw BSL module code
        seed: Seed for reproducible generation
        current_element_id: Current element ID counter
        module_type: "form" or "object"

    Returns:
        dict with code, next_element_id, id_offset, validation_token, watermark_style
    """
    # Calculate ID offset (critical for XML)
    id_offset = _calculate_module_id_offset(module_code)

    if module_type == "object":
        id_offset += 3

    next_element_id = current_element_id + id_offset

    # Generate validation token
    token = _generate_validation_token(module_code, id_offset, seed)

    return {
        "code": module_code,  # No watermark in community edition
        "next_element_id": next_element_id,
        "id_offset": id_offset,
        "validation_token": token,
        "watermark_style": -1,
    }
