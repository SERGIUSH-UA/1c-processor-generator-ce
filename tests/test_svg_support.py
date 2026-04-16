"""
Тести для SVG Local Pictures підтримки (v2.23.0+).

Перевіряє:
- SVGConverter (валідація, конвертація)
- PictureDecoration parsing
- Local Pictures generation
- Інтеграція з генератором
"""

import pytest
import tempfile
import sys
from pathlib import Path
import os

# Skip all SVG tests on Windows - cairosvg requires GTK+ Runtime which is not available in CI
pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="SVG tests require cairosvg which needs GTK+ Runtime on Windows"
)

# SVG Converter tests
class TestSVGConverter:
    """Тести для SVGConverter класу"""

    def test_svg_converter_initialization(self):
        """SVGConverter ініціалізується коректно"""
        import importlib
        svg_converter = importlib.import_module('1c_processor_generator.svg_converter')
        SVGConverter = svg_converter.SVGConverter

        converter = SVGConverter()
        assert converter is not None
        # cairosvg має бути доступний після pip install
        assert converter._cairosvg_available or converter._pillow_available

    def test_validate_svg_valid_file(self, tmp_path):
        """Валідація правильного SVG файлу"""
        import importlib
        svg_converter = importlib.import_module('1c_processor_generator.svg_converter')
        SVGConverter = svg_converter.SVGConverter

        # Створюємо простий валідний SVG
        svg_file = tmp_path / "test.svg"
        svg_content = '''<?xml version="1.0"?>
<svg width="100" height="100" xmlns="http://www.w3.org/2000/svg">
    <rect width="100" height="100" fill="blue"/>
</svg>'''
        svg_file.write_text(svg_content, encoding='utf-8')

        converter = SVGConverter()
        # Має пройти без винятків
        assert converter.validate_svg(str(svg_file)) == True

    def test_validate_svg_invalid_file(self, tmp_path):
        """Валідація невалідного SVG файлу"""
        import importlib
        svg_converter = importlib.import_module('1c_processor_generator.svg_converter')
        SVGConverter = svg_converter.SVGConverter
        SVGValidationError = svg_converter.SVGValidationError

        # Створюємо невалідний SVG
        svg_file = tmp_path / "bad.svg"
        svg_file.write_text("Not an SVG file", encoding='utf-8')

        converter = SVGConverter()
        with pytest.raises(SVGValidationError):
            converter.validate_svg(str(svg_file))

    def test_validate_svg_nonexistent_file(self):
        """Валідація неіснуючого файлу"""
        import importlib
        svg_converter = importlib.import_module('1c_processor_generator.svg_converter')
        SVGConverter = svg_converter.SVGConverter
        SVGValidationError = svg_converter.SVGValidationError

        converter = SVGConverter()
        with pytest.raises(SVGValidationError, match="not found"):
            converter.validate_svg("nonexistent.svg")

    def test_convert_svg_to_png(self, tmp_path):
        """Конвертація SVG → PNG"""
        import importlib
        svg_converter = importlib.import_module('1c_processor_generator.svg_converter')
        SVGConverter = svg_converter.SVGConverter

        # Створюємо простий SVG
        svg_file = tmp_path / "logo.svg"
        svg_content = '''<?xml version="1.0"?>
<svg width="200" height="80" xmlns="http://www.w3.org/2000/svg">
    <rect width="200" height="80" fill="#2196F3"/>
    <circle cx="40" cy="40" r="20" fill="#FFFFFF"/>
</svg>'''
        svg_file.write_text(svg_content, encoding='utf-8')

        output_png = tmp_path / "output.png"

        converter = SVGConverter()
        result = converter.convert_svg_to_png(
            svg_path=str(svg_file),
            output_path=str(output_png),
            width=200,
            height=80
        )

        # Перевіряємо що PNG створено
        assert Path(result).exists()
        assert output_png.stat().st_size > 0

    def test_get_svg_dimensions(self, tmp_path):
        """Витягування розмірів з SVG"""
        import importlib
        svg_converter = importlib.import_module('1c_processor_generator.svg_converter')
        SVGConverter = svg_converter.SVGConverter

        svg_file = tmp_path / "sized.svg"
        svg_content = '''<?xml version="1.0"?>
<svg width="300" height="150" xmlns="http://www.w3.org/2000/svg">
    <rect width="300" height="150" fill="red"/>
</svg>'''
        svg_file.write_text(svg_content, encoding='utf-8')

        converter = SVGConverter()
        width, height = converter.get_svg_dimensions(str(svg_file))

        assert width == 300
        assert height == 150


