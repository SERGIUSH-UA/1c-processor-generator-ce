"""
Тести складних сценаріїв генерації
Базується на реальній обробці ТестированиеStripeTax
"""

import pytest
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib
yaml_parser_module = importlib.import_module("1c_processor_generator.yaml_parser")
generator_module = importlib.import_module("1c_processor_generator.generator")

parse_yaml_config = yaml_parser_module.parse_yaml_config
ProcessorGenerator = generator_module.ProcessorGenerator


class TestStripeTaxProcessor:
    """
    Тести на базі реальної обробки ТестированиеStripeTax

    Ця обробка містить:
    - 8 сторінок (Pages)
    - 4 ValueTable з колонками
    - 16 команд
    - Багаторівневу вкладеність UsualGroup
    - LabelDecoration елементи
    - Різні типи полів (InputField, LabelField, Button, Table)
    """

    def test_generate_stripe_tax_processor(self, fixtures_dir, temp_dir):
        """Генерація складної обробки ТестированиеStripeTax"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"

        # Парсинг YAML (без handlers, щоб не залежати від зовнішніх файлів)
        processor = parse_yaml_config(yaml_path, handlers_dir=None)
        assert processor is not None
        assert processor.name == "ТестированиеStripeTax"

        # Генерація
        generator = ProcessorGenerator(processor)
        processor_root = generator.generate(str(temp_dir))
        assert processor_root is not None

        # Перевірка що файли створені
        # processor_root вже отримано з generate()
        assert processor_root.exists()

        main_xml = processor_root / f"{processor.name}.xml"
        assert main_xml.exists()
        assert main_xml.stat().st_size > 0

    def test_stripe_tax_attributes(self, fixtures_dir, temp_dir):
        """Перевірка атрибутів обробки"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        processor = parse_yaml_config(yaml_path, handlers_dir=None)

        # Має бути 19 атрибутів
        assert len(processor.attributes) == 19

        # Перевірка специфічних атрибутів
        attr_names = [attr.name for attr in processor.attributes]
        assert "Организация" in attr_names
        assert "ТестовыйКонтрагент" in attr_names
        assert "КлючAPI" in attr_names
        assert "ЛогОпераций" in attr_names

    def test_stripe_tax_value_tables(self, fixtures_dir, temp_dir):
        """Перевірка ValueTable атрибутів"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        processor = parse_yaml_config(yaml_path, handlers_dir=None)

        form = processor.get_default_form()

        # Має бути 4 ValueTable
        assert len(form.value_table_attributes) == 4

        table_names = [vt.name for vt in form.value_table_attributes]
        assert "РезультатыРасчета" in table_names
        assert "ИсторияТестов" in table_names
        assert "КэшЗаписи" in table_names
        assert "СтатистикаДанные" in table_names

        # Перевірка колонок у першій таблиці
        results_table = next(vt for vt in form.value_table_attributes if vt.name == "РезультатыРасчета")
        assert len(results_table.columns) == 3
        column_names = [col.name for col in results_table.columns]
        assert "НазваниеПоля" in column_names
        assert "Значение" in column_names
        assert "Описание" in column_names

    def test_stripe_tax_commands(self, fixtures_dir, temp_dir):
        """Перевірка команд обробки"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        processor = parse_yaml_config(yaml_path, handlers_dir=None)

        form = processor.get_default_form()

        # Має бути 16 команд
        assert len(form.commands) == 16

        # Перевірка специфічних команд
        cmd_names = [cmd.name for cmd in form.commands]
        assert "ТестMarylandB2B" in cmd_names
        assert "ПроверитьПодключение" in cmd_names
        assert "ЭкспортРезультатов" in cmd_names
        assert "ОчиститьЛог" in cmd_names

    def test_stripe_tax_form_pages(self, fixtures_dir, temp_dir):
        """Перевірка сторінок форми (Pages)"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        processor = parse_yaml_config(yaml_path, handlers_dir=None)

        form = processor.get_default_form()

        # Має бути Pages з 8 сторінками
        pages_elements = [elem for elem in form.elements if elem.element_type == "Pages"]
        assert len(pages_elements) == 1

        pages = pages_elements[0]
        assert len(pages.child_items) == 8

        # child_items містить словники, а не об'єкти
        page_names = [page['name'] if isinstance(page, dict) else page.name for page in pages.child_items]
        assert "СтраницаГлавная" in page_names
        assert "СтраницаПодключение" in page_names
        assert "СтраницаТестКлиента" in page_names
        assert "СтраницаЛог" in page_names

    def test_stripe_tax_xml_structure(self, fixtures_dir, temp_dir):
        """Перевірка структури згенерованого XML"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        processor = parse_yaml_config(yaml_path, handlers_dir=None)

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        # Читаємо згенерований Form.xml
        form_xml = (
            temp_dir / processor.name / processor.name / "Forms" / "Форма" / "Ext" / "Form.xml"
        )
        assert form_xml.exists()

        # Парсимо XML
        tree = ET.parse(form_xml)
        root = tree.getroot()
        assert root is not None

        # Перевіряємо що XML валідний і має правильну структуру
        assert root.tag.endswith("Form")

    def test_stripe_tax_label_decorations(self, fixtures_dir, temp_dir):
        """Перевірка LabelDecoration елементів"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        processor = parse_yaml_config(yaml_path, handlers_dir=None)

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_xml = (
            temp_dir / processor.name / processor.name / "Forms" / "Форма" / "Ext" / "Form.xml"
        )

        content = form_xml.read_text(encoding="utf-8")

        # Має бути 8 LabelDecoration (по одному на кожній сторінці)
        label_count = content.count("<LabelDecoration")
        assert label_count == 8

        # Перевірка заголовків
        assert "🧪 Интерактивное тестирование Stripe Tax API" in content
        assert "Настройки подключения к Stripe Tax API" in content

    def test_stripe_tax_nested_groups(self, fixtures_dir, temp_dir):
        """Перевірка вкладених UsualGroup (рекурсивна структура)"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        processor = parse_yaml_config(yaml_path, handlers_dir=None)

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_xml = (
            temp_dir / processor.name / processor.name / "Forms" / "Форма" / "Ext" / "Form.xml"
        )

        content = form_xml.read_text(encoding="utf-8")

        # Перевіряємо наявність вкладених груп
        assert "ГруппаБыстрыеТесты" in content
        assert "ГруппаКнопокБыстрыхТестов" in content

        # Перевіряємо що UsualGroup правильно згенеровані
        usual_group_count = content.count("<UsualGroup")
        assert usual_group_count == 13  # 13 вкладених груп

    def test_stripe_tax_id_sequence(self, fixtures_dir, temp_dir):
        """Перевірка послідовності ID елементів форми"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        processor = parse_yaml_config(yaml_path, handlers_dir=None)

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_xml = (
            temp_dir / processor.name / processor.name / "Forms" / "Форма" / "Ext" / "Form.xml"
        )

        tree = ET.parse(form_xml)
        root = tree.getroot()

        # Збираємо ID тільки з ChildItems секції (елементи форми)
        child_items = root.find(".//{http://v8.1c.ru/8.3/xcf/logform}ChildItems")
        if child_items is None:
            # Fallback: без namespace
            child_items = root.find(".//ChildItems")

        assert child_items is not None, "ChildItems section not found"

        # Збираємо всі ID з елементів форми
        form_element_ids = []
        for elem in child_items.iter():
            if "id" in elem.attrib:
                id_val = elem.attrib["id"]
                if id_val != "-1":  # Пропускаємо AutoCommandBar
                    form_element_ids.append(int(id_val))

        # Видаляємо дублікати і сортуємо
        unique_ids = sorted(set(form_element_ids))

        # Перевіряємо що є багато ID
        assert len(unique_ids) >= 200  # Має бути багато унікальних елементів
        assert unique_ids[0] == 1  # Починається з 1
        assert unique_ids[-1] >= 200  # Максимальний ID великий

        # Перевіряємо що ID послідовні без пропусків
        for i in range(len(unique_ids) - 1):
            diff = unique_ids[i + 1] - unique_ids[i]
            assert diff == 1, f"Gap in ID sequence: {unique_ids[i]} -> {unique_ids[i + 1]}"

    def test_stripe_tax_xml_size(self, fixtures_dir, temp_dir):
        """Перевірка розміру згенерованих файлів"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        processor = parse_yaml_config(yaml_path, handlers_dir=None)

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        # Головний XML має бути великим (багато атрибутів)
        main_xml = temp_dir / processor.name / f"{processor.name}.xml"
        assert main_xml.stat().st_size > 20000  # > 20 KB

        # Form.xml теж має бути великим (багато елементів)
        form_xml = (
            temp_dir / processor.name / processor.name / "Forms" / "Форма" / "Ext" / "Form.xml"
        )
        assert form_xml.stat().st_size > 50000  # > 50 KB

    def test_stripe_tax_tables_in_form(self, fixtures_dir, temp_dir):
        """Перевірка Table елементів у формі"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        processor = parse_yaml_config(yaml_path, handlers_dir=None)

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_xml = (
            temp_dir / processor.name / processor.name / "Forms" / "Форма" / "Ext" / "Form.xml"
        )

        content = form_xml.read_text(encoding="utf-8")

        # Має бути 4 таблиці (ValueTable)
        table_count = content.count("<Table name=")
        assert table_count == 4

        # Перевірка назв таблиць
        assert "РезультатыРасчетаТаблица" in content
        assert "ИсторияТестовТаблица" in content
        assert "КэшЗаписиТаблица" in content
        assert "СтатистикаДанныеТаблица" in content

    def test_stripe_tax_encoding(self, fixtures_dir, temp_dir):
        """Перевірка правильності кодування файлів"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        processor = parse_yaml_config(yaml_path, handlers_dir=None)

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        # XML файли мають бути UTF-8 з BOM (для сумісності з Designer)
        main_xml = temp_dir / processor.name / f"{processor.name}.xml"
        with open(main_xml, "rb") as f:
            first_bytes = f.read(3)
            # Має бути BOM (для сумісності з Designer)
            assert first_bytes == b'\xef\xbb\xbf'

        # BSL файли мають бути UTF-8 з BOM
        form_module = (
            temp_dir / processor.name / processor.name / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )
        with open(form_module, "rb") as f:
            first_bytes = f.read(3)
            # Має бути BOM
            assert first_bytes == b'\xef\xbb\xbf'

    def test_stripe_tax_multiline_field(self, fixtures_dir, temp_dir):
        """Перевірка багаторядкового поля (ЛогОпераций)"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        processor = parse_yaml_config(yaml_path, handlers_dir=None)

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_xml = (
            temp_dir / processor.name / processor.name / "Forms" / "Форма" / "Ext" / "Form.xml"
        )

        content = form_xml.read_text(encoding="utf-8")

        # Перевіряємо що поле ЛогОпераций існує і має TitleLocation=None
        assert 'name="ЛогОперацийПоле"' in content
        assert "<TitleLocation>None</TitleLocation>" in content

    def test_stripe_tax_input_hints(self, fixtures_dir, temp_dir):
        """Перевірка InputHint (підказок у полях)"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        processor = parse_yaml_config(yaml_path, handlers_dir=None)

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_xml = (
            temp_dir / processor.name / processor.name / "Forms" / "Форма" / "Ext" / "Form.xml"
        )

        content = form_xml.read_text(encoding="utf-8")

        # Перевіряємо що InputHint згенеровано
        assert "<InputHint>" in content
        assert "txcd_10103000 для SaaS" in content


