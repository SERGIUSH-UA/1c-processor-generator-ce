"""
BSP Integration Generator - PRO Feature.

Generates BSP-compatible ObjectModule code including:
- СведенияОВнешнейОбработке() function
- Печать() procedure for print forms
- Integration with БСП (1C Standard Subsystems Library)

Copyright (c) 2024-2025 ITDEO. All rights reserved.
This module is compiled to .pyd in release builds.

v2.57.0+
"""

from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..models import BSPConfig, BSPCommand

# ============================================================================
# BSP PROTECTED CONSTANTS
# ============================================================================

# Маппінг YAML типів обробок → Внутрішні ідентифікатори
BSP_TYPE_MAPPING_YAML = {
    "print_form": "PrintForm",
    "object_filling": "ObjectFilling",
    "creation_of_related": "CreationOfRelatedObjects",
    "report": "Report",
    "additional_processor": "AdditionalDataProcessor",
    "additional_report": "AdditionalReport",
    "message_template": "MessageTemplate",
}

# Маппінг внутрішніх типів → 1C ідентифікатори (для СведенияОВнешнейОбработке)
BSP_KIND_MAPPING = {
    "PrintForm": "ПечатнаяФорма",
    "ObjectFilling": "ЗаполнениеОбъекта",
    "CreationOfRelatedObjects": "СозданиеСвязанныхОбъектов",
    "Report": "Отчет",
    "AdditionalDataProcessor": "ДополнительнаяОбработка",
    "AdditionalReport": "ДополнительныйОтчет",
    "MessageTemplate": "ШаблонСообщения",
}

# Маппінг YAML usage → Внутрішні ідентифікатори
BSP_USAGE_MAPPING_YAML = {
    "server_method": "CallOfServerMethod",
    "client_method": "CallOfClientMethod",
    "open_form": "OpenForm",
    "filling_form": "FillingForm",
    "data_import": "DataImportFromFile",
    "safe_mode_scenario": "SafeModeScenario",
}

# Маппінг внутрішніх usage → 1C ідентифікатори
BSP_USAGE_MAPPING = {
    "CallOfServerMethod": "ВызовСерверногоМетода",
    "CallOfClientMethod": "ВызовКлиентскогоМетода",
    "OpenForm": "ОткрытиеФормы",
    "FillingForm": "ЗаполнениеФормы",
    "DataImportFromFile": "ЗагрузкаДанныхИзФайла",
    "SafeModeScenario": "СценарийВБезопасномРежиме",
}

# BSP версія для СведенияОВнешнейОбработке
BSP_VERSION = "2.4.6.113"  # Актуальна версія БСП


# ============================================================================
# BSP CODE TEMPLATES
# ============================================================================

# Шаблон модуля об'єкта для BSP обробки
BSP_OBJECT_MODULE_TEMPLATE = '''#Если Сервер Или ТолстыйКлиентОбычноеПриложение Или ВнешнееСоединение Тогда

#Область ПрограммныйИнтерфейс

{svedeniya_function}

{print_procedure}

#КонецОбласти

#Область СлужебныеПроцедурыИФункции

{helper_procedures}

#КонецОбласти

#Иначе
	ВызватьИсключение НСтр("ru='Недопустимый вызов объекта на клиенте.';uk='Неприпустимий виклик об`єкту на клієнті.';en='Invalid call of the object on the client.'");
#КонецЕсли
'''

# Шаблон СведенияОВнешнейОбработке
BSP_SVEDENIYA_TEMPLATE = '''// Возвращает сведения о внешней обработке для регистрации в БСП.
//
// Возвращаемое значение:
//   Структура - параметры регистрации внешней обработки.
//
Функция СведенияОВнешнейОбработке() Экспорт

	ПараметрыРегистрации = Новый Структура;

	ПараметрыРегистрации.Вставить("Вид", "{bsp_kind}");
	ПараметрыРегистрации.Вставить("Версия", "{version}");
	ПараметрыРегистрации.Вставить("БезопасныйРежим", {safe_mode});
	ПараметрыРегистрации.Вставить("Информация", НСтр("ru='{info_ru}';uk='{info_uk}';en='{info_en}'"));

	// Назначение обработки
	НазначениеОбработки = Новый Массив;
{assignments}
	ПараметрыРегистрации.Вставить("Назначение", НазначениеОбработки);

	// Команды обработки
	Команды = Новый ТаблицаЗначений;
	Команды.Колонки.Добавить("Идентификатор", Новый ОписаниеТипов("Строка"));
	Команды.Колонки.Добавить("Представление", Новый ОписаниеТипов("Строка"));
	Команды.Колонки.Добавить("Использование", Новый ОписаниеТипов("Строка"));
	Команды.Колонки.Добавить("ПоказыватьОповещение", Новый ОписаниеТипов("Булево"));
	Команды.Колонки.Добавить("Модификатор", Новый ОписаниеТипов("Строка"));
	Команды.Колонки.Добавить("Скрыть", Новый ОписаниеТипов("Булево"));
	Команды.Колонки.Добавить("ЗаменяемыеКоманды", Новый ОписаниеТипов("Строка"));

{commands}

	ПараметрыРегистрации.Вставить("Команды", Команды);

	Возврат ПараметрыРегистрации;

КонецФункции'''