# PictureDecoration parsing tests
class TestPictureDecorationParsing:
    """Тести для парсингу PictureDecoration"""

    def test_parse_picture_decoration_with_svg(self, tmp_path):
        """Парсинг PictureDecoration з svg_source"""
        import importlib
        yaml_parser = importlib.import_module('1c_processor_generator.yaml_parser')
        YAMLParser = yaml_parser.YAMLParser

        # Створюємо SVG файл
        svg_file = tmp_path / "logo.svg"
        svg_file.write_text('<?xml version="1.0"?><svg width="100" height="100" xmlns="http://www.w3.org/2000/svg"><rect width="100" height="100"/></svg>')

        # Створюємо YAML конфігурацію
        yaml_config = tmp_path / "config.yaml"
        yaml_content = f"""
processor:
  name: TestPicture
  synonym:
    ru: Тест
    uk: Тест
    en: Test

forms:
  - name: Форма
    default: true
    elements:
      - type: PictureDecoration
        name: Logo
        svg_source: {svg_file.name}
        width: 100
        height: 100
        picture_size: Proportionally
"""
        yaml_config.write_text(yaml_content)

        parser = YAMLParser(str(yaml_config))
        processor = parser.parse()

        # Перевіряємо що елемент створено
        assert len(processor.forms) == 1
        form = processor.forms[0]
        assert len(form.elements) == 1

        elem = form.elements[0]
        assert elem.element_type == "PictureDecoration"
        assert elem.name == "Logo"
        assert elem.properties['svg_source'] == svg_file.name
        assert elem.properties['width'] == 100
        assert elem.properties['height'] == 100
        assert elem.properties['picture_size'] == "Proportionally"

    def test_parse_picture_decoration_with_std_picture(self):
        """Парсинг PictureDecoration з StdPicture"""
        import importlib
        yaml_parser = importlib.import_module('1c_processor_generator.yaml_parser')
        YAMLParser = yaml_parser.YAMLParser

        yaml_content = """
processor:
  name: TestStdPicture
  synonym:
    ru: Тест
    uk: Тест
    en: Test

forms:
  - name: Форма
    default: true
    elements:
      - type: PictureDecoration
        name: Icon
        picture: StdPicture.Information
        width: 32
        height: 32
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write(yaml_content)
            yaml_path = f.name

        try:
            parser = YAMLParser(yaml_path)
            processor = parser.parse()

            elem = processor.forms[0].elements[0]
            assert elem.element_type == "PictureDecoration"
            assert elem.properties['picture'] == "StdPicture.Information"
        finally:
            os.unlink(yaml_path)


# Local Pictures generation tests
class TestLocalPicturesGeneration:
    """Тести для генерації Local Pictures"""

    def test_generate_local_pictures_creates_structure(self, tmp_path):
        """Генерація створює правильну структуру Items/{ElementName}/Picture.png"""
        import importlib
        yaml_parser = importlib.import_module('1c_processor_generator.yaml_parser')
        generator = importlib.import_module('1c_processor_generator.generator')
        YAMLParser = yaml_parser.YAMLParser
        ProcessorGenerator = generator.ProcessorGenerator

        # Створюємо SVG
        svg_file = tmp_path / "test.svg"
        svg_file.write_text('<?xml version="1.0"?><svg width="50" height="50" xmlns="http://www.w3.org/2000/svg"><rect width="50" height="50" fill="green"/></svg>')

        # Створюємо YAML
        yaml_config = tmp_path / "config.yaml"
        yaml_content = f"""
processor:
  name: LocalPictureTest
  synonym:
    ru: Тест
    uk: Тест
    en: Test

