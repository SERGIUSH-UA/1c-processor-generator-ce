"""
Константи для генерації зовнішніх обробок 1C

Re-exports core constants from _protected module.
"""

from ._protected import (
    # Class IDs - critical for EPF recognition
    CLASS_ID_EXTERNAL_DATA_PROCESSOR,
    CLASS_ID_EXTERNAL_REPORT,
    # Functions to get protected constants
    get_xml_namespaces,
    get_form_xml_namespaces,
    get_type_mapping,
    get_element_suffixes,
    get_class_id,
    # v2.54.0+ Element rendering functions
    get_element_submenu_xml,
    get_data_path_xml,
    get_table_data_path_xml,
    get_line_number_data_path_xml,
    get_element_id_increment,
    get_element_structure,
    get_embedded_template,
    has_embedded_templates,
    is_bsp_pro_feature,
)

# Re-export namespaces for backward compatibility
# These call protected functions internally
XML_NAMESPACES = get_xml_namespaces()
FORM_XML_NAMESPACES = get_form_xml_namespaces()
TYPE_MAPPING = get_type_mapping()
ELEMENT_SUFFIXES = get_element_suffixes()

# ID елементів форми
AUTO_COMMAND_BAR_ID = -1  # Завжди -1

# ELEMENT_ID_INCREMENTS - imported from pro/generation_context module
# ELEMENT_SUFFIXES - imported from _protected module (see above)

# Версії платформи 1C
# ВАЖЛИВО: Генератор підтримує будь-яку версію формату XML (pattern: \d+\.\d+)
# Цей словник для довідки - показує відповідність версій платформи та формату XML
PLATFORM_VERSIONS = {
    "8.3.23": "2.10",  # Старіші версії платформи
    "8.3.24": "2.10",
    "8.3.25": "2.11",  # Стандартна версія (за замовчуванням)
    "8.3.26": "2.18",  # Нові версії платформи
    "8.3.27": "2.18",
    # Генератор приймає будь-яку версію (2.10, 2.11, 2.15, 2.18, 2.19, тощо)
    # Використовуйте ту версію, яку підтримує ваша платформа 1C
}

# v2.64.1: Fallback CompatibilityMode для Configuration.xml
# Використовується коли не вдається визначити версію встановленої платформи
# Формат: Version{Major}_{Minor}_{Patch} (наприклад Version8_3_15)
DEFAULT_COMPATIBILITY_MODE = "Version8_3_15"

# v2.64.3: Fallback XML format version - MUST match DEFAULT_COMPATIBILITY_MODE!
# Version8_3_15 → XML format 2.9
# Mapping: 8.3.15→2.9, 8.3.18→2.11, 8.3.19→2.12, 8.3.25→2.18
DEFAULT_XML_FORMAT_VERSION = "2.9"

# Кодування файлів
ENCODING_UTF8_BOM = "utf-8-sig"  # UTF-8 з BOM для BSL файлів

# Шаблон для порожнього BSL файлу
EMPTY_BSL_TEMPLATE = "//ПУСТО"

# Шаблон для BSL модуля об'єкта
OBJECT_MODULE_TEMPLATE = """
#Область ПрограммныйИнтерфейс

// Публичные функции

#КонецОбласти

#Область СлужебныеПроцедурыИФункции

// Вспомогательные функции

#КонецОбласти
""".strip()

# Шаблон для BSL модуля форми
FORM_MODULE_TEMPLATE = """
#Область ОбработчикиСобытийФормы

// Обработчики событий формы

#КонецОбласти

#Область ОбработчикиСобытийЭлементовШапкиФормы

// Обработчики событий элементов формы

#КонецОбласти

#Область ОбработчикиКомандФормы

// Обработчики команд формы

#КонецОбласти

#Область СлужебныеПроцедурыИФункции

// Вспомогательные функции

#КонецОбласти
""".strip()

# Назва форми за замовчуванням
DEFAULT_FORM_NAME = "Форма"

# Мови
LANGUAGES = ["ru", "uk", "en"]
DEFAULT_LANGUAGE = "ru"