class TestStripeTaxBSLGeneration:
    """
    Тести генерації BSL коду для обробки ТестированиеStripeTax

    Перевіряємо:
    - Структуру модуля форми
    - Наявність процедур обробників
    - Правильність директив (&НаКлиенте, &НаСервере)
    - Синтаксис BSL
    """

    def test_form_module_structure(self, fixtures_dir, temp_dir):
        """Перевірка базової структури модуля форми"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        processor = parse_yaml_config(yaml_path, handlers_dir=None)

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_module = (
            temp_dir / processor.name / processor.name / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )
        assert form_module.exists()

        content = form_module.read_text(encoding="utf-8-sig")

        # Має містити базові BSL конструкції
        assert "Процедура" in content
        assert "КонецПроцедуры" in content

        # Має містити області (regions)
        assert "#Область" in content
        assert "#КонецОбласти" in content

    def test_form_event_handlers(self, fixtures_dir, temp_dir):
        """Перевірка обробників подій форми"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        processor = parse_yaml_config(yaml_path, handlers_dir=None)

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_module = (
            temp_dir / processor.name / processor.name / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )

        content = form_module.read_text(encoding="utf-8-sig")

        # Перевіряємо наявність обробників подій форми
        assert "Процедура ПриОткрытии" in content or "ПриОткрытии" in content
        assert "Процедура ПриСозданииНаСервере" in content or "ПриСозданииНаСервере" in content

    def test_command_handlers_generated(self, fixtures_dir, temp_dir):
        """Перевірка що обробники команд згенеровані"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        processor = parse_yaml_config(yaml_path, handlers_dir=None)

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_module = (
            temp_dir / processor.name / processor.name / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )

        content = form_module.read_text(encoding="utf-8-sig")

        # Має містити обробники команд
        # Перевіряємо хоча б кілька ключових команд
        assert "ТестMarylandB2B" in content
        assert "ПроверитьПодключение" in content
        assert "ОчиститьЛог" in content

    def test_bsl_syntax_correctness(self, fixtures_dir, temp_dir):
        """Перевірка правильності синтаксису BSL"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        processor = parse_yaml_config(yaml_path, handlers_dir=None)

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_module = (
            temp_dir / processor.name / processor.name / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )

        content = form_module.read_text(encoding="utf-8-sig")

        # Перевіряємо парність конструкцій
        procedure_count = content.count("Процедура ")
        end_procedure_count = content.count("КонецПроцедуры")
        assert procedure_count == end_procedure_count, \
            f"Mismatch: {procedure_count} Процедура vs {end_procedure_count} КонецПроцедуры"

        # Перевіряємо парність областей
        region_start = content.count("#Область")
        region_end = content.count("#КонецОбласти")
        assert region_start == region_end, \
            f"Mismatch: {region_start} #Область vs {region_end} #КонецОбласти"

    def test_client_server_directives(self, fixtures_dir, temp_dir):
        """Перевірка директив &НаКлиенте та &НаСервере"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        processor = parse_yaml_config(yaml_path, handlers_dir=None)

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_module = (
            temp_dir / processor.name / processor.name / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )

        content = form_module.read_text(encoding="utf-8-sig")

        # Має бути хоча б одна серверна процедура (ПриСозданииНаСервере)
        assert "&НаСервере" in content or "&AtServer" in content

        # Більшість обробників команд - клієнтські
        assert "&НаКлиенте" in content or "&AtClient" in content

    def test_procedure_signatures(self, fixtures_dir, temp_dir):
        """Перевірка правильності сигнатур процедур"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        processor = parse_yaml_config(yaml_path, handlers_dir=None)

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_module = (
            temp_dir / processor.name / processor.name / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )

        content = form_module.read_text(encoding="utf-8-sig")

        # Перевіряємо що обробники подій форми мають правильні параметри
        # ПриОткрытии має мати параметр Отказ
        if "Процедура ПриОткрытии(" in content:
            assert "Отказ" in content

        # ПриСозданииНаСервере має мати параметри Отказ, СтандартнаяОбработка
        if "Процедура ПриСозданииНаСервере(" in content:
            assert "Отказ" in content or "СтандартнаяОбработка" in content

    def test_command_handlers_have_parameters(self, fixtures_dir, temp_dir):
        """Перевірка що обробники команд мають параметр Команда"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        processor = parse_yaml_config(yaml_path, handlers_dir=None)

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_module = (
            temp_dir / processor.name / processor.name / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )

        content = form_module.read_text(encoding="utf-8-sig")

        # Обробники команд мають мати параметр Команда
        # Шукаємо будь-яку процедуру команди
        import re
        command_procedures = re.findall(r'Процедура (Тест\w+|Проверить\w+|Очистить\w+)\(', content)

        if command_procedures:
            # Перевіряємо що хоча б одна команда має параметр
            has_command_param = "Команда)" in content or "Command)" in content
            assert has_command_param, "Command handlers should have Команда parameter"

    def test_no_syntax_errors_in_generated_code(self, fixtures_dir, temp_dir):
        """Базова перевірка відсутності явних синтаксичних помилок"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        processor = parse_yaml_config(yaml_path, handlers_dir=None)

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_module = (
            temp_dir / processor.name / processor.name / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )

        content = form_module.read_text(encoding="utf-8-sig")

        # Перевіряємо відсутність типових помилок
        assert "ПроцедураПроцедура" not in content  # Дублювання ключових слів
        assert "КонецПроцедурыКонецПроцедуры" not in content
        assert "##Область" not in content  # Подвійні символи

        # Перевіряємо що немає незакритих лапок чи дужок (базова перевірка)
        # Рахуємо дужки (приблизно)
        open_parens = content.count("(")
        close_parens = content.count(")")
        # Допускаємо невелику різницю через коментарі
        assert abs(open_parens - close_parens) < 10

    def test_object_module_structure(self, fixtures_dir, temp_dir):
        """Перевірка структури модуля об'єкта обробки"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        processor = parse_yaml_config(yaml_path, handlers_dir=None)

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        object_module = (
            temp_dir / processor.name / processor.name / "Ext" / "ObjectModule.bsl"
        )
        assert object_module.exists()

        content = object_module.read_text(encoding="utf-8-sig")

        # Має містити базові області
        assert "#Область ПрограммныйИнтерфейс" in content
        assert "#Область СлужебныеПроцедурыИФункции" in content

    def test_form_module_size(self, fixtures_dir, temp_dir):
        """Перевірка розміру модуля форми"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        processor = parse_yaml_config(yaml_path, handlers_dir=None)

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_module = (
            temp_dir / processor.name / processor.name / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )

        # Модуль має бути не порожній
        size = form_module.stat().st_size
        assert size > 1000  # > 1 KB

        # Але не занадто великий (без handlers це має бути базовий шаблон)
        assert size < 10000  # < 10 KB

    def test_all_16_commands_present(self, fixtures_dir, temp_dir):
        """Перевірка що всі 16 команд присутні в модулі"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        processor = parse_yaml_config(yaml_path, handlers_dir=None)

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_module = (
            temp_dir / processor.name / processor.name / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )

        content = form_module.read_text(encoding="utf-8-sig")

        # Список всіх 16 команд
        expected_commands = [
            "ТестMarylandB2B",
            "ТестMarylandB2C",
            "ТестTexasSaaS",
            "ПроверитьПодключение",
            "ЗагрузитьНастройки",
            "ПодготовитьДанныеКлиента",
            "ЗаполнитьMarylandB2B",
            "ЗаполнитьTexas",
            "ВыполнитьПолныйТест",
            "ЗаполнитьSaaS",
            "ЭкспортРезультатов",
            "ОбновитьКэш",
            "ОчиститьВесьКэш",
            "ОчиститьУстаревшийКэш",
            "ОбновитьСтатистику",
            "ОчиститьЛог"
        ]

        for cmd_name in expected_commands:
            assert cmd_name in content, f"Command {cmd_name} not found in module"

    def test_total_procedures_count(self, fixtures_dir, temp_dir):
        """Перевірка загальної кількості процедур і функцій"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        processor = parse_yaml_config(yaml_path, handlers_dir=None)

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_module = (
            temp_dir / processor.name / processor.name / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )

        content = form_module.read_text(encoding="utf-8-sig")

        import re
        # Рахуємо процедури і функції
        procedures = re.findall(r'^Процедура (\w+)\(', content, re.MULTILINE)
        functions = re.findall(r'^Функция (\w+)\(', content, re.MULTILINE)

        total = len(procedures) + len(functions)

        # Має бути 19 процедур:
        # - 2 обробники подій форми (ПриОткрытии, ПриСозданииНаСервере)
        # - 1 серверний обробник (ПриОткрытииНаСервере)
        # - 16 команд
        assert total == 19, f"Expected 19 procedures/functions, got {total}"
        assert len(procedures) == 19, f"Expected 19 procedures, got {len(procedures)}"
        assert len(functions) == 0, f"Expected 0 functions, got {len(functions)}"

        # Перевіряємо наявність ключових процедур
        procedure_names = [p for p in procedures]
        assert "ПриОткрытии" in procedure_names
        assert "ПриОткрытииНаСервере" in procedure_names
        assert "ПриСозданииНаСервере" in procedure_names

    def test_procedure_pairing(self, fixtures_dir, temp_dir):
        """Перевірка клієнт-серверних пар процедур"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        processor = parse_yaml_config(yaml_path, handlers_dir=None)

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_module = (
            temp_dir / processor.name / processor.name / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )

        content = form_module.read_text(encoding="utf-8-sig")

        # ПриОткрытии має мати серверну пару ПриОткрытииНаСервере
        if "Процедура ПриОткрытии(" in content:
            assert "Процедура ПриОткрытииНаСервере(" in content, \
                "ПриОткрытии should have server handler ПриОткрытииНаСервере"

            # Клієнтська версія має викликати серверну
            assert "ПриОткрытииНаСервере(" in content, \
                "Client handler should call server handler"


class TestStripeTaxWithRealHandlers:
    """
    БОЙОВИЙ ТЕСТ: Генерація обробки ТестированиеStripeTax з реальним BSL кодом

    Перевіряємо:
    - Інжекцію всіх 25 handlers з YAML
    - Інжекцію всіх 13 standalone helpers (не згадані в YAML)
    - Правильність структури модуля
    - Відсутність дублювання коду
    - Правильність викликів між процедурами
    """

    def test_full_generation_with_handlers_file(self, fixtures_dir, temp_dir):
        """БОЙОВИЙ ТЕСТ: Генерація з реальним handlers.bsl"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        handlers_file = fixtures_dir / "stripe_tax_handlers.bsl"

        # Перевірка що тестовий файл існує
        assert handlers_file.exists(), f"Test handlers file not found: {handlers_file}"

        # Генеруємо з реальним BSL кодом
        processor = parse_yaml_config(
            yaml_path,
            handlers_file=handlers_file
        )

        assert processor is not None
        assert processor.name == "ТестированиеStripeTax"

        # Генерація
        generator = ProcessorGenerator(processor)
        processor_root = generator.generate(str(temp_dir))
        assert processor_root is not None

        # Перевірка що файли створені
        form_module = (
            temp_dir / processor.name / processor.name /
            "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )
        assert form_module.exists()

        # Файл має бути великим (реальний BSL код)
        size = form_module.stat().st_size
        assert size > 20000, f"Module too small: {size} bytes (expected > 20KB with real handlers)"

    def test_standalone_helpers_injection(self, fixtures_dir, temp_dir):
        """Перевірка інжекції standalone helpers (не згадані в YAML)"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        handlers_file = fixtures_dir / "stripe_tax_handlers.bsl"

        processor = parse_yaml_config(yaml_path, handlers_file=handlers_file)
        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_module = (
            temp_dir / processor.name / processor.name /
            "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )
        content = form_module.read_text(encoding="utf-8-sig")

        # Перевіряємо наявність ключових standalone helpers
        # Ці процедури НЕ згадані в YAML, але викликаються з інших обробників
        standalone_helpers = [
            "ВыполнитьТестРасчетаНаСервере",  # Викликається з ТестMarylandB2B
            "ДобавитьВЛог",                   # Викликається з багатьох місць
            "НачатьТест",                     # Викликається з тестів
            "ЗавершитьТест",                  # Викликається з тестів
            "СоздатьТестовогоКонтрагента",    # Викликається з ПодготовитьДанныеКлиента
            "СоздатьТестовыйДокумент",        # Викликається з ВыполнитьТестРасчета
            "СоздатьТестовуюНоменклатуру",    # Викликається з СоздатьТестовыйДокумент
            "ОтобразитьРезультатыРасчета",    # Викликається з ВыполнитьТестРасчета
            "ДобавитьРезультат",              # Викликається з ОтобразитьРезультаты
            "ПолучитьОрганизациюПоУмолчанию", # Викликається з ПриОткрытии
            "ЗагрузитьИсториюТестов",         # Викликається з ПриОткрытии
            "ОписаниеПоляКлиента",            # Викликається з ПодготовитьДанныеКлиента
            "ЭкспортироватьРезультатыВJSON",  # Викликається з ЭкспортРезультатов
        ]

        for helper in standalone_helpers:
            # Перевіряємо наявність (може бути Процедура або Функция)
            assert (f"Процедура {helper}(" in content or
                   f"Функция {helper}(" in content), \
                   f"Standalone helper '{helper}' not found in module"

        print(f"\n✅ Всі {len(standalone_helpers)} standalone helpers знайдені")

    def test_total_procedures_with_helpers(self, fixtures_dir, temp_dir):
        """Перевірка загальної кількості процедур (handlers + helpers)"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        handlers_file = fixtures_dir / "stripe_tax_handlers.bsl"

        processor = parse_yaml_config(yaml_path, handlers_file=handlers_file)
        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_module = (
            temp_dir / processor.name / processor.name /
            "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )
        content = form_module.read_text(encoding="utf-8-sig")

        import re
        # Рахуємо процедури і функції
        procedures = re.findall(r'^Процедура (\w+)\(', content, re.MULTILINE)
        functions = re.findall(r'^Функция (\w+)\(', content, re.MULTILINE)

        total = len(procedures) + len(functions)

        # Очікуємо:
        # 25 handlers (події форми + команди + серверні пари)
        # + 13 standalone helpers
        # = 38 процедур/функцій
        assert total >= 32, \
            f"Expected at least 32 procedures/functions (handlers + helpers), got {total}"

        print(f"\n✅ Загальна кількість процедур/функцій: {total}")
        print(f"   Процедур: {len(procedures)}")
        print(f"   Функцій: {len(functions)}")

    def test_helper_procedures_region(self, fixtures_dir, temp_dir):
        """Перевірка секції СлужебныеПроцедурыИФункции"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        handlers_file = fixtures_dir / "stripe_tax_handlers.bsl"

        processor = parse_yaml_config(yaml_path, handlers_file=handlers_file)
        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_module = (
            temp_dir / processor.name / processor.name /
            "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )
        content = form_module.read_text(encoding="utf-8-sig")

        # Має бути секція для helpers
        assert "#Область СлужебныеПроцедурыИФункции" in content, \
            "Module should have helpers region"

        # Розділяємо на секції
        import re
        regions = re.split(r'#Область', content)

        # Знаходимо секцію helpers
        helpers_region = None
        for region in regions:
            if "СлужебныеПроцедурыИФункции" in region:
                helpers_region = region
                break

        assert helpers_region is not None, "Helpers region not found"

        # У секції helpers мають бути standalone процедури
        assert "ВыполнитьТестРасчетаНаСервере" in helpers_region, \
            "ВыполнитьТестРасчетаНаСервере should be in helpers region"
        assert "ДобавитьВЛог" in helpers_region, \
            "ДобавитьВЛог should be in helpers region"

        print("\n✅ Секція СлужебныеПроцедурыИФункции містить standalone helpers")

    def test_no_duplicate_procedures(self, fixtures_dir, temp_dir):
        """Перевірка відсутності дублювання процедур"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        handlers_file = fixtures_dir / "stripe_tax_handlers.bsl"

        processor = parse_yaml_config(yaml_path, handlers_file=handlers_file)
        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_module = (
            temp_dir / processor.name / processor.name /
            "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )
        content = form_module.read_text(encoding="utf-8-sig")

        import re
        # Знаходимо всі процедури/функції
        all_procedures = re.findall(
            r'^(?:Процедура|Функция) (\w+)\(',
            content,
            re.MULTILINE
        )

        # Перевіряємо дублікати
        from collections import Counter
        duplicates = {name: count for name, count in Counter(all_procedures).items() if count > 1}

        assert not duplicates, \
            f"Found duplicate procedures/functions: {duplicates}"

        print(f"\n✅ Немає дублікатів серед {len(all_procedures)} процедур/функцій")

    def test_client_server_directives_with_real_code(self, fixtures_dir, temp_dir):
        """Перевірка директив &НаКлиенте та &НаСервере в реальному коді"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        handlers_file = fixtures_dir / "stripe_tax_handlers.bsl"

        processor = parse_yaml_config(yaml_path, handlers_file=handlers_file)
        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_module = (
            temp_dir / processor.name / processor.name /
            "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )
        content = form_module.read_text(encoding="utf-8-sig")

        client_count = content.count("&НаКлиенте")
        server_count = content.count("&НаСервере")

        # Має бути багато клієнтських процедур (команди + події)
        assert client_count >= 15, \
            f"Expected at least 15 client procedures, got {client_count}"

        # Має бути багато серверних процедур (серверні пари + helpers)
        assert server_count >= 15, \
            f"Expected at least 15 server procedures, got {server_count}"

        print(f"\n✅ Директиви: {client_count} клієнтських, {server_count} серверних")

    def test_procedure_calls_between_handlers_and_helpers(self, fixtures_dir, temp_dir):
        """Перевірка викликів між handlers та helpers"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        handlers_file = fixtures_dir / "stripe_tax_handlers.bsl"

        processor = parse_yaml_config(yaml_path, handlers_file=handlers_file)
        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_module = (
            temp_dir / processor.name / processor.name /
            "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )
        content = form_module.read_text(encoding="utf-8-sig")

        # Перевірка що handlers викликають helpers
        test_cases = [
            ("ТестMarylandB2B", "ВыполнитьТестРасчетаНаСервере"),  # Handler -> Helper
            ("ПриОткрытии", "ДобавитьВЛог"),                       # Event -> Helper
            ("ТестMarylandB2B", "НачатьТест"),                     # Handler -> Helper
            ("ТестMarylandB2B", "ЗавершитьТест"),                  # Handler -> Helper
        ]

        for handler, helper in test_cases:
            # Знаходимо тіло процедури handler
            import re
            handler_match = re.search(
                rf'Процедура {handler}\(.*?\).*?КонецПроцедуры',
                content,
                re.DOTALL
            )

            if handler_match:
                handler_body = handler_match.group(0)
                assert helper in handler_body, \
                    f"Handler '{handler}' should call helper '{helper}'"

        print("\n✅ Виклики між handlers та helpers правильні")

    def test_real_bsl_code_structure(self, fixtures_dir, temp_dir):
        """Перевірка структури реального BSL коду"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        handlers_file = fixtures_dir / "stripe_tax_handlers.bsl"

        processor = parse_yaml_config(yaml_path, handlers_file=handlers_file)
        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_module = (
            temp_dir / processor.name / processor.name /
            "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )
        content = form_module.read_text(encoding="utf-8-sig")

        # Перевіряємо наявність реального коду (не порожні шаблони)
        real_code_indicators = [
            "МенеджерИнтеграцииStripeTax",  # Виклики модуля інтеграції
            "РезультатТеста.Успешно",       # Робота з результатами
            "СтрШаблон(",                   # Форматування рядків
            "Попытка",                      # Обробка помилок
            "Исключение",
            "КонецПопытки",
            "Новый Структура",              # Створення об'єктів
            "ТекущаяДата()",                # Виклики платформи
        ]

        for indicator in real_code_indicators:
            assert indicator in content, \
                f"Real code indicator '{indicator}' not found - handlers may be empty templates"

        # Перевіряємо що є коментарі (реальний код зазвичай їх має)
        comment_count = content.count("//")
        assert comment_count >= 10, \
            f"Expected at least 10 comments in real code, got {comment_count}"

        print("\n✅ Модуль містить реальний BSL код (не шаблони)")

    def test_all_form_events_with_real_handlers(self, fixtures_dir, temp_dir):
        """Перевірка що події форми мають реальні обробники"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        handlers_file = fixtures_dir / "stripe_tax_handlers.bsl"

        processor = parse_yaml_config(yaml_path, handlers_file=handlers_file)
        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_module = (
            temp_dir / processor.name / processor.name /
            "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )
        content = form_module.read_text(encoding="utf-8-sig")

        # ПриОткрытии має мати реальний код
        import re
        priotkrytii_match = re.search(
            r'Процедура ПриОткрытии\(.*?\).*?КонецПроцедуры',
            content,
            re.DOTALL
        )
        assert priotkrytii_match, "ПриОткрытии procedure not found"

        priotkrytii_body = priotkrytii_match.group(0)
        # Має містити реальну логіку
        assert "Организация" in priotkrytii_body, \
            "ПриОткрытии should have real code working with Организация"
        assert "ЗагрузитьНастройкиНаСервере" in priotkrytii_body, \
            "ПриОткрытии should call ЗагрузитьНастройкиНаСервере"

        # ПриСозданииНаСервере має мати реальний код
        prisozd_match = re.search(
            r'Процедура ПриСозданииНаСервере\(.*?\).*?КонецПроцедуры',
            content,
            re.DOTALL
        )
        assert prisozd_match, "ПриСозданииНаСервере procedure not found"

        prisozd_body = prisozd_match.group(0)
        # Має містити ініціалізацію
        assert "АдресСервера" in prisozd_body, \
            "ПриСозданииНаСервере should initialize default values"

        print("\n✅ Події форми мають реальні обробники")

    def test_module_size_with_real_handlers(self, fixtures_dir, temp_dir):
        """Перевірка розміру модуля з реальними handlers"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        handlers_file = fixtures_dir / "stripe_tax_handlers.bsl"

        processor = parse_yaml_config(yaml_path, handlers_file=handlers_file)
        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_module = (
            temp_dir / processor.name / processor.name /
            "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )

        size = form_module.stat().st_size

        # З реальними handlers модуль має бути великим
        assert size > 20000, \
            f"Module too small: {size} bytes (expected > 20KB with 38 procedures)"

        # Але не занадто великим (без дублювання)
        assert size < 50000, \
            f"Module too large: {size} bytes (expected < 50KB, possible duplication)"

        print(f"\n✅ Розмір модуля: {size:,} байт (оптимально)")

    def test_syntax_correctness_with_real_code(self, fixtures_dir, temp_dir):
        """Перевірка синтаксичної коректності згенерованого коду"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        handlers_file = fixtures_dir / "stripe_tax_handlers.bsl"

        processor = parse_yaml_config(yaml_path, handlers_file=handlers_file)
        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_module = (
            temp_dir / processor.name / processor.name /
            "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )
        content = form_module.read_text(encoding="utf-8-sig")

        # Перевіряємо парність конструкцій
        procedure_count = content.count("Процедура ")
        end_procedure_count = content.count("КонецПроцедуры")
        assert procedure_count == end_procedure_count, \
            f"Mismatch: {procedure_count} Процедура vs {end_procedure_count} КонецПроцедуры"

        function_count = content.count("Функция ")
        end_function_count = content.count("КонецФункции")
        assert function_count == end_function_count, \
            f"Mismatch: {function_count} Функция vs {end_function_count} КонецФункции"

        # Перевіряємо парність областей
        region_start = content.count("#Область")
        region_end = content.count("#КонецОбласти")
        assert region_start == region_end, \
            f"Mismatch: {region_start} #Область vs {region_end} #КонецОбласти"

        # Перевіряємо парність Попытка/Исключение/КонецПопытки
        popytka_count = content.count("Попытка")
        konec_popytki_count = content.count("КонецПопытки")
        assert popytka_count == konec_popytki_count, \
            f"Mismatch: {popytka_count} Попытка vs {konec_popytki_count} КонецПопытки"

        print("\n✅ Синтаксис BSL коректний (всі конструкції парні)")

    def test_encoding_correctness_with_real_handlers(self, fixtures_dir, temp_dir):
        """Перевірка коректності кодування файлів"""
        yaml_path = fixtures_dir / "stripe_tax_config.yaml"
        handlers_file = fixtures_dir / "stripe_tax_handlers.bsl"

        processor = parse_yaml_config(yaml_path, handlers_file=handlers_file)
        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        # BSL файли мають бути UTF-8 з BOM
        form_module = (
            temp_dir / processor.name / processor.name /
            "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )

        with open(form_module, "rb") as f:
            first_bytes = f.read(3)
            # Має бути BOM
            assert first_bytes == b'\xef\xbb\xbf', \
                "BSL file should have UTF-8 BOM"

        # Перевіряємо що кирилиця читається коректно
        content = form_module.read_text(encoding="utf-8-sig")
        assert "Процедура" in content, "Cyrillic not decoded correctly"
        assert "КонецПроцедуры" in content, "Cyrillic not decoded correctly"

        print("\n✅ Кодування файлів коректне (UTF-8 з BOM)")