attributes:
  - name: Field
    type: string

forms:
  - name: Форма
    default: true
    elements:
      - type: PictureDecoration
        name: TestLogo
        svg_source: {svg_file.name}
        width: 50
        height: 50
    commands:
      - name: DoSomething
        title:
          ru: Зробити
          uk: Зробити
          en: Do
        handler: DoSomethingHandler
"""
        yaml_config.write_text(yaml_content)

        # Створюємо handlers файл
        handlers_file = tmp_path / "handlers.bsl"
        handlers_file.write_text("""
&НаКлиенте
Процедура DoSomethingHandler(Команда)
    Сообщить("Test");
КонецПроцедуры
""")

        # Парсимо і генеруємо
        parser = YAMLParser(str(yaml_config))
        processor = parser.parse()

        # Inject BSL handlers using BSLSplitter
        import importlib
        bsl_splitter = importlib.import_module('1c_processor_generator.bsl_splitter')
        bsl_injector = importlib.import_module('1c_processor_generator.bsl_injector')
        BSLSplitter = bsl_splitter.BSLSplitter
        BSLInjector = bsl_injector.BSLInjector

        splitter = BSLSplitter(handlers_file)
        virtual_handlers = splitter.extract_procedures()

        injector = BSLInjector()
        injector.virtual_handlers_cache = virtual_handlers
        injector.inject_all_handlers(processor)

        output_dir = tmp_path / "output"
        generator = ProcessorGenerator(processor)
        result = generator.generate(str(output_dir))

        # Перевіряємо структуру
        assert result is not None

        # Перевіряємо PNG файл (форма називається "Форма" через backward compatibility з singular form:)
        # result вже вказує на output/LocalPictureTest
        picture_png = result / "LocalPictureTest" / "Forms" / "Форма" / "Ext" / "Form" / "Items" / "TestLogo" / "Picture.png"
        assert picture_png.exists()
        assert picture_png.stat().st_size > 0

    def test_local_picture_flag_set_in_properties(self, tmp_path):
        """Після конвертації встановлюється local_picture flag"""
        import importlib
        yaml_parser = importlib.import_module('1c_processor_generator.yaml_parser')
        generator = importlib.import_module('1c_processor_generator.generator')
        YAMLParser = yaml_parser.YAMLParser
        ProcessorGenerator = generator.ProcessorGenerator

        svg_file = tmp_path / "flag_test.svg"
        svg_file.write_text('<?xml version="1.0"?><svg width="100" height="100" xmlns="http://www.w3.org/2000/svg"><circle cx="50" cy="50" r="40"/></svg>')

        yaml_config = tmp_path / "config.yaml"
        yaml_content = f"""
processor:
  name: FlagTest
  synonym:
    ru: Тест
    uk: Тест
    en: Test

forms:
  - name: Форма
    default: true
    elements:
      - type: PictureDecoration
        name: MyPicture
        svg_source: {svg_file.name}
    commands:
      - name: Test
        title:
          ru: Тест
          uk: Тест
          en: Test
        handler: TestHandler