# Допустимі StdPicture для використання в командах і елементах форми
VALID_STD_PICTURES = {
    "StdPicture.AccumulationRegister",
    "StdPicture.ActiveUsers",
    "StdPicture.AddToFavorites",
    "StdPicture.AppearanceExclamationMarkIcon",
    "StdPicture.Attach",
    "StdPicture.Attribute",
    "StdPicture.Back",
    "StdPicture.BusinessProcessStart",
    "StdPicture.CancelSearch",
    "StdPicture.Catalog",
    "StdPicture.Change",
    "StdPicture.ChangeListItem",
    "StdPicture.CheckAll",
    "StdPicture.CheckSyntax",
    "StdPicture.ChooseValue",
    "StdPicture.ClearFilter",
    "StdPicture.CloneListItem",
    "StdPicture.CloneObject",
    "StdPicture.Close",
    "StdPicture.CollaborationSystemUser",
    "StdPicture.CollapseAll",
    "StdPicture.CreateFolder",
    "StdPicture.CreateInitialImage",
    "StdPicture.CreateListItem",
    "StdPicture.CustomizeForm",
    "StdPicture.CustomizeList",
    "StdPicture.DataCompositionConditionalAppearance",
    "StdPicture.DataCompositionDataParameters",
    "StdPicture.DataCompositionFilter",
    "StdPicture.DataCompositionGroupFields",
    "StdPicture.DataCompositionNewChart",
    "StdPicture.DataCompositionNewGroup",
    "StdPicture.DataCompositionNewNestedScheme",
    "StdPicture.DataCompositionNewTable",
    "StdPicture.DataCompositionOrder",
    "StdPicture.DataCompositionOutputParameters",
    "StdPicture.DataCompositionSelection",
    "StdPicture.DataCompositionSettingsWizard",
    "StdPicture.DataCompositionStandardSettings",
    "StdPicture.DataCompositionUserFields",
    "StdPicture.DataHistory",
    "StdPicture.DebitCredit",
    "StdPicture.Delete",
    "StdPicture.DeleteDirectly",
    "StdPicture.Document",
    "StdPicture.DocumentJournal",
    "StdPicture.EndEdit",
    "StdPicture.EventLog",
    "StdPicture.EventLogByUser",
    "StdPicture.ExchangePlan",
    "StdPicture.ExecuteTask",
    "StdPicture.ExpandAll",
    "StdPicture.ExternalDataSourceTable",
    "StdPicture.FilterByCurrentValue",
    "StdPicture.FilterCriterion",
    "StdPicture.Find",
    "StdPicture.FindInList",
    "StdPicture.FindNext",
    "StdPicture.FindPrevious",
    "StdPicture.Form",
    "StdPicture.FormHelp",
    "StdPicture.Forward",
    "StdPicture.GenerateReport",
    "StdPicture.GetURL",
    "StdPicture.GoBack",
    "StdPicture.GroupConversation",
    "StdPicture.Information",
    "StdPicture.InformationRegister",
    "StdPicture.InputFieldCalculator",
    "StdPicture.InputFieldCalendar",
    "StdPicture.InputFieldChooseType",
    "StdPicture.InputFieldClear",
    "StdPicture.InputFieldOpen",
    "StdPicture.InputFieldSelect",
    "StdPicture.InputOnBasis",
    "StdPicture.ListSettings",
    "StdPicture.ListViewMode",
    "StdPicture.ListViewModeHierarchicalList",
    "StdPicture.ListViewModeList",
    "StdPicture.ListViewModeTree",
    "StdPicture.LoadReportSettings",
    "StdPicture.MarkToDelete",
    "StdPicture.MoveDown",
    "StdPicture.MoveItem",
    "StdPicture.MoveLeft",
    "StdPicture.MoveRight",
    "StdPicture.MoveUp",
    "StdPicture.Notifications",
    "StdPicture.OpenFile",
    "StdPicture.Picture",
    "StdPicture.Post",
    "StdPicture.Print",
    "StdPicture.PrintImmediately",
    "StdPicture.Properties",
    "StdPicture.QueryWizard",
    "StdPicture.QueryWizardCreateTempTableDropQuery",
    "StdPicture.ReadChanges",
    "StdPicture.Refresh",
    "StdPicture.Replace",
    "StdPicture.Report",
    "StdPicture.ReportSettings",
    "StdPicture.Reread",
    "StdPicture.RestoreValues",
    "StdPicture.SaveFile",
    "StdPicture.SaveReportSettings",
    "StdPicture.SaveValues",
    "StdPicture.ScheduledJob",
    "StdPicture.ScheduledJobs",
    "StdPicture.SelectAll",
    "StdPicture.SetDateInterval",
    "StdPicture.SetListItemDeletionMark",
    "StdPicture.SetTime",
    "StdPicture.SettingsStorage",
    "StdPicture.ShowData",
    "StdPicture.ShowInList",
    "StdPicture.SortListAsc",
    "StdPicture.SortListDesc",
    "StdPicture.SpreadsheetReadOnly",
    "StdPicture.Stop",
    "StdPicture.SyncContents",
    "StdPicture.UncheckAll",
    "StdPicture.UndoPosting",
    "StdPicture.UnselectAll",
    "StdPicture.User",
    "StdPicture.UserWithAuthentication",
    "StdPicture.UserWithoutNecessaryProperties",
    "StdPicture.Write",
    "StdPicture.WriteAndClose",
    "StdPicture.WriteChanges",
}

