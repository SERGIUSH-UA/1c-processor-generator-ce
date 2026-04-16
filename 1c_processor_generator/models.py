"""
Моделі даних для опису зовнішніх обробок 1C
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from uuid import uuid4


def generate_uuid() -> str:
    """Генерує валідний UUID для 1C (lowercase)"""
    return str(uuid4()).lower()


@dataclass
class Column:
    """Колонка табличної частини"""
    name: str
    type: str
    synonym_ru: Optional[str] = None
    synonym_uk: Optional[str] = None
    synonym_en: Optional[str] = None
    length: Optional[int] = None  # Для string
    digits: Optional[int] = None  # Для number
    fraction_digits: Optional[int] = None  # Для number
    read_only: bool = False  # Колонка тільки для перегляду
    uuid: str = field(default_factory=generate_uuid)

    def __post_init__(self):
        if not self.synonym_ru:
            self.synonym_ru = self.name
        if not self.synonym_uk:
            self.synonym_uk = self.name
        if not self.synonym_en:
            self.synonym_en = self.name


@dataclass
class TabularSection:
    """Таблична частина обробки"""
    name: str
    synonym_ru: Optional[str] = None
    synonym_uk: Optional[str] = None
    synonym_en: Optional[str] = None
    columns: List[Column] = field(default_factory=list)
    uuid: str = field(default_factory=generate_uuid)
    type_id: str = field(default_factory=generate_uuid)
    value_id: str = field(default_factory=generate_uuid)
    row_type_id: str = field(default_factory=generate_uuid)
    row_value_id: str = field(default_factory=generate_uuid)

    def __post_init__(self):
        if not self.synonym_ru:
            self.synonym_ru = self.name
        if not self.synonym_uk:
            self.synonym_uk = self.name
        if not self.synonym_en:
            self.synonym_en = self.name


@dataclass
class Attribute:
    """Реквізит обробки"""
    name: str
    type: str
    synonym_ru: Optional[str] = None
    synonym_uk: Optional[str] = None
    synonym_en: Optional[str] = None
    length: Optional[int] = None  # Для string
    digits: Optional[int] = None  # Для number
    fraction_digits: Optional[int] = None  # Для number
    uuid: str = field(default_factory=generate_uuid)

    def __post_init__(self):
        if not self.synonym_ru:
            self.synonym_ru = self.name
        if not self.synonym_uk:
            self.synonym_uk = self.name
        if not self.synonym_en:
            self.synonym_en = self.name


# ===== ConditionalAppearance Support (v2.67.0+) =====


@dataclass
class AppearanceStyle:
    """Style settings for ConditionalAppearance.

    Підтримує налаштування зовнішнього вигляду для умовного оформлення:
    - back_color: колір фону (hex #RRGGBB)
    - text_color: колір тексту (hex #RRGGBB)
    - font_bold: жирний шрифт
    - font_italic: курсив
    - visible: видимість елемента
    - enabled: доступність елемента

    v2.67.0+

    Example:
        >>> style = AppearanceStyle(
        ...     back_color="#FFFF00",
        ...     text_color="#000000",
        ...     font_bold=True
        ... )
    """
    back_color: Optional[str] = None      # #RRGGBB
    text_color: Optional[str] = None      # #RRGGBB
    font_bold: Optional[bool] = None
    font_italic: Optional[bool] = None
    visible: Optional[bool] = None
    enabled: Optional[bool] = None


@dataclass
class ConditionalFilter:
    """Filter condition for ConditionalAppearance.

    Визначає умову застосування стилю:
    - field: шлях до поля даних (напр. "IsWhite" або "Объект.Status")
    - comparison: тип порівняння (Equal, NotEqual)
    - value: значення для порівняння
    - value_type: тип значення (string, boolean, number)

    v2.67.0+

    Example:
        >>> filter = ConditionalFilter(
        ...     field="IsWhite",
        ...     comparison="Equal",
        ...     value=True,
        ...     value_type="boolean"
        ... )
    """
    field: str                           # Data path
    comparison: str = "Equal"            # Equal, NotEqual
    value: Any = None                    # Comparison value
    value_type: str = "string"           # string, boolean, number


@dataclass
class ConditionalAppearanceItem:
    """Single conditional appearance rule.

    Правило умовного оформлення, що поєднує:
    - name: ім'я правила (для документації)
    - selection: список полів для стилізації
    - filter: умова застосування
    - appearance: налаштування стилю

    v2.67.0+

    Example:
        >>> item = ConditionalAppearanceItem(
        ...     name="WhiteCells",
        ...     selection=["Piece"],
        ...     filter=ConditionalFilter(field="IsWhite", value=True, value_type="boolean"),
        ...     appearance=AppearanceStyle(back_color="#F5F5DC")
        ... )
    """
    name: str
    selection: List[str] = field(default_factory=list)
    filter: Optional[ConditionalFilter] = None
    appearance: Optional[AppearanceStyle] = None
    uuid: str = field(default_factory=generate_uuid)


@dataclass
class FormElement:
    """Елемент форми (InputField, Button, Table, Pages, тощо)"""
    element_type: str  # "InputField", "Table", "Button", "LabelField", "LabelDecoration", "Pages", "Page", etc.
    name: str
    attribute: Optional[str] = None  # Для InputField, LabelField
    tabular_section: Optional[str] = None  # Для Table
    command: Optional[str] = None  # Для Button
    event_handlers: Dict[str, str] = field(default_factory=dict)  # {"OnChange": "ИмяМетода"}
    properties: Dict[str, any] = field(default_factory=dict)  # Додаткові властивості (title, hyperlink, pages_representation, behavior, etc.)
    child_items: List = field(default_factory=list)  # Для Pages, Page - вкладені елементи
    conditional_appearances: List[ConditionalAppearanceItem] = field(default_factory=list)  # v2.67.0+ ConditionalAppearance


@dataclass
class FormGroup:
    """Група елементів форми (UsualGroup, Pages, etc.)"""
    group_type: str  # "UsualGroup", "Pages", "CommandBar", etc.
    name: str
    title_ru: Optional[str] = None
    title_uk: Optional[str] = None
    title_en: Optional[str] = None
    group_direction: str = "Vertical"  # "Vertical", "Horizontal"
    representation: str = "None"  # "None", "NormalSeparation", "WeakSeparation", "StrongSeparation"
    show_title: bool = False
    child_items: List = field(default_factory=list)  # List[Union[FormElement, FormGroup]] - рекурсивно
    properties: Dict[str, any] = field(default_factory=dict)  # Додаткові властивості


@dataclass
class LongOperationSettings:
    """Налаштування фонового завдання (Background Job / Long Operation).

    Використовується для операцій, які тривають >3-5 секунд:
    - Імпорт/експорт даних
    - Генерація звітів з тисячами рядків
    - Пакетна обробка документів

    v3.0.0+

    Example:
        >>> # Мінімальні налаштування (використовуються defaults)
        >>> settings = LongOperationSettings()
        >>>
        >>> # Кастомні налаштування
        >>> settings = LongOperationSettings(
        ...     show_progress=True,
        ...     allow_cancel=True,
        ...     timeout_seconds=600,
        ...     progress_message="Завантаження даних...",
        ...     progress_message_uk="Завантаження даних...",
        ...     progress_message_en="Loading data..."
        ... )
    """
    # UI Options
    show_progress: bool = True                      # Показувати вікно прогресу
    allow_cancel: bool = True                       # Дозволити скасування операції
    progress_message: str = "Выполнение операции..."  # Текст повідомлення (ru)
    progress_message_uk: Optional[str] = "Виконання операції..."  # Текст повідомлення (uk)
    progress_message_en: Optional[str] = "Operation in progress..."  # Текст повідомлення (en)

    # Technical Options
    timeout_seconds: int = 300                      # Таймаут операції (за замовчуванням 5 хвилин)
    wait_completion_initial: float = 0              # Початкове очікування перед показом прогресу (0 = негайно)

    # Advanced Options
    use_additional_parameters: bool = False         # Передавати всі атрибути форми в Parameters
    output_messages: bool = True                    # Виводити повідомлення користувачу
    output_progress: bool = False                   # Виводити прогрес-бар (кастомний)

    def get_progress_message(self, language: str = "ru") -> str:
        """Отримати локалізоване повідомлення про прогрес."""
        if language == "uk" and self.progress_message_uk:
            return self.progress_message_uk
        elif language == "en" and self.progress_message_en:
            return self.progress_message_en
        return self.progress_message


@dataclass
class Command:
    """Команда форми"""
    name: str
    title_ru: str
    title_uk: str
    title_en: Optional[str] = None
    action: str = ""  # Ім'я методу-обробника
    tooltip_ru: Optional[str] = None
    tooltip_uk: Optional[str] = None
    tooltip_en: Optional[str] = None
    picture: Optional[str] = None  # StdPicture.Refresh, CommonPicture.xxx
    shortcut: Optional[str] = None  # F5, Ctrl+S, etc.
    uuid: str = field(default_factory=generate_uuid)
    bsl_code: Optional[str] = None  # BSL код обробника (якщо завантажено з файлу)

    # Long Operations / Background Jobs (v3.0.0+)
    long_operation: bool = False  # Чи є це фоновим завданням
    long_operation_settings: Optional[LongOperationSettings] = None  # Налаштування фонового завдання

    def __post_init__(self):
        """Автоматично створити налаштування якщо long_operation=True"""
        if self.long_operation and self.long_operation_settings is None:
            self.long_operation_settings = LongOperationSettings()


@dataclass
class FormAttribute:
    """Простий атрибут форми (не табличний)

    Використовується для:
    - SpreadsheetDocument (type='spreadsheet_document')
    - Binary data (type='binary_data')
    - Planner (type='planner') - для PlannerField (v2.47.0+)
    - Інших простих типів, які є атрибутами форми, а не процесора

    Відмінність від Attribute (process attribute):
    - FormAttribute існує тільки в формі (не зберігається в базі)
    - DataPath без префікса "Объект." (просто "ИмяАтрибута")
    - Оголошується в секції <Attributes> форми, а не в процесорі

    v2.15.1+
    """
    name: str
    type: str  # "spreadsheet_document", "binary_data", "planner", "string", etc.
    synonym_ru: Optional[str] = None
    synonym_uk: Optional[str] = None
    synonym_en: Optional[str] = None
    title_ru: Optional[str] = None
    title_uk: Optional[str] = None
    title_en: Optional[str] = None
    id: int = 1  # ID атрибуту форми

    # Planner-specific settings (v2.47.0+)
    time_scale: Optional[str] = None  # Hour, Day, Week, Month
    time_scale_interval: int = 1
    time_scale_format: Optional[str] = None  # e.g., 'DF="HH:mm"'
    display_current_date: bool = True
    show_weekends: bool = True

    def __post_init__(self):
        if not self.synonym_ru:
            self.synonym_ru = self.name
        if not self.synonym_uk:
            self.synonym_uk = self.name
        if not self.synonym_en:
            self.synonym_en = self.name
        if not self.title_ru:
            self.title_ru = self.synonym_ru
        if not self.title_uk:
            self.title_uk = self.synonym_uk
        if not self.title_en:
            self.title_en = self.synonym_en
        # Default time_scale_format based on time_scale
        if self.type == "planner" and self.time_scale and not self.time_scale_format:
            formats = {
                "Hour": 'DF="HH:mm"',
                "Day": 'DF="d"',
                "Week": 'DF="ddd, d MMMM"',
                "Month": 'DF="MMMM yyyy"',
            }
            self.time_scale_format = formats.get(self.time_scale, 'DF="HH:mm"')


@dataclass
class FormParameter:
    """Параметр форми (передається при відкритті форми)

    Використовується для:
    - Передачі контексту при відкритті форми (дата, режим перегляду, тощо)
    - Wizard flows (передача даних між кроками)
    - Фільтрація даних при відкритті (FilterDate, FilterStatus, тощо)

    Відмінність від FormAttribute:
    - FormParameter передається ЗЗовні при відкритті форми
    - FormAttribute існує всередині форми

    v2.36.0+ (Phase 2)

    Example:
        >>> # Дата фільтру як ключовий параметр
        >>> param = FormParameter(
        ...     name="FilterDate",
        ...     type="date",
        ...     key_parameter=True,
        ...     synonym_ru="Дата фильтра"
        ... )
        >>>
        >>> # Режим перегляду (булевий параметр)
        >>> param = FormParameter(
        ...     name="ViewMode",
        ...     type="boolean",
        ...     synonym_ru="Режим просмотра"
        ... )
    """
    name: str
    type: str  # "string", "number", "boolean", "date", "CatalogRef.*", "DocumentRef.*", etc.
    synonym_ru: Optional[str] = None
    synonym_uk: Optional[str] = None
    synonym_en: Optional[str] = None
    key_parameter: bool = False  # Чи є ключовим параметром форми
    uuid: str = field(default_factory=generate_uuid)

    def __post_init__(self):
        if not self.synonym_ru:
            self.synonym_ru = self.name
        if not self.synonym_uk:
            self.synonym_uk = self.name
        if not self.synonym_en:
            self.synonym_en = self.name


@dataclass
class TemplatePlaceholder:
    """Placeholder для заміни в HTML макеті.

    v2.41.0+

    Підтримує два типи заміни:
    - bsl_value: BSL вираз (напр. "ТекущийПользователь().Имя")
    - attribute: посилання на атрибут форми (напр. "CompanyName" → Объект.CompanyName)

    Example:
        >>> placeholder = TemplatePlaceholder(
        ...     name="{{UserName}}",
        ...     bsl_value="ТекущийПользователь().Имя"
        ... )
    """
    name: str  # Placeholder pattern, e.g. "{{UserName}}"
    bsl_value: Optional[str] = None   # BSL expression to substitute
    attribute: Optional[str] = None   # Form attribute name (will use Объект.AttributeName)


@dataclass
class TemplateAssets:
    """CSS/JS assets для інжекту в HTML макет.

    v2.41.0+

    Example:
        >>> assets = TemplateAssets(
        ...     styles=[{"file": "styles.css"}],
        ...     scripts=[{"inline": "function init() {}"}]
        ... )
    """
    styles: List[dict] = field(default_factory=list)   # [{"file": "path"} or {"inline": "css"}]
    scripts: List[dict] = field(default_factory=list)  # [{"file": "path"} or {"inline": "js"}]


@dataclass
class Template:
    """Макет обробки (HTMLDocument або SpreadsheetDocument).

    Templates are DataProcessor-level metadata objects that contain
    external content (HTML, SpreadsheetDocument) which can be loaded
    at runtime using GetTemplate() / ПолучитьМакет().

    v2.40.0+ (base), v2.41.0+ (automation)

    Example:
        >>> template = Template(
        ...     name="EmailTemplate",
        ...     template_type="HTMLDocument",
        ...     file_path="templates/email.html",
        ...     auto_field=True,
        ...     automation_file="templates/email.automation.yaml"
        ... )
    """
    name: str
    template_type: str  # "HTMLDocument" or "SpreadsheetDocument"
    file_path: Optional[str] = None     # Path to template content file
    content: Optional[str] = None       # Loaded content (for HTMLDocument)
    content_binary: Optional[bytes] = None  # Loaded binary content (for SpreadsheetDocument)
    uuid: str = field(default_factory=generate_uuid)

    # v2.41.0+ Automation fields
    auto_field: bool = False            # Auto-create form_attribute + HTMLDocumentField
    field_name: Optional[str] = None    # Custom field name (default: {name}Field)
    target_form: Optional[str] = None   # Target form name (default: first form)
    automation_file: Optional[str] = None  # Path to .automation.yaml file
    placeholders: List[TemplatePlaceholder] = field(default_factory=list)
    assets: Optional[TemplateAssets] = None

    def __post_init__(self):
        valid_types = {"HTMLDocument", "SpreadsheetDocument"}
        if self.template_type not in valid_types:
            raise ValueError(
                f"Template '{self.name}': Invalid template_type '{self.template_type}'. "
                f"Valid types: {valid_types}"
            )


@dataclass
class ValueTableAttribute:
    """ValueTable атрибут форми"""
    name: str
    title_ru: Optional[str] = None
    title_uk: Optional[str] = None
    title_en: Optional[str] = None
    columns: List[Column] = field(default_factory=list)
    id: int = 1


@dataclass
class ValueTreeAttribute:
    """ValueTree атрибут форми (ієрархічна таблиця).

    ValueTree - це ієрархічна структура даних для відображення в Tree mode.
    На відміну від ValueTable, підтримує вкладені рядки (parent-child).

    Використовується з Table елементом з representation: tree.

    v2.64.0+

    Example:
        >>> vt = ValueTreeAttribute(
        ...     name="ДеревоДанних",
        ...     title_ru="Дерево данных",
        ...     columns=[
        ...         Column(name="Наименование", type="string"),
        ...         Column(name="Уровень", type="number")
        ...     ]
        ... )
    """
    name: str
    title_ru: Optional[str] = None
    title_uk: Optional[str] = None
    title_en: Optional[str] = None
    columns: List[Column] = field(default_factory=list)
    id: int = 1  # ID атрибуту форми


@dataclass
class DynamicListParameter:
    """Параметр динамічного списку"""
    name: str
    type: str  # "String", "Number", "Date", "Boolean", etc.
    default_value: Optional[any] = None  # Значення за замовчуванням


@dataclass
class DynamicListColumn:
    """Колонка для відображення в DynamicList Table"""
    field: str  # Ім'я поля з запиту (Description, Code, Ref, Дата, тощо)
    title_ru: Optional[str] = None  # Заголовок колонки (якщо відрізняється від field)
    title_uk: Optional[str] = None
    title_en: Optional[str] = None
    width: Optional[int] = None  # Column width in character units (approx. number of visible characters, NOT pixels)


@dataclass
class DynamicListAttribute:
    """Атрибут форми типу DynamicList"""
    name: str
    title_ru: Optional[str] = None
    title_uk: Optional[str] = None
    title_en: Optional[str] = None
    manual_query: bool = False  # False = на основі MainTable, True = довільний QueryText
    main_table: Optional[str] = None  # Document.*, Catalog.*, DocumentJournal.* (опціонально для manual_query=true)
    query_text: Optional[str] = None  # Текст запиту для ManualQuery=true
    key_fields: List[str] = field(default_factory=list)  # Ключові поля для ідентифікації рядків (KeyField) - використовується для manual_query=true без main_table
    parameters: List[DynamicListParameter] = field(default_factory=list)  # Параметри запиту
    use_always_fields: List[str] = field(default_factory=list)  # Обов'язкові поля (UseAlways)
    functional_options: List[str] = field(default_factory=list)  # Функціональні опції
    auto_save_user_settings: Optional[bool] = None  # AutoSaveUserSettings
    main_attribute: bool = False  # Чи є головним атрибутом форми
    columns: List[DynamicListColumn] = field(default_factory=list)  # Колонки для відображення на формі
    skip_stub_validation: bool = False  # Пропустити генерацію атрибутів для заглушки (для складних запитів)
    id: int = 1  # ID атрибуту форми

    # DCS Setting IDs (auto-generated unique UUIDs for user settings)
    filter_setting_id: str = field(default_factory=generate_uuid)
    order_setting_id: str = field(default_factory=generate_uuid)
    appearance_setting_id: str = field(default_factory=generate_uuid)
    items_setting_id: str = field(default_factory=generate_uuid)

    def __post_init__(self):
        if not self.title_ru:
            self.title_ru = self.name
        if not self.title_uk:
            self.title_uk = self.name
        if not self.title_en:
            self.title_en = self.name

        # Валідація: для manual_query=false main_table обов'язковий
        if not self.manual_query and not self.main_table:
            raise ValueError(f"DynamicList '{self.name}': main_table обов'язковий для manual_query=false")


@dataclass
class Form:
    """Форма обробки 1C"""
    name: str  # Ім'я форми (наприклад, "Форма", "НастройкиФормы")
    default: bool = False  # Чи є формою за замовчуванням
    include: Optional[str] = None  # Шлях до include файлу (для модульності)
    handlers_dir: Optional[str] = None  # Директорія з handlers для цієї форми
    handlers_file: Optional[str] = None  # Шлях до монолітного BSL файлу з handlers для цієї форми (v2.69.0+)

    # Елементи форми
    elements: List[FormElement] = field(default_factory=list)
    auto_command_bar_elements: List[FormElement] = field(default_factory=list)
    form_groups: List[FormGroup] = field(default_factory=list)
    command_bars: List[FormGroup] = field(default_factory=list)

    # Команди форми
    commands: List[Command] = field(default_factory=list)

    # Події форми
    events: Dict[str, str] = field(default_factory=dict)  # {"OnOpen": "ПриОткрытии"}
    events_bsl: Dict[str, str] = field(default_factory=dict)  # BSL код для подій

    # Властивості форми
    properties: Dict[str, any] = field(default_factory=dict)  # Title, AutoTitle, etc

    # Параметри форми (передаються при відкритті форми, v2.36.0+)
    parameters: List[FormParameter] = field(default_factory=list)

    # Атрибути форми (тільки для цієї форми)
    form_attributes: List[FormAttribute] = field(default_factory=list)  # v2.15.1+ (SpreadsheetDocument, BinaryData, etc.)
    value_table_attributes: List[ValueTableAttribute] = field(default_factory=list)
    value_tree_attributes: List[ValueTreeAttribute] = field(default_factory=list)  # v2.64.0+ (hierarchical data)
    dynamic_list_attributes: List[DynamicListAttribute] = field(default_factory=list)

    # Допоміжні процедури/функції (helpers) для цієї форми
    helper_procedures: Dict[str, str] = field(default_factory=dict)  # {"НазваПроцедури": "BSL код"}

    # Документація модуля форми (v2.14.0+)
    documentation_file: Optional[str] = None  # Шлях до файлу документації (відносно config.yaml)
    documentation: Optional[str] = None  # Об'єднана документація (з файлу + з регіону handlers.bsl)

    # Модульні змінні (v2.73.0+)
    # Декларації Перем на рівні модуля (до процедур/функцій)
    module_variables: Optional[str] = None

    # UUID для форми
    uuid: str = field(default_factory=generate_uuid)

    # Умовне оформлення на рівні форми (v2.67.0+)
    conditional_appearances: List[ConditionalAppearanceItem] = field(default_factory=list)


@dataclass
class ValidationConfig:
    """
    Налаштування валідації BSL коду.

    Підтримує 2 типи валідації:
    1. Синтаксична - швидка перевірка для різних режимів клієнта
    2. Семантична - глибока перевірка (некоректні посилання, пусті обробники, тощо)

    Example:
        >>> # Мінімальна валідація (за замовчуванням)
        >>> config = ValidationConfig()
        >>>
        >>> # Розширена валідація з семантичною перевіркою
        >>> config = ValidationConfig(
        ...     semantic_check_enabled=True,
        ...     check_web_client=True,
        ...     check_extended_modules=True
        ... )
    """
    # ===== Синтаксична перевірка =====
    syntax_check_enabled: bool = True   # Увімкнути синтаксичну перевірку
    check_thin_client: bool = True      # Режим тонкого клієнта
    check_server: bool = True           # Режим сервера
    check_web_client: bool = False      # Режим веб-клієнта
    check_external_connection: bool = False  # Зовнішнє з'єднання
    check_thick_client: bool = False    # Товстий клієнт

    # ===== Семантична перевірка =====
    semantic_check_enabled: bool = True  # Семантична перевірка увімкнена за замовчуванням
    check_incorrect_references: bool = True   # Пошук некоректних посилань
    check_handlers_existence: bool = True     # Перевірка існування обробників
    check_empty_handlers: bool = True         # Пошук пустих обробників
    check_unreference_procedures: bool = False # Невикористовувані процедури (може бути повільно)
    check_extended_modules: bool = True       # Розширена перевірка типів через точку

    # Aliases для backwards compatibility (v2.52 -> v2.53)
    @property
    def check_modules_enabled(self) -> bool:
        """Alias для syntax_check_enabled (backwards compatibility)."""
        return self.syntax_check_enabled

    @property
    def check_config_enabled(self) -> bool:
        """Alias для semantic_check_enabled (backwards compatibility)."""
        return self.semantic_check_enabled


# ===== BSP Integration (v2.57.0+) - PRO Feature =====


@dataclass
class BSPCommand:
    """Команда BSP обробки для СведенияОВнешнейОбработке().

    Визначає одну команду (печатну форму, заповнення, тощо) яка буде
    зареєстрована в БСП при підключенні обробки.

    PRO Feature: Потребує PRO ліцензії.

    v2.57.0+

    Example:
        >>> cmd = BSPCommand(
        ...     id="СчетНаОплату",
        ...     title_ru="Счет на оплату",
        ...     title_uk="Рахунок на оплату",
        ...     usage="CallOfServerMethod",
        ...     modifier="ПечатьMXL"
        ... )
    """
    id: str                                     # Унікальний ідентифікатор команди
    title_ru: str                               # Російська назва (Представление)
    title_uk: Optional[str] = None              # Українська назва
    title_en: Optional[str] = None              # Англійська назва
    usage: str = "CallOfServerMethod"           # Тип виклику: CallOfServerMethod, CallOfClientMethod, OpenForm
    modifier: Optional[str] = None              # Модифікатор: "ПечатьMXL" для MXL макетів
    handler: Optional[str] = None               # Кастомне ім'я обробника (за замовчуванням Печать{id})
    template_name: Optional[str] = None         # Посилання на макет для печатних форм
    show_notification: bool = True              # Показувати "Виконується..." (ПоказыватьОповещение)
    check_posting: bool = True                  # Перевіряти проведення документів
    hide: bool = False                          # Приховати команду (Скрыть)
    replaced_commands: Optional[str] = None     # Команди, які замінює (ЗаменяемыеКоманды)
    uuid: str = field(default_factory=generate_uuid)

    def __post_init__(self):
        if not self.title_uk:
            self.title_uk = self.title_ru
        if not self.title_en:
            self.title_en = self.title_ru


@dataclass
class BSPConfig:
    """Конфігурація інтеграції з БСП (Бібліотека стандартних підсистем).

    Визначає параметри для функції СведенияОВнешнейОбработке() та
    генерації відповідного ObjectModule для зовнішніх обробок БСП.

    PRO Feature: Потребує PRO ліцензії.

    v2.57.0+

    Supported BSP types:
    - PrintForm (ПечатнаяФорма) - зовнішні печатні форми
    - ObjectFilling (ЗаполнениеОбъекта) - заповнення об'єктів
    - CreationOfRelatedObjects (СозданиеСвязанныхОбъектов) - створення пов'язаних
    - Report (Отчет) - контекстні звіти
    - AdditionalDataProcessor (ДополнительнаяОбработка) - глобальні обробки
    - AdditionalReport (ДополнительныйОтчет) - глобальні звіти

    Example:
        >>> config = BSPConfig(
        ...     type="PrintForm",
        ...     version="1.0",
        ...     targets=["Документ.СчетНаОплатуПокупателю"],
        ...     commands=[
        ...         BSPCommand(id="СчетНаОплату", title_ru="Счет на оплату")
        ...     ]
        ... )
    """
    type: str                                   # Тип обробки: PrintForm, ObjectFilling, Report, etc.
    version: str = "1.0"                        # Версія обробки (формат X.Y)
    safe_mode: bool = True                      # Безпечний режим (БезопасныйРежим)
    information: Optional[str] = None           # Опис для адміністратора (Информация)
    targets: List[str] = field(default_factory=list)  # Повні імена об'єктів (Назначение)
    commands: List[BSPCommand] = field(default_factory=list)  # Команди обробки
    print_handler: str = "Печать"               # Ім'я головної процедури друку
    uuid: str = field(default_factory=generate_uuid)

    # Валідні типи обробок
    VALID_TYPES = {
        "PrintForm",           # ПечатнаяФорма
        "ObjectFilling",       # ЗаполнениеОбъекта
        "CreationOfRelatedObjects",  # СозданиеСвязанныхОбъектов
        "Report",              # Отчет
        "AdditionalDataProcessor",   # ДополнительнаяОбработка
        "AdditionalReport",    # ДополнительныйОтчет
        "MessageTemplate",     # ШаблонСообщения
    }

    def __post_init__(self):
        if self.type not in self.VALID_TYPES:
            raise ValueError(
                f"BSPConfig: Invalid type '{self.type}'. "
                f"Valid types: {self.VALID_TYPES}"
            )
        if not self.targets:
            raise ValueError("BSPConfig: 'targets' cannot be empty")
        if not self.commands:
            raise ValueError("BSPConfig: 'commands' cannot be empty")


@dataclass
class Processor:
    """Зовнішня обробка 1C"""
    name: str
    synonym_ru: Optional[str] = None
    synonym_uk: Optional[str] = None
    synonym_en: Optional[str] = None
    platform_version: str = "2.11"  # "2.11" або "2.18"
    attributes: List[Attribute] = field(default_factory=list)
    tabular_sections: List[TabularSection] = field(default_factory=list)

    # Compact multilang support (v2.69.0+)
    # Порядок мов для array/pipe синтаксису. Перша мова = primary (fallback).
    languages: List[str] = field(default_factory=lambda: ["ru", "uk", "en"])

    # Нова структура: список форм
    forms: List[Form] = field(default_factory=list)

    # Макети (Templates) - v2.40.0+
    templates: List[Template] = field(default_factory=list)

    # Модуль об'єкта обробки (ObjectModule.bsl)
    object_module_bsl: Optional[str] = None  # Готовий BSL код модуля об'єкта
    object_module_from_handlers: Optional[str] = None  # Код з регіону #Область МодульОбъекта в handlers.bsl (v2.66.0+)

    # UUID для обробки
    main_uuid: str = field(default_factory=generate_uuid)
    object_id: str = field(default_factory=generate_uuid)
    type_id: str = field(default_factory=generate_uuid)
    value_id: str = field(default_factory=generate_uuid)
    form_uuid: str = field(default_factory=generate_uuid)

    # Налаштування валідації BSL коду (v2.12.0+)
    validation: ValidationConfig = field(default_factory=ValidationConfig)

    # Налаштування тестування (v2.16.0+)
    tests_config: Optional[TestsConfig] = None  # Конфігурація тестів (якщо є tests_file)

    # Long Operations Handlers (v3.0.0+)
    # Dict[handler_name, bsl_code]: {"ImportКнопка": "...", "ImportВФоне": "...", "ImportЗавершение": "...", "ImportНаСервере": "..."}
    long_operation_handlers: Dict[str, str] = field(default_factory=dict)

    # BSP Integration (v2.57.0+) - PRO Feature
    # Конфігурація для генерації зовнішніх обробок БСП (печатні форми, заповнення, тощо)
    bsp_config: Optional[BSPConfig] = None

    def __post_init__(self):
        if not self.synonym_ru:
            self.synonym_ru = self.name
        if not self.synonym_uk:
            self.synonym_uk = self.name
        if not self.synonym_en:
            self.synonym_en = self.name

    def add_attribute(self, name: str, type: str, **kwargs) -> Attribute:
        """Додати реквізит"""
        attr = Attribute(name=name, type=type, **kwargs)
        self.attributes.append(attr)
        return attr

    def add_tabular_section(self, name: str, **kwargs) -> TabularSection:
        """Додати табличну частину"""
        ts = TabularSection(name=name, **kwargs)
        self.tabular_sections.append(ts)
        return ts

    # Методи для роботи з формами
    def add_form(self, name: str, default: bool = False, **kwargs) -> Form:
        """Додати форму"""
        form = Form(name=name, default=default, **kwargs)
        self.forms.append(form)
        return form

    def get_default_form(self) -> Optional[Form]:
        """Отримати форму за замовчуванням"""
        for form in self.forms:
            if form.default:
                return form
        # Якщо немає форми з default=True, повернути першу
        return self.forms[0] if self.forms else None

    def get_form_by_name(self, name: str) -> Optional[Form]:
        """Отримати форму за ім'ям"""
        for form in self.forms:
            if form.name == name:
                return form
        return None


# ===== Testing Infrastructure (v2.16.0+) =====


@dataclass
class MessageAssertion:
    """Перевірка повідомлень у тесті (v2.19.0+: extended assertions)

    Example:
        >>> MessageAssertion(contains="Calculation complete")
        >>> MessageAssertion(equals="Результат: 100")
        >>> MessageAssertion(count=3)
        >>> MessageAssertion(matches="^Result: \\d+$")  # v2.19.0+
        >>> MessageAssertion(starts_with="Error:")      # v2.19.0+
    """
    # Basic assertions (v2.16.0+)
    contains: Optional[str] = None  # Повідомлення містить текст
    equals: Optional[str] = None    # Повідомлення точно дорівнює
    count: Optional[int] = None     # Кількість повідомлень

    # Extended string assertions (v2.19.0+)
    matches: Optional[str] = None       # Regex pattern
    starts_with: Optional[str] = None   # Починається з
    ends_with: Optional[str] = None     # Закінчується на


@dataclass
class TableAssertion:
    """Перевірка табличної частини / ValueTable у тесті

    Example:
        >>> TableAssertion(
        ...     table_name="Results",
        ...     row_count=10,
        ...     columns=["Product", "Quantity", "Price"]
        ... )
    """
    table_name: str                          # Ім'я таблиці (TabularSection або ValueTable)
    row_count: Optional[int] = None          # Очікувана кількість рядків
    columns: List[str] = field(default_factory=list)  # Перевірка наявності колонок
    row_data: Optional[Dict[int, Dict[str, any]]] = None  # Перевірка конкретних значень {row_idx: {column: value}}


@dataclass
class ExceptionAssertion:
    """Перевірка виключень у тесті

    Example:
        >>> ExceptionAssertion(contains="Amount must be positive")
        >>> ExceptionAssertion(raised=True)
    """
    raised: bool = True                     # Чи має виникнути виключення
    contains: Optional[str] = None          # Текст помилки містить


@dataclass
class TestAssertion:
    """Assertions для тесту (що перевіряти після виконання)

    v2.19.0+: Extended assertions support
    - Simple value: {"Result": 30} - equality check
    - Extended: {"Price": {"greater_than": 100, "less_than": 200}}

    Example:
        >>> # Basic assertions (v2.16.0+)
        >>> TestAssertion(
        ...     attributes={"Result": 30, "Status": "Complete"},
        ...     messages=[MessageAssertion(contains="Done")],
        ...     tables=[TableAssertion("Results", row_count=5)]
        ... )
        >>>
        >>> # Extended assertions (v2.19.0+)
        >>> TestAssertion(
        ...     attributes={
        ...         "Price": {"greater_than": 100, "less_than": 200},
        ...         "Code": {"matches": "^PROD-\\d+$", "starts_with": "PROD-"},
        ...         "Status": {"in": ["New", "Processing", "Done"]}
        ...     }
        ... )
    """
    # Очікувані значення атрибутів
    # Може бути: {name: value} для equals або {name: {assertion: value}} для extended
    attributes: Dict[str, any] = field(default_factory=dict)

    messages: List[MessageAssertion] = field(default_factory=list)  # Перевірка повідомлень
    tables: List[TableAssertion] = field(default_factory=list)  # Перевірка таблиць
    exception: Optional[ExceptionAssertion] = None  # Перевірка виключення


@dataclass
class TestSetup:
    """Setup частина тесту (підготовка даних перед виконанням)

    Example:
        >>> TestSetup(
        ...     attributes={"Number1": 10, "Number2": 20},
        ...     table_rows={
        ...         "Lines": [
        ...             {"Product": "Apple", "Quantity": 5},
        ...             {"Product": "Orange", "Quantity": 3}
        ...         ]
        ...     }
        ... )
    """
    attributes: Dict[str, any] = field(default_factory=dict)  # Атрибути для встановлення {name: value}
    table_rows: Dict[str, List[Dict[str, any]]] = field(default_factory=dict)  # Рядки для таблиць {table_name: [row_dict]}


@dataclass
class TestFixture:
    """Фікстура для тестів - reusable setup data (v2.20.0+)

    Fixtures дозволяють повторно використовувати setup дані між тестами.
    Це зменшує дублювання коду і покращує maintainability.

    Example:
        >>> # Define fixture
        >>> common_setup = TestFixture(
        ...     name="common_setup",
        ...     setup=TestSetup(
        ...         attributes={"Database": "Test", "Mode": "Test"}
        ...     )
        ... )
        >>>
        >>> # Use in test
        >>> test = DeclarativeTest(
        ...     name="test_with_fixture",
        ...     use_fixtures=["common_setup"],
        ...     execute_command="Process"
        ... )
    """
    name: str                           # Ім'я фікстури
    setup: TestSetup                    # Setup дані (attributes, table_rows)


@dataclass
class DeclarativeTest:
    """Декларативний тест (описаний у YAML)

    Example (simple):
        >>> DeclarativeTest(
        ...     name="test_calculation",
        ...     description="Test simple calculation",
        ...     setup=TestSetup(attributes={"Number1": 10, "Number2": 20}),
        ...     execute_command="Calculate",
        ...     assert_result=TestAssertion(attributes={"Result": 30})
        ... )

    Example (with fixtures, v2.20.0+):
        >>> DeclarativeTest(
        ...     name="test_with_fixtures",
        ...     use_fixtures=["common_setup", "with_products"],
        ...     setup=TestSetup(attributes={"Discount": 10}),  # Applied after fixtures
        ...     execute_command="CalculateTotal",
        ...     assert_result=TestAssertion(attributes={"Total": 270})
        ... )
    """
    name: str                                   # Ім'я тесту (має відповідати Python naming: test_*)
    description: Optional[str] = None           # Опис тесту
    use_fixtures: List[str] = field(default_factory=list)  # Список fixtures для застосування (v2.20.0+)
    setup: Optional[TestSetup] = None           # Підготовка даних (застосовується ПІСЛЯ fixtures)
    execute_command: Optional[str] = None       # Яку команду виконати
    execute_procedure: Optional[str] = None     # Або яку процедуру викликати (для custom логіки)
    assert_result: Optional[TestAssertion] = None  # Що перевіряти після виконання


@dataclass
class ProceduralTests:
    """Процедурні тести (написані вручну в BSL файлі)

    Example:
        >>> ProceduralTests(
        ...     file="tests/custom_tests.bsl",
        ...     procedures=["Тест_МножественныеТаблицы", "Тест_СложнаяВалидация"]
        ... )
    """
    file: str                               # Шлях до BSL файлу з тестовими процедурами (відносно tests.yaml)
    procedures: List[str] = field(default_factory=list)  # Список процедур Тест_* для виконання


@dataclass
class ObjectModuleTestsConfig:
    """Конфігурація тестів для ObjectModule (v2.23.2+)

    ObjectModule тести виконуються через External Connection (швидко, без UI).

    Example:
        >>> config = ObjectModuleTestsConfig(
        ...     declarative=[
        ...         DeclarativeTest(name="test_calc", execute_command="Calculate")
        ...     ],
        ...     procedural=ProceduralTests(
        ...         file="objectmodule_tests.bsl",
        ...         procedures=["Тест_БізнесЛогіка"]
        ...     )
        ... )
    """
    declarative: List[DeclarativeTest] = field(default_factory=list)  # Декларативні тести
    procedural: Optional[ProceduralTests] = None  # Процедурні тести (ObjectModule style)


@dataclass
class FormTestsConfig:
    """Конфігурація тестів для конкретної форми (v2.23.2+)

    Form тести виконуються через Automation Server (повільно, з UI).

    Example:
        >>> config = FormTestsConfig(
        ...     name="Форма",
        ...     declarative=[
        ...         DeclarativeTest(name="test_button", click_button="Calculate")
        ...     ],
        ...     procedural=ProceduralTests(
        ...         file="form_Форма_tests.bsl",
        ...         procedures=["Тест_КнопкаВидимість"]
        ...     )
        ... )
    """
    name: str  # Ім'я форми
    declarative: List[DeclarativeTest] = field(default_factory=list)  # Декларативні тести
    procedural: Optional[ProceduralTests] = None  # Процедурні тести (Form Module style)


@dataclass
class TestsConfig:
    """Конфігурація тестів для процесора (v2.23.2+ - new architecture)

    BREAKING CHANGE: Повна переробка структури з auto-detection.

    Тепер підтримує:
    - ObjectModule тести (виконуються через External Connection)
    - Per-form тести (виконуються через Automation Server)
    - Автоматична детекція типу тестів (без флагів!)

    Architecture:
        objectmodule_tests → External Connection (fast, no UI)
        forms[].tests → Automation Server (slow, with UI)

    Example:
        >>> config = TestsConfig(
        ...     objectmodule_tests=ObjectModuleTestsConfig(
        ...         declarative=[...],
        ...         procedural=ProceduralTests(...)
        ...     ),
        ...     forms=[
        ...         FormTestsConfig(
        ...             name="Форма",
        ...             declarative=[...],
        ...             procedural=ProceduralTests(...)
        ...         )
        ...     ]
        ... )
    """
    # v2.23.2: Нова структура з auto-detection
    objectmodule_tests: Optional[ObjectModuleTestsConfig] = None  # ObjectModule тести
    forms: List[FormTestsConfig] = field(default_factory=list)  # Per-form тести

    # Fixtures (reusable setup data, v2.20.0+)
    fixtures: Dict[str, TestFixture] = field(default_factory=dict)

    # Налаштування виконання тестів
    persistent_ib_path: Optional[str] = None  # Шлях до тестової бази
    timeout: int = 300  # Timeout для виконання всіх тестів (секунди)