# Шаблон команди
BSP_COMMAND_TEMPLATE = '''	НоваяКоманда = Команды.Добавить();
	НоваяКоманда.Идентификатор = "{cmd_id}";
	НоваяКоманда.Представление = НСтр("ru='{title_ru}';uk='{title_uk}';en='{title_en}'");
	НоваяКоманда.Использование = "{usage}";
	НоваяКоманда.ПоказыватьОповещение = {show_notification};
	НоваяКоманда.Модификатор = "{modifier}";
	НоваяКоманда.Скрыть = {hide};
	НоваяКоманда.ЗаменяемыеКоманды = "{replaced_commands}";
'''

# Шаблон процедури Печать для PrintForm
BSP_PRINT_PROCEDURE_TEMPLATE = '''// Обработчик печати.
//
// Параметры:
//   МассивОбъектов      - Массив - ссылки на объекты, которые нужно распечатать.
//   КоллекцияПечатныхФорм - ТаблицаЗначений - информация о табличных документах.
//   ОбъектыПечати       - СписокЗначений - соответствие между объектами и областями.
//   ПараметрыВывода     - Структура - дополнительные параметры.
//
Процедура Печать(МассивОбъектов, КоллекцияПечатныхФорм, ОбъектыПечати, ПараметрыВывода) Экспорт

{print_handlers}

КонецПроцедуры'''

# Шаблон обробника однієї печатної форми
BSP_PRINT_HANDLER_TEMPLATE = '''	Если УправлениеПечатью.НужноПечататьМакет(КоллекцияПечатныхФорм, "{cmd_id}") Тогда
		ПечатныйДокумент = Печать{cmd_id}(МассивОбъектов, ОбъектыПечати);
		УправлениеПечатью.ВывестиТабличныйДокументВКоллекцию(
			КоллекцияПечатныхФорм,
			"{cmd_id}",
			НСтр("ru='{title_ru}';uk='{title_uk}';en='{title_en}'"),
			ПечатныйДокумент
		);
	КонецЕсли;
'''

# Шаблон заглушки для функції друку
BSP_PRINT_STUB_TEMPLATE = '''// Формирование печатной формы "{cmd_id}".
//
// Параметры:
//   МассивОбъектов - Массив - ссылки на объекты для печати.
//   ОбъектыПечати  - СписокЗначений - соответствие объектов и областей.
//
// Возвращаемое значение:
//   ТабличныйДокумент - сформированный документ для печати.
//
Функция Печать{cmd_id}(МассивОбъектов, ОбъектыПечати)

	ТабличныйДокумент = Новый ТабличныйДокумент;
	ТабличныйДокумент.КлючПараметровПечати = "ПАРАМЕТРЫ_ПЕЧАТИ_{cmd_id}";

	// TODO: Реализуйте формирование печатной формы
	// Макет = ПолучитьМакет("{template_name}");
	//
	// Для Каждого Ссылка Из МассивОбъектов Цикл
	//     НачалоОбласти = ТабличныйДокумент.ВысотаТаблицы + 1;
	//
	//     // Получение данных и вывод областей макета...
	//
	//     УправлениеПечатью.ЗадатьОбластьПечатиДокумента(ТабличныйДокумент, НачалоОбласти, ОбъектыПечати, Ссылка);
	// КонецЦикла;

	Возврат ТабличныйДокумент;

КонецФункции
'''


# ============================================================================
# BSP GENERATOR CLASS
# ============================================================================

