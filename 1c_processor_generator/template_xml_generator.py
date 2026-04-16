"""
XML Generator для Templates (v2.41.0+)

Генерує XML структуру для templates (HTMLDocument, SpreadsheetDocument).
Виділено з generator.py для кращої організації коду.

Структура файлів для template:
    ProcessorName/Templates/TemplateName.xml          # Метадані
    ProcessorName/Templates/TemplateName/Ext/Template.xml  # Формат (Help/Template)
    ProcessorName/Templates/TemplateName/Ext/Template/ru.html  # Контент (HTMLDocument)
    ProcessorName/Templates/TemplateName/Ext/Template/uk.html
    ProcessorName/Templates/TemplateName/Ext/Template/Template.mxl  # Контент (SpreadsheetDocument)
"""

from pathlib import Path
from typing import Optional
from jinja2 import Environment

from .models import Template
from .constants import ENCODING_UTF8_BOM


def generate_template_ext_xml(template: Template) -> str:
    """
    Генерує Ext/Template.xml для template.

    Різні типи templates мають різний XML формат:
    - HTMLDocument: Help format з version="2.11" та Page елементами
    - SpreadsheetDocument: Template format з data елементом

    Args:
        template: Template об'єкт

    Returns:
        XML контент для Ext/Template.xml
    """
    if template.template_type == "HTMLDocument":
        # HTMLDocument використовує формат "Help" з підтримкою 3 мов (ru, uk, en)
        return '''<?xml version="1.0" encoding="UTF-8"?>
<Help xmlns="http://v8.1c.ru/8.3/xcf/extrnprops" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.11">
\t<Page>ru</Page>
\t<Page>uk</Page>
\t<Page>en</Page>
</Help>'''
    elif template.template_type == "SpreadsheetDocument":
        # SpreadsheetDocument - MXL XML записується прямо в Template.xml
        # content_binary містить повний MXL XML з XML declaration
        if template.content_binary:
            return template.content_binary.decode('utf-8')
        else:
            # Fallback якщо немає content
            return '''<?xml version="1.0" encoding="UTF-8"?>
<document xmlns="http://v8.1c.ru/8.2/data/spreadsheet"/>'''
    else:
        # Інші типи використовують generic формат
        return '''<?xml version="1.0" encoding="UTF-8"?>
<Template xmlns="http://v8.1c.ru/8.3/xcf/extfile" xmlns:xr="http://v8.1c.ru/8.3/xcf/readable" format="Packed" formatVersion="15">
\t<data/>
</Template>'''


def write_template_content(
    template: Template,
    content_dir: Path,
    dry_run: bool = False
) -> str:
    """
    Записує контент файли для template.

    Args:
        template: Template об'єкт з content/content_binary
        content_dir: Директорія для контент файлів (Ext/Template/)
        dry_run: Якщо True, не записує файли

    Returns:
        Опис записаних файлів для логу
    """
    if template.template_type == "HTMLDocument":
        # HTMLDocument потребує мовних версій: ru.html, uk.html, en.html
        for lang in ["ru", "uk", "en"]:
            content_file = content_dir / f"{lang}.html"
            if not dry_run:
                content_file.write_text(template.content, encoding="utf-8")
        return f"Template/ru.html, uk.html, en.html ({len(template.content)} bytes)"

    elif template.template_type == "SpreadsheetDocument":
        # SpreadsheetDocument: MXL вбудовано прямо в Template.xml, окремий файл не потрібен
        # Папка Template/ не створюється
        return f"(MXL inline in Template.xml, {len(template.content_binary)} bytes)"

    else:
        # Невідомий тип - записуємо як текст
        content_file = content_dir / "Template.txt"
        if not dry_run:
            content_file.write_text(template.content or "", encoding="utf-8")
        return f"Template/Template.txt ({len(template.content or '')} bytes)"


def generate_template_files(
    template: Template,
    templates_root_dir: Path,
    env: Environment,
    namespaces: str,
    platform_version: str,
    dry_run: bool = False
) -> None:
    """
    Генерує повну структуру файлів для одного template.

    Args:
        template: Template об'єкт
        templates_root_dir: Коренева директорія Templates (ProcessorName/Templates/)
        env: Jinja2 Environment для рендерингу
        namespaces: XML namespaces рядок
        platform_version: Версія платформи 1С
        dry_run: Якщо True, не створює файли/директорії
    """
    template_name = template.name
    print(f"      Template '{template_name}'...")

    # Створити структуру папок:
    # Templates/TemplateName.xml
    # Templates/TemplateName/Ext/Template.xml
    # Templates/TemplateName/Ext/Template/{content files}  (тільки для HTMLDocument)
    template_dir = templates_root_dir / template_name
    template_ext_dir = template_dir / "Ext"
    template_content_dir = template_ext_dir / "Template"

    if not dry_run:
        templates_root_dir.mkdir(parents=True, exist_ok=True)
        template_dir.mkdir(parents=True, exist_ok=True)
        template_ext_dir.mkdir(parents=True, exist_ok=True)
        # Папка Template/ потрібна тільки для HTMLDocument (ru.html, uk.html, en.html)
        if template.template_type == "HTMLDocument":
            template_content_dir.mkdir(parents=True, exist_ok=True)

    # 1. Генерувати TemplateName.xml (метадані макету)
    meta_template = env.get_template("template_meta.xml.j2")
    meta_content = meta_template.render(
        template=template,
        namespaces=namespaces,
        version=platform_version,
    )

    template_meta_xml = templates_root_dir / f"{template_name}.xml"
    if not dry_run:
        template_meta_xml.write_text(meta_content, encoding=ENCODING_UTF8_BOM)
    print(f"         {'📄' if dry_run else '✅'} {template_meta_xml.name}")

    # 2. Генерувати Ext/Template.xml (формат залежить від типу)
    ext_template_xml = template_ext_dir / "Template.xml"
    ext_xml_content = generate_template_ext_xml(template)
    if not dry_run:
        ext_template_xml.write_text(ext_xml_content, encoding=ENCODING_UTF8_BOM)

    # 3. Записати контент файли
    content_description = write_template_content(template, template_content_dir, dry_run)
    print(f"         {'📄' if dry_run else '✅'} {content_description}")


def generate_all_templates(
    templates: list,
    processor_dir: Path,
    env: Environment,
    namespaces: str,
    platform_version: str,
    dry_run: bool = False
) -> None:
    """
    Генерує всі templates для processor.

    Args:
        templates: Список Template об'єктів
        processor_dir: Директорія processor (ProcessorName/ProcessorName/)
        env: Jinja2 Environment для рендерингу
        namespaces: XML namespaces рядок
        platform_version: Версія платформи 1С
        dry_run: Якщо True, не створює файли/директорії
    """
    if not templates:
        return

    print(f"\n   Generating templates...")

    templates_root_dir = processor_dir / "Templates"

    for template in templates:
        generate_template_files(
            template=template,
            templates_root_dir=templates_root_dir,
            env=env,
            namespaces=namespaces,
            platform_version=platform_version,
            dry_run=dry_run
        )

    print(f"      Templates generated: {len(templates)}")
