"""
Integration тести для generator.py
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib
generator_module = importlib.import_module("1c_processor_generator.generator")

ProcessorGenerator = generator_module.ProcessorGenerator
create_minimal_processor = generator_module.create_minimal_processor


class TestProcessorGenerator:
    """Тести для ProcessorGenerator"""

    def test_generator_creation(self, simple_processor):
        """Створення генератора"""
        generator = ProcessorGenerator(simple_processor)
        assert generator.processor == simple_processor
        assert generator.env is not None

    def test_validate_simple_processor(self, simple_processor):
        """Валідація простого процесора"""
        generator = ProcessorGenerator(simple_processor)
        is_valid = generator.validate()
        assert is_valid

    def test_validate_complex_processor(self, complex_processor):
        """Валідація складного процесора"""
        generator = ProcessorGenerator(complex_processor)
        is_valid = generator.validate()
        assert is_valid

    def test_generate_simple_processor(self, simple_processor, temp_dir):
        """Генерація простого процесора"""
        generator = ProcessorGenerator(simple_processor)
        result = generator.generate(str(temp_dir))

        assert result is not None
        assert isinstance(result, Path)

        # Перевіряємо структуру файлів
        processor_root = temp_dir / simple_processor.name
        assert processor_root.exists()

        # Перевіряємо головний XML файл
        main_xml = processor_root / f"{simple_processor.name}.xml"
        assert main_xml.exists()

        # Перевіряємо структуру директорій
        processor_dir = processor_root / simple_processor.name
        assert processor_dir.exists()

        ext_dir = processor_dir / "Ext"
        assert ext_dir.exists()

        object_module = ext_dir / "ObjectModule.bsl"
        assert object_module.exists()

    def test_generate_complex_processor(self, complex_processor, temp_dir):
        """Генерація складного процесора"""
        generator = ProcessorGenerator(complex_processor)
        result = generator.generate(str(temp_dir))

        assert result is not None
        assert isinstance(result, Path)

        processor_root = temp_dir / complex_processor.name
        assert processor_root.exists()

    def test_generate_form_files(self, simple_processor, temp_dir):
        """Генерація файлів форми"""
        generator = ProcessorGenerator(simple_processor)
        generator.generate(str(temp_dir))

        processor_root = temp_dir / simple_processor.name
        processor_dir = processor_root / simple_processor.name
        forms_dir = processor_dir / "Forms"

        # Форма.xml (метадані форми)
        form_meta_xml = forms_dir / "Форма.xml"
        assert form_meta_xml.exists()

        # Form.xml (структура форми)
        form_dir = forms_dir / "Форма" / "Ext"
        form_xml = form_dir / "Form.xml"
        assert form_xml.exists()

        # Module.bsl (модуль форми)
        form_module = form_dir / "Form" / "Module.bsl"
        assert form_module.exists()

    def test_form_module_generation(self, simple_processor):
        """Генерація модуля форми"""
        generator = ProcessorGenerator(simple_processor)
        form = simple_processor.get_default_form()
        form_module_code = generator._generate_form_module_code(form)

        assert form_module_code is not None
        assert "#Область" in form_module_code
        assert "ОбработчикиСобытийФормы" in form_module_code
        assert "ОбработчикиКомандФормы" in form_module_code

    def test_prepare_form_elements(self, simple_processor):
        """Підготовка елементів форми"""
        generator = ProcessorGenerator(simple_processor)
        form = simple_processor.get_default_form()
        form_elements, next_id = generator._prepare_form_elements(form)

        assert len(form_elements) > 0
        assert next_id > 1  # ID має бути > 1

        # Перевіряємо що кожен елемент має ID
        for elem in form_elements:
            assert "id" in elem
            assert elem["id"] > 0

    def test_id_sequencing(self, complex_processor):
        """Перевірка послідовності ID"""
        generator = ProcessorGenerator(complex_processor)
        form = complex_processor.get_default_form()
        form_elements, next_id = generator._prepare_form_elements(form)

        ids = [elem["id"] for elem in form_elements]

        # ID мають починатися з 1
        assert min(ids) == 1

        # ID мають бути унікальними
        assert len(ids) == len(set(ids))

    def test_prepare_auto_command_bar(self, simple_processor):
        """Підготовка AutoCommandBar"""
        generator = ProcessorGenerator(simple_processor)
        form = simple_processor.get_default_form()
        form_elements, next_id = generator._prepare_form_elements(form)
        auto_command_bar = generator._prepare_auto_command_bar(next_id, form)

        # AutoCommandBar може бути порожнім для простого процесора
        assert isinstance(auto_command_bar, list)


class TestCreateMinimalProcessor:
    """Тести для create_minimal_processor()"""

    def test_create_minimal_processor(self):
        """Створення мінімального процесора"""
        processor = create_minimal_processor("МинимальныйПроцессор")

        assert processor is not None
        assert processor.name == "МинимальныйПроцессор"
        assert len(processor.attributes) == 1
        assert len(processor.forms) == 1
        assert len(processor.forms[0].elements) == 1

    def test_create_minimal_processor_with_version(self):
        """Створення мінімального процесора з версією платформи"""
        processor = create_minimal_processor("Процесор", platform_version="2.18")

        assert processor.platform_version == "2.18"

    def test_create_minimal_processor_with_version_2_10(self):
        """Створення мінімального процесора з версією 2.10 (для старіших платформ)"""
        processor = create_minimal_processor("Процесор2010", platform_version="2.10")

        assert processor.platform_version == "2.10"
        assert processor.name == "Процесор2010"

    def test_generate_with_custom_version(self, temp_dir):
        """Генерація процесора з кастомною версією (2.10)"""
        processor = create_minimal_processor("ПроцесорВерсия210", platform_version="2.10")
        generator = ProcessorGenerator(processor)
        result = generator.generate(str(temp_dir))

        assert result is not None
        assert isinstance(result, Path)

        # Перевіряємо що версія правильно записана в XML
        processor_root = temp_dir / processor.name
        main_xml = processor_root / f"{processor.name}.xml"
        assert main_xml.exists()

        content = main_xml.read_text(encoding="utf-8")
        assert 'version="2.10"' in content

    def test_generate_minimal_processor(self, temp_dir):
        """Генерація мінімального процесора"""
        processor = create_minimal_processor("МинимальныйПроцессор")
        generator = ProcessorGenerator(processor)
        result = generator.generate(str(temp_dir))

        assert result is not None
        assert isinstance(result, Path)


class TestGeneratorWithBSLHandlers:
    """Тести генератора з BSL обробниками"""

    def test_generate_with_bsl_handlers(self, fixtures_dir, temp_dir):
        """Генерація процесора з BSL обробниками"""
        import importlib
        yaml_parser_module = importlib.import_module("1c_processor_generator.yaml_parser")
        parse_yaml_config = yaml_parser_module.parse_yaml_config

        yaml_path = fixtures_dir / "simple_config.yaml"
        handlers_dir = fixtures_dir / "handlers"
        processor = parse_yaml_config(yaml_path, handlers_dir)

        generator = ProcessorGenerator(processor)
        result = generator.generate(str(temp_dir))

        assert result is not None
        assert isinstance(result, Path)

        # Перевіряємо що BSL код включено в Module.bsl
        processor_root = temp_dir / processor.name
        form_module = (
            processor_root / processor.name / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        )
        assert form_module.exists()

        # Читаємо модуль і перевіряємо наявність обробників
        content = form_module.read_text(encoding="utf-8-sig")
        assert len(content) > 0


class TestXMLGeneration:
    """Тести генерації XML файлів"""

    def test_main_xml_content(self, simple_processor, temp_dir):
        """Перевірка вмісту головного XML файлу"""
        generator = ProcessorGenerator(simple_processor)
        generator.generate(str(temp_dir))

        processor_root = temp_dir / simple_processor.name
        main_xml = processor_root / f"{simple_processor.name}.xml"

        content = main_xml.read_text(encoding="utf-8")

        # Перевіряємо основні елементи
        assert '<?xml version="1.0" encoding="UTF-8"?>' in content
        assert "<MetaDataObject" in content
        assert simple_processor.name in content

    def test_form_xml_content(self, simple_processor, temp_dir):
        """Перевірка вмісту Form.xml"""
        generator = ProcessorGenerator(simple_processor)
        generator.generate(str(temp_dir))

        processor_root = temp_dir / simple_processor.name
        form_xml = (
            processor_root / simple_processor.name / "Forms" / "Форма" / "Ext" / "Form.xml"
        )

        content = form_xml.read_text(encoding="utf-8")

        assert '<?xml version="1.0" encoding="UTF-8"?>' in content
        assert "<Form" in content


class TestEncodingHandling:
    """Тести роботи з кодуванням"""

    def test_xml_files_utf8(self, simple_processor, temp_dir):
        """XML файли мають бути в UTF-8 з BOM (для сумісності з Designer)"""
        generator = ProcessorGenerator(simple_processor)
        generator.generate(str(temp_dir))

        processor_root = temp_dir / simple_processor.name
        main_xml = processor_root / f"{simple_processor.name}.xml"

        # Читаємо в binary mode
        with open(main_xml, "rb") as f:
            content = f.read()

        # Має бути BOM (для сумісності з Designer)
        assert content.startswith(b'\xef\xbb\xbf')

    def test_bsl_files_utf8_bom(self, simple_processor, temp_dir):
        """BSL файли мають бути в UTF-8 з BOM"""
        generator = ProcessorGenerator(simple_processor)
        generator.generate(str(temp_dir))

        processor_root = temp_dir / simple_processor.name
        object_module = processor_root / simple_processor.name / "Ext" / "ObjectModule.bsl"

        # Читаємо в binary mode
        with open(object_module, "rb") as f:
            content = f.read()

        # Має бути BOM
        assert content.startswith(b'\xef\xbb\xbf')


class TestDryRunMode:
    """Тести dry-run режиму генерації"""

    def test_dry_run_minimal_processor(self, simple_processor, temp_dir):
        """Dry-run не створює файли"""
        generator = ProcessorGenerator(simple_processor)
        result = generator.generate(str(temp_dir), dry_run=True)

        assert result is None  # Dry-run повертає None

        # Перевіряємо що папка НЕ створена
        processor_root = temp_dir / simple_processor.name
        assert not processor_root.exists()

    def test_dry_run_complex_processor(self, complex_processor, temp_dir):
        """Dry-run з складним процесором"""
        generator = ProcessorGenerator(complex_processor)
        result = generator.generate(str(temp_dir), dry_run=True)

        assert result is None  # Dry-run повертає None

        # Перевіряємо що файли НЕ створені
        processor_root = temp_dir / complex_processor.name
        assert not processor_root.exists()

    def test_dry_run_validation_still_runs(self, temp_dir):
        """Dry-run виконує валідацію"""
        import importlib
        models_module = importlib.import_module("1c_processor_generator.models")
        Processor = models_module.Processor

        # Створюємо невалідний процесор (без атрибутів)
        processor = Processor(name="InvalidProcessor")

        generator = ProcessorGenerator(processor)

        # Валідація повинна працювати навіть у dry-run режимі
        # Але тут буде warning, а не error, тому generate поверне None (dry-run)
        result = generator.generate(str(temp_dir), dry_run=True)

        # Процесор валідний (warning не блокує генерацію), але dry-run повертає None
        assert result is None

    def test_normal_mode_creates_files(self, simple_processor, temp_dir):
        """Звичайний режим створює файли"""
        generator = ProcessorGenerator(simple_processor)
        result = generator.generate(str(temp_dir), dry_run=False)

        assert result is not None
        assert isinstance(result, Path)

        # Перевіряємо що файли СТВОРЕНІ
        processor_root = temp_dir / simple_processor.name
        assert processor_root.exists()

        main_xml = processor_root / f"{simple_processor.name}.xml"
        assert main_xml.exists()


class TestPopupGeneration:
    """Тести генерації Popup елементів"""

    def test_prepare_popup_element(self):
        """Підготовка Popup елемента"""
        import importlib
        models_module = importlib.import_module("1c_processor_generator.models")
        Processor = models_module.Processor
        FormElement = models_module.FormElement
        id_module = importlib.import_module("1c_processor_generator.id_allocator")
        IDAllocator = id_module.IDAllocator

        processor = Processor(name="ТестPopup")

        # Створюємо форму
        form = processor.add_form(name="Форма", default=True)

        # Створюємо Popup з кнопкою
        button = FormElement(
            element_type="Button",
            name="Кнопка1",
            command="Команда1"
        )

        popup = FormElement(
            element_type="Popup",
            name="МенюДействия",
            properties={
                "title_ru": "Действия",
                "picture": "StdPicture.ExecuteTask",
            },
            child_items=[button]
        )

        form.auto_command_bar_elements.append(popup)

        generator = ProcessorGenerator(processor)

        # Викликаємо _prepare_popup_element з IDAllocator (v2.38.0+)
        allocator = IDAllocator(_start_id=10)
        popup_data = generator._prepare_popup_element(popup, allocator)

        assert popup_data["type"] == "Popup"
        assert popup_data["name"] == "МенюДействия"
        assert popup_data["id"] == 10
        assert len(popup_data["child_items"]) == 1
        assert allocator.current > 10  # ID інкрементовано через allocator

    def test_popup_id_sequencing(self):
        """ID sequencing для Popup елементів"""
        import importlib
        models_module = importlib.import_module("1c_processor_generator.models")
        Processor = models_module.Processor
        FormElement = models_module.FormElement
        id_module = importlib.import_module("1c_processor_generator.id_allocator")
        IDAllocator = id_module.IDAllocator

        processor = Processor(name="ТестPopupID")

        # Створюємо форму
        form = processor.add_form(name="Форма", default=True)

        # Popup з двома кнопками
        button1 = FormElement(element_type="Button", name="Кнопка1", command="Команда1")
        button2 = FormElement(element_type="Button", name="Кнопка2", command="Команда2")

        popup = FormElement(
            element_type="Popup",
            name="Меню",
            child_items=[button1, button2]
        )

        form.auto_command_bar_elements.append(popup)

        generator = ProcessorGenerator(processor)
        form_elements, next_id = generator._prepare_form_elements(form)
        # v2.38.0+ use IDAllocator instead of raw next_id
        auto_bar_allocator = IDAllocator(_start_id=next_id)
        auto_command_bar = generator._prepare_auto_command_bar(auto_bar_allocator, form)

        assert len(auto_command_bar) == 1
        popup_elem = auto_command_bar[0]

        # Перевіряємо ID child items
        child_ids = [child["id"] for child in popup_elem["child_items"]]
        assert len(child_ids) == 2
        assert len(set(child_ids)) == 2  # Унікальні ID

    def test_generate_with_popup(self, temp_dir):
        """Генерація процесора з Popup"""
        import importlib
        models_module = importlib.import_module("1c_processor_generator.models")
        Processor = models_module.Processor
        FormElement = models_module.FormElement
        Command = models_module.Command

        processor = Processor(name="ПроцесорСPopup")

        # Створюємо форму
        form = processor.add_form(name="Форма", default=True)

        # Додаємо команду
        cmd = Command(
            name="ТестоваКоманда",
            title_ru="Тестовая команда",
            title_uk="Тестова команда",
            action="ТестоваКоманда"
        )
        form.commands.append(cmd)

        # Додаємо Popup
        button = FormElement(element_type="Button", name="ТестоваКнопка", command="ТестоваКоманда")
        popup = FormElement(
            element_type="Popup",
            name="МенюТест",
            properties={
                "title_ru": "Меню",
            },
            child_items=[button]
        )
        form.auto_command_bar_elements.append(popup)

        # Генеруємо
        generator = ProcessorGenerator(processor)
        result = generator.generate(str(temp_dir))

        assert result is not None
        assert isinstance(result, Path)

        # Перевіряємо що файли створено
        processor_root = temp_dir / processor.name
        assert processor_root.exists()

        # Перевіряємо Form.xml на наявність Popup
        form_xml = (
            processor_root / processor.name / "Forms" / "Форма" / "Ext" / "Form.xml"
        )
        assert form_xml.exists()

        content = form_xml.read_text(encoding="utf-8")
        assert "Popup" in content
        assert "МенюТест" in content


class TestHTMLDocumentFieldGeneration:
    """Тести генерації HTMLDocumentField елементів (v2.39.0+)"""

    def test_html_document_field_generation(self, temp_dir):
        """Генерація HTMLDocumentField елемента"""
        import importlib
        models_module = importlib.import_module("1c_processor_generator.models")
        Processor = models_module.Processor
        FormElement = models_module.FormElement
        FormAttribute = models_module.FormAttribute

        processor = Processor(name="ТестHTML")

        # Створюємо форму
        form = processor.add_form(name="Форма", default=True)

        # Додаємо form_attribute для HTML контенту
        html_attr = FormAttribute(
            name="HTMLКонтент",
            type="string"
        )
        form.form_attributes.append(html_attr)

        # Створюємо HTMLDocumentField
        html_field = FormElement(
            element_type="HTMLDocumentField",
            name="ПолеHTML",
            attribute="HTMLКонтент",
            properties={
                "title_location": "None",
                "width": 50,
                "height": 20
            },
            event_handlers={"OnClick": "ПолеHTMLПриНажатии"}
        )
        form.elements.append(html_field)

        # Генеруємо
        generator = ProcessorGenerator(processor)
        result = generator.generate(str(temp_dir))

        assert result is not None
        assert isinstance(result, Path)

        # Перевіряємо що файли створено
        processor_root = temp_dir / processor.name
        assert processor_root.exists()

        # Перевіряємо Form.xml на наявність HTMLDocumentField
        form_xml = (
            processor_root / processor.name / "Forms" / "Форма" / "Ext" / "Form.xml"
        )
        assert form_xml.exists()

        content = form_xml.read_text(encoding="utf-8")
        assert "HTMLDocumentField" in content
        assert "ПолеHTML" in content
        assert "HTMLКонтент" in content
        assert "TitleLocation" in content
        assert "OnClick" in content
        assert "ПолеHTMLПриНажатии" in content


class TestFormattedStringGeneration:
    """Тести генерації FormattedString (v2.45.0+)"""

    def test_label_decoration_formatted_true(self, temp_dir):
        """LabelDecoration з formatted=true генерує правильний XML"""
        import importlib
        models_module = importlib.import_module("1c_processor_generator.models")
        Processor = models_module.Processor
        FormElement = models_module.FormElement

        processor = Processor(name="ТестFormatted")

        # Створюємо форму
        form = processor.add_form(name="Форма", default=True)

        # Створюємо LabelDecoration з formatted=true
        label = FormElement(
            element_type="LabelDecoration",
            name="ВажливийТекст",
            properties={
                "title": "Увага: <b>важливо</b>!",
                "formatted": True
            }
        )
        form.elements.append(label)

        # Генеруємо
        generator = ProcessorGenerator(processor)
        result = generator.generate(str(temp_dir))

        assert result is not None

        # Перевіряємо Form.xml
        form_xml = (
            temp_dir / processor.name / processor.name / "Forms" / "Форма" / "Ext" / "Form.xml"
        )
        assert form_xml.exists()

        content = form_xml.read_text(encoding="utf-8")

        # Перевіряємо що formatted="true" в XML
        assert 'formatted="true"' in content
        assert "LabelDecoration" in content
        assert "ВажливийТекст" in content

    def test_label_decoration_formatted_false_default(self, temp_dir):
        """LabelDecoration без formatted генерує formatted='false'"""
        import importlib
        models_module = importlib.import_module("1c_processor_generator.models")
        Processor = models_module.Processor
        FormElement = models_module.FormElement

        processor = Processor(name="ТестFormattedDefault")

        form = processor.add_form(name="Форма", default=True)

        # LabelDecoration БЕЗ formatted property
        label = FormElement(
            element_type="LabelDecoration",
            name="ЗвичайнийТекст",
            properties={
                "title": "Звичайний текст"
            }
        )
        form.elements.append(label)

        generator = ProcessorGenerator(processor)
        result = generator.generate(str(temp_dir))

        assert result is not None

        form_xml = (
            temp_dir / processor.name / processor.name / "Forms" / "Форма" / "Ext" / "Form.xml"
        )
        content = form_xml.read_text(encoding="utf-8")

        # За замовчуванням formatted="false"
        assert 'formatted="false"' in content

    def test_label_decoration_html_escaped(self, temp_dir):
        """HTML теги в formatted title правильно екрануються для XML"""
        import importlib
        models_module = importlib.import_module("1c_processor_generator.models")
        Processor = models_module.Processor
        FormElement = models_module.FormElement

        processor = Processor(name="ТестHTMLEscape")

        form = processor.add_form(name="Форма", default=True)

        label = FormElement(
            element_type="LabelDecoration",
            name="HTMLТекст",
            properties={
                "title": "<font color='red'>Червоний</font> та <b>жирний</b>",
                "formatted": True
            }
        )
        form.elements.append(label)

        generator = ProcessorGenerator(processor)
        result = generator.generate(str(temp_dir))

        assert result is not None

        form_xml = (
            temp_dir / processor.name / processor.name / "Forms" / "Форма" / "Ext" / "Form.xml"
        )
        content = form_xml.read_text(encoding="utf-8")

        # HTML теги мають бути XML-escaped
        assert "&lt;font" in content or "<font" not in content
        assert "&lt;b&gt;" in content or "<b>" not in content
        assert 'formatted="true"' in content