class BSPGenerator:
    """
    Generates BSP-compatible ObjectModule code.

    PRO Feature: Requires PRO license.

    Usage:
        >>> from models import BSPConfig, BSPCommand
        >>> config = BSPConfig(
        ...     type="PrintForm",
        ...     targets=["Документ.СчетНаОплату"],
        ...     commands=[BSPCommand(id="Счет", title_ru="Счет на оплату")]
        ... )
        >>> generator = BSPGenerator(config)
        >>> bsl_code = generator.generate()
    """

    def __init__(self, bsp_config: "BSPConfig", user_handlers: Optional[str] = None):
        """
        Initialize BSP generator.

        Args:
            bsp_config: BSP configuration from YAML
            user_handlers: Optional user-provided handler code
        """
        self.config = bsp_config
        self.user_handlers = user_handlers or ""

    def generate(self) -> str:
        """
        Generate complete ObjectModule BSL code.

        Returns:
            str: BSL code for ObjectModule.bsl
        """
        # Generate СведенияОВнешнейОбработке
        svedeniya = self._generate_svedeniya()

        # Generate Печать procedure (for PrintForm type)
        print_procedure = ""
        if self.config.type == "PrintForm":
            print_procedure = self._generate_print_procedure()

        # Combine with user handlers
        helper_procedures = self._combine_handlers()

        # Build final module
        return BSP_OBJECT_MODULE_TEMPLATE.format(
            svedeniya_function=svedeniya,
            print_procedure=print_procedure,
            helper_procedures=helper_procedures,
        )

    def _generate_svedeniya(self) -> str:
        """Generate СведенияОВнешнейОбработке function."""
        # Get BSP kind
        bsp_kind = BSP_KIND_MAPPING.get(self.config.type, "ПечатнаяФорма")

        # Safe mode
        safe_mode = "Истина" if self.config.safe_mode else "Ложь"

        # Information
        info = self.config.information or ""
        info_ru = info
        info_uk = info
        info_en = info

        # Generate assignments
        assignments_lines = []
        for target in self.config.targets:
            assignments_lines.append(f'\tНазначениеОбработки.Добавить("{target}");')
        assignments = "\n".join(assignments_lines)

        # Generate commands
        commands_code = self._generate_commands()

        return BSP_SVEDENIYA_TEMPLATE.format(
            bsp_kind=bsp_kind,
            version=self.config.version,
            safe_mode=safe_mode,
            info_ru=info_ru,
            info_uk=info_uk,
            info_en=info_en,
            assignments=assignments,
            commands=commands_code,
        )

    def _generate_commands(self) -> str:
        """Generate commands table population code."""
        commands_lines = []

        for cmd in self.config.commands:
            # Get usage string
            usage = BSP_USAGE_MAPPING.get(cmd.usage, "ВызовСерверногоМетода")

            # Boolean conversions
            show_notification = "Истина" if cmd.show_notification else "Ложь"
            hide = "Истина" if cmd.hide else "Ложь"

            # Optional values
            modifier = cmd.modifier or ""
            replaced_commands = cmd.replaced_commands or ""

            cmd_code = BSP_COMMAND_TEMPLATE.format(
                cmd_id=cmd.id,
                title_ru=cmd.title_ru,
                title_uk=cmd.title_uk or cmd.title_ru,
                title_en=cmd.title_en or cmd.title_ru,
                usage=usage,
                show_notification=show_notification,
                modifier=modifier,
                hide=hide,
                replaced_commands=replaced_commands,
            )
            commands_lines.append(cmd_code)

        return "\n".join(commands_lines)

    def _generate_print_procedure(self) -> str:
        """Generate Печать procedure for PrintForm type."""
        handlers_lines = []

        for cmd in self.config.commands:
            handler = BSP_PRINT_HANDLER_TEMPLATE.format(
                cmd_id=cmd.id,
                title_ru=cmd.title_ru,
                title_uk=cmd.title_uk or cmd.title_ru,
                title_en=cmd.title_en or cmd.title_ru,
            )
            handlers_lines.append(handler)

        return BSP_PRINT_PROCEDURE_TEMPLATE.format(
            print_handlers="\n".join(handlers_lines)
        )

    def _combine_handlers(self) -> str:
        """Combine user handlers with generated stubs."""
        parts = []

        # Generate stubs for print functions (if not provided by user)
        if self.config.type == "PrintForm":
            for cmd in self.config.commands:
                handler_name = f"Печать{cmd.id}"

                # Check if user provided this handler
                if handler_name not in self.user_handlers:
                    stub = BSP_PRINT_STUB_TEMPLATE.format(
                        cmd_id=cmd.id,
                        template_name=cmd.template_name or f"ПФ_MXL_{cmd.id}",
                    )
                    parts.append(stub)

        # Add user handlers
        if self.user_handlers:
            parts.append(self.user_handlers)

        return "\n\n".join(parts)


# ============================================================================
# PUBLIC API
# ============================================================================

def get_bsp_type_mapping() -> dict:
    """Get YAML type to internal type mapping."""
    return BSP_TYPE_MAPPING_YAML.copy()


def get_bsp_usage_mapping() -> dict:
    """Get YAML usage to internal usage mapping."""
    return BSP_USAGE_MAPPING_YAML.copy()


def generate_bsp_object_module(
    bsp_config: "BSPConfig",
    user_handlers: Optional[str] = None
) -> str:
    """
    Generate BSP-compatible ObjectModule code.

    Args:
        bsp_config: BSP configuration
        user_handlers: Optional user-provided handler code

    Returns:
        str: BSL code for ObjectModule.bsl
    """
    generator = BSPGenerator(bsp_config, user_handlers)
    return generator.generate()