"""
        yaml_config.write_text(yaml_content)

        handlers_file = tmp_path / "handlers.bsl"
        handlers_file.write_text("&НаКлиенте\nПроцедура TestHandler(Команда)\nКонецПроцедуры")

        parser = YAMLParser(str(yaml_config))
        processor = parser.parse()

        # Inject BSL handlers using BSLSplitter
        import importlib
        bsl_splitter = importlib.import_module('1c_processor_generator.bsl_splitter')
        bsl_injector = importlib.import_module('1c_processor_generator.bsl_injector')
        BSLSplitter = bsl_splitter.BSLSplitter
        BSLInjector = bsl_injector.BSLInjector

        splitter = BSLSplitter(handlers_file)
        virtual_handlers = splitter.extract_procedures()

        injector = BSLInjector()
        injector.virtual_handlers_cache = virtual_handlers
        injector.inject_all_handlers(processor)

        # Після парсингу svg_source має бути в properties
        elem = processor.forms[0].elements[0]
        assert 'svg_source' in elem.properties

        output_dir = tmp_path / "output"
        generator = ProcessorGenerator(processor)

        # Після _generate_local_pictures() svg_source має бути видалено
        # і local_picture має бути встановлено
        # (це відбувається всередині generate())
        generator.generate(str(output_dir))

        # Після генерації перевіряємо що local_picture встановлено
        # (опосередковано через наявність PNG файлу)
        # Форма називається "Форма" через backward compatibility з singular form:
        # generator.generate() повертає output_dir/FlagTest, тому додаємо ще один рівень
        picture_path = output_dir / "FlagTest" / "FlagTest" / "Forms" / "Форма" / "Ext" / "Form" / "Items" / "MyPicture" / "Picture.png"
        assert picture_path.exists()


# Integration test
class TestSVGIntegration:
    """Інтеграційні тести повного циклу"""

    def test_full_generation_with_svg_logo(self, tmp_path):
        """Повна генерація обробки з SVG логотипом"""
        import importlib
        yaml_parser = importlib.import_module('1c_processor_generator.yaml_parser')
        generator = importlib.import_module('1c_processor_generator.generator')
        YAMLParser = yaml_parser.YAMLParser
        ProcessorGenerator = generator.ProcessorGenerator

        # Створюємо реалістичний SVG логотип
        svg_file = tmp_path / "company_logo.svg"
        svg_content = '''<?xml version="1.0"?>
<svg width="200" height="80" xmlns="http://www.w3.org/2000/svg">
    <rect width="200" height="80" fill="#2196F3" rx="8"/>
    <circle cx="40" cy="40" r="20" fill="#FFFFFF"/>
    <text x="75" y="50" font-family="Arial" font-size="20" fill="#FFFFFF">Company</text>
</svg>'''
        svg_file.write_text(svg_content)

        # Створюємо повну конфігурацію
        yaml_config = tmp_path / "full_test.yaml"
        yaml_content = f"""
processor:
  name: FullSVGTest
  synonym:
    ru: Полный тест SVG
    uk: Повний тест SVG
    en: Full SVG Test

attributes:
  - name: Name
    type: string
  - name: Description
    type: string

forms:
  - name: Форма
    default: true
    properties:
      title:
        ru: Главная форма
        uk: Головна форма
        en: Main Form

    elements:
      - type: PictureDecoration
        name: CompanyLogo
        svg_source: {svg_file.name}
        width: 200
        height: 80
        form_width: 200
        form_height: 80
        picture_size: Proportionally
        hyperlink: false

      - type: InputField
        name: NameField
        attribute: Name

      - type: InputField
        name: DescField
        attribute: Description

    commands:
      - name: Save
        title:
          ru: Сохранить
          uk: Зберегти
          en: Save
        handler: SaveHandler
"""
        yaml_config.write_text(yaml_content)

        # Handlers
        handlers_file = tmp_path / "handlers.bsl"
        handlers_content = """
&НаКлиенте
Процедура SaveHandler(Команда)
    Если ПустаяСтрока(Объект.Name) Тогда
        Сообщить("Введите имя!");
        Возврат;
    КонецЕсли;

    Сообщить("Сохранено: " + Объект.Name);