# Зарезервовані ключові слова BSL (не можуть бути іменами процедур/функцій)
# Джерело: офіційна документація 1C:Enterprise 8.3
BSL_RESERVED_KEYWORDS = {
    # Структура процедур і функцій
    "Процедура", "Функция", "КонецПроцедуры", "КонецФункции",
    "Procedure", "Function", "EndProcedure", "EndFunction",

    # Умовні оператори
    "Если", "Тогда", "Иначе", "ИначеЕсли", "КонецЕсли",
    "If", "Then", "Else", "ElsIf", "EndIf",

    # Цикли
    "Для", "Каждого", "Из", "По", "Цикл", "КонецЦикла",
    "Пока",
    "For", "Each", "In", "To", "Do", "While", "EndDo",

    # Обробка винятків
    "Попытка", "Исключение", "КонецПопытки", "ВызватьИсключение",
    "Try", "Except", "EndTry", "Raise",

    # Керування виконанням
    "Прервать", "Продолжить", "Возврат",
    "Break", "Continue", "Return",

    # Константи і типи
    "Новый", "Неопределено", "Истина", "Ложь", "NULL",
    "New", "Undefined", "True", "False",

    # Модифікатори
    "Экспорт", "Знач", "Перем",
    "Export", "Val", "Var",

    # Логічні оператори
    "И", "Или", "Не",
    "And", "Or", "Not",

    # КРИТИЧНО ВАЖЛИВІ: системні функції які НЕ можна перевизначати
    "Выполнить",   # Execute() - динамічне виконання коду
    "Вычислить",   # Eval() - обчислення виразів
    "Execute",
    "Eval",

    # Інші системні слова
    "Перейти", "Goto",

    # Вбудовані глобальні функції які часто плутають з іменами процедур
    "Найти", "Find",             # СтрНайти/Find - пошук підрядка
}

# Вбудовані методи форми 1C, які НЕ можна перевизначати в обробниках
# Ці методи автоматично доступні у всіх керованих формах
FORM_BUILTIN_METHODS = {
    # Методи керування формою
    "Закрыть", "Close",                    # Закрити форму
    "Открыть", "Open",                     # Відкрити форму
    "ОткрытьМодально", "OpenModal",        # Відкрити модально
    "Модифицированность", "Modified",      # Перевірка зміни даних
    "ПолучитьФорму", "GetForm",            # Отримати форму
    "Активизировать", "Activate",          # Активувати форму
    "ОбновитьОтображениеДанных", "RefreshDataRepresentation",  # Оновити відображення
    "ПоказатьЗначение", "ShowValue",       # Показати значення
    "ПоказатьВводЧисла", "ShowInputNumber", # Показати введення числа
    "ПоказатьВводДаты", "ShowInputDate",   # Показати введення дати
    "ПоказатьВводСтроки", "ShowInputString", # Показати введення рядка
    "УстановитьВидимость", "SetVisible",   # Встановити видимість
    "УстановитьДоступность", "SetEnabled", # Встановити доступність
}

# Стандартні команди форм 1C (v2.15.1+)
# Ці команди НЕ можна визначати як custom команди - вони вбудовані в платформу
# Використання: Form.StandardCommand.Close (а не Form.Command.Close)
STANDARD_FORM_COMMANDS = {
    "Close",     # Закрити форму
    "Cancel",    # Скасувати
    "Help",      # Довідка
    "OK",        # OK
    # Додаткові стандартні команди можна додати за потреби
}

# ============================================================================
# SHORTCUT VALIDATION (v2.72.0+)
# ============================================================================

# Valid function keys
VALID_FUNCTION_KEYS = {f"F{i}" for i in range(1, 13)}  # F1-F12

# Valid special keys (without modifiers)
VALID_SPECIAL_KEYS = {
    "Insert", "Delete", "Escape", "Home", "End",
    "PageUp", "PageDown", "Tab", "Enter", "Backspace",
    "Up", "Down", "Left", "Right", "Space",
}

# Valid modifiers
VALID_MODIFIERS = {"Ctrl", "Alt", "Shift"}

# All valid key names (for combination shortcuts)
VALID_KEY_NAMES = (
    VALID_FUNCTION_KEYS |
    VALID_SPECIAL_KEYS |
    set("ABCDEFGHIJKLMNOPQRSTUVWXYZ") |
    set("0123456789")
)

# ============================================================================
# BSP Integration Constants (v2.57.0+) - PRO Feature
# ============================================================================
# PROTECTED: Основні BSP константи та шаблони знаходяться в pro/bsp_generator_impl.py
# Цей модуль компілюється в .pyd для захисту
#
# PRO/FREE flag is in _protected.py, use is_bsp_pro_feature() function
# is_bsp_pro_feature - imported from _protected (see imports above)
