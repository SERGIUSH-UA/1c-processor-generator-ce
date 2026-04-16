"""
BSL Generator для Templates automation (v2.41.0+)

Генерує BSL helper функції для templates з placeholders.
"""

from typing import List, Optional
from .models import Processor, Template, TemplatePlaceholder


def generate_template_helpers(processor: Processor) -> str:
    """
    Генерує BSL helper функції для всіх templates з placeholders.

    Для кожного template з placeholders генерується функція:
        ПолучитьТекстМакета{TemplateName}()

    Args:
        processor: Processor об'єкт з templates

    Returns:
        BSL код helper функцій (або порожній рядок якщо немає templates з placeholders)

    Example output:
        &НаСервере
        Функция ПолучитьТекстМакетаEmailTemplate()
            Макет = РеквизитФормыВЗначение("Объект").ПолучитьМакет("EmailTemplate");
            Результат = Макет.ПолучитьТекст();

            // Автоматична заміна placeholders
            Результат = СтрЗаменить(Результат, "{{UserName}}", ТекущийПользователь().Имя);
            Результат = СтрЗаменить(Результат, "{{Date}}", Формат(ТекущаяДата(), "ДФ='dd.MM.yyyy'"));

            Возврат Результат;
        КонецФункции

    v2.41.0+
    """
    if not processor.templates:
        return ""

    helpers = []

    for template in processor.templates:
        if not template.placeholders:
            continue

        helper_code = _generate_single_template_helper(template)
        if helper_code:
            helpers.append(helper_code)

    return "\n\n".join(helpers)


def _generate_single_template_helper(template: Template) -> str:
    """
    Генерує BSL helper функцію для одного template.

    Args:
        template: Template об'єкт з placeholders

    Returns:
        BSL код функції
    """
    if not template.placeholders:
        return ""

    function_name = f"ПолучитьТекстМакета{template.name}"

    # Генеруємо рядки СтрЗаменить для кожного placeholder
    replacements = []
    for ph in template.placeholders:
        replacement_value = _get_placeholder_bsl_value(ph)
        replacements.append(
            f'\tРезультат = СтрЗаменить(Результат, "{ph.name}", {replacement_value});'
        )

    replacements_code = "\n".join(replacements)

    # Формуємо повну функцію
    bsl_code = f"""&НаСервере
Функция {function_name}()
\t// Автогенерована функція для template "{template.name}" (v2.41.0+)
\tМакет = РеквизитФормыВЗначение("Объект").ПолучитьМакет("{template.name}");
\tРезультат = Макет.ПолучитьТекст();

\t// Заміна placeholders
{replacements_code}

\tВозврат Результат;
КонецФункции"""

    return bsl_code


def _get_placeholder_bsl_value(placeholder: TemplatePlaceholder) -> str:
    """
    Повертає BSL вираз для значення placeholder.

    Args:
        placeholder: TemplatePlaceholder об'єкт

    Returns:
        BSL вираз (наприклад: "Объект.UserName" або "ТекущаяДата()")
    """
    if placeholder.bsl_value:
        # Використовуємо прямий BSL вираз
        return placeholder.bsl_value
    elif placeholder.attribute:
        # Посилання на атрибут форми/об'єкта
        # Визначаємо чи це атрибут об'єкта (з "Объект.") чи форми
        if "." in placeholder.attribute:
            # Вже містить крапку - використовуємо як є
            return placeholder.attribute
        else:
            # Простий атрибут - додаємо "Объект."
            return f"Объект.{placeholder.attribute}"
    else:
        # Fallback - порожній рядок
        return '""'


def get_template_helper_names(processor: Processor) -> List[str]:
    """
    Повертає список імен helper функцій для templates.

    Корисно для документації та валідації.

    Args:
        processor: Processor об'єкт

    Returns:
        Список імен функцій (наприклад: ["ПолучитьТекстМакетаEmailTemplate"])
    """
    if not processor.templates:
        return []

    names = []
    for template in processor.templates:
        if template.placeholders:
            names.append(f"ПолучитьТекстМакета{template.name}")

    return names