КонецПроцедуры
"""
        handlers_file.write_text(handlers_content)

        # Парсинг
        parser = YAMLParser(str(yaml_config))
        processor = parser.parse()

        # Inject BSL handlers using BSLSplitter
        import importlib
        bsl_splitter = importlib.import_module('1c_processor_generator.bsl_splitter')
        bsl_injector = importlib.import_module('1c_processor_generator.bsl_injector')
        BSLSplitter = bsl_splitter.BSLSplitter
        BSLInjector = bsl_injector.BSLInjector

        splitter = BSLSplitter(handlers_file)
        virtual_handlers = splitter.extract_procedures()

        injector = BSLInjector()
        injector.virtual_handlers_cache = virtual_handlers
        injector.inject_all_handlers(processor)

        # Валідація
        assert processor.name == "FullSVGTest"
        assert len(processor.forms) == 1
        assert len(processor.forms[0].elements) == 3  # Logo + 2 fields

        # Генерація
        output_dir = tmp_path / "generated"
        generator = ProcessorGenerator(processor)
        result = generator.generate(str(output_dir))

        assert result is not None

        # Перевіряємо всі згенеровані файли
        # Форма називається "Форма" через backward compatibility з singular form:
        processor_xml = result / "FullSVGTest.xml"
        object_module = result / "FullSVGTest" / "Ext" / "ObjectModule.bsl"
        form_xml = result / "FullSVGTest" / "Forms" / "Форма.xml"
        form_module = result / "FullSVGTest" / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
        form_structure_xml = result / "FullSVGTest" / "Forms" / "Форма" / "Ext" / "Form.xml"
        logo_png = result / "FullSVGTest" / "Forms" / "Форма" / "Ext" / "Form" / "Items" / "CompanyLogo" / "Picture.png"

        assert processor_xml.exists()
        assert object_module.exists()
        assert form_xml.exists()
        assert form_module.exists()
        assert form_structure_xml.exists()
        assert logo_png.exists()

        # Перевіряємо що PNG має розумний розмір
        png_size = logo_png.stat().st_size
        assert png_size > 500  # At least 500 bytes
        assert png_size < 50000  # Less than 50KB

        # Перевіряємо XML форми містить правильний reference
        form_xml_content = form_structure_xml.read_text(encoding='utf-8')
        assert '<PictureDecoration name="CompanyLogo"' in form_xml_content
        assert '<xr:Abs>Picture.png</xr:Abs>' in form_xml_content
        assert '<Width>200</Width>' in form_xml_content
        assert '<Height>80</Height>' in form_xml_content

    def test_backward_compatibility_without_svg(self, tmp_path):
        """Генерація без SVG працює як раніше (backward compatibility)"""
        import importlib
        yaml_parser = importlib.import_module('1c_processor_generator.yaml_parser')
        generator = importlib.import_module('1c_processor_generator.generator')
        YAMLParser = yaml_parser.YAMLParser
        ProcessorGenerator = generator.ProcessorGenerator

        yaml_config = tmp_path / "no_svg.yaml"
        yaml_content = """
processor:
  name: NoSVGTest
  synonym:
    ru: Тест без SVG
    uk: Тест без SVG
    en: No SVG Test

attributes:
  - name: Field
    type: string

forms:
  - name: SimpleForm
    default: true
    elements:
      - type: InputField
        name: FieldInput
        attribute: Field
    commands:
      - name: DoIt
        title:
          ru: Выполнить
          uk: Виконати
          en: Do It
        handler: DoItHandler
        picture: StdPicture.Refresh
"""
        yaml_config.write_text(yaml_content)

        handlers_file = tmp_path / "handlers.bsl"
        handlers_file.write_text("&НаКлиенте\nПроцедура DoItHandler(Команда)\nКонецПроцедуры")

        parser = YAMLParser(str(yaml_config))
        processor = parser.parse()

        # Inject BSL handlers using BSLSplitter
        import importlib
        bsl_splitter = importlib.import_module('1c_processor_generator.bsl_splitter')
        bsl_injector = importlib.import_module('1c_processor_generator.bsl_injector')
        BSLSplitter = bsl_splitter.BSLSplitter
        BSLInjector = bsl_injector.BSLInjector

        splitter = BSLSplitter(handlers_file)
        virtual_handlers = splitter.extract_procedures()

        injector = BSLInjector()
        injector.virtual_handlers_cache = virtual_handlers
        injector.inject_all_handlers(processor)

        output_dir = tmp_path / "output"
        generator = ProcessorGenerator(processor)
        result = generator.generate(str(output_dir))

        # Має згенеруватися нормально БЕЗ Items/ папки
        assert result is not None
        processor_xml = result / "NoSVGTest.xml"
        assert processor_xml.exists()

        # Items/ папки НЕ має бути (немає SVG)
        items_dir = result / "NoSVGTest" / "Forms" / "SimpleForm" / "Ext" / "Form" / "Items"
        assert not items_dir.exists()
