"""Tests for Templates support (v2.40.0+) and Automation (v2.41.0+)"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib
models_module = importlib.import_module("1c_processor_generator.models")
yaml_parser_module = importlib.import_module("1c_processor_generator.yaml_parser")
generator_module = importlib.import_module("1c_processor_generator.generator")
template_bsl_module = importlib.import_module("1c_processor_generator.template_bsl_generator")

Template = models_module.Template
TemplatePlaceholder = models_module.TemplatePlaceholder
TemplateAssets = models_module.TemplateAssets
Processor = models_module.Processor
Form = models_module.Form
YAMLParser = yaml_parser_module.YAMLParser
ProcessorGenerator = generator_module.ProcessorGenerator
generate_template_helpers = template_bsl_module.generate_template_helpers


class TestTemplateModel:
    """Tests for Template dataclass"""

    def test_template_creation_html(self):
        """Create HTMLDocument template"""
        template = Template(
            name="EmailTemplate",
            template_type="HTMLDocument",
            file_path="templates/email.html"
        )
        assert template.name == "EmailTemplate"
        assert template.template_type == "HTMLDocument"
        assert template.uuid is not None
        assert len(template.uuid) == 36  # UUID format

    def test_template_creation_spreadsheet(self):
        """Create SpreadsheetDocument template"""
        template = Template(
            name="ReportLayout",
            template_type="SpreadsheetDocument",
            file_path="templates/report.mxl"
        )
        assert template.template_type == "SpreadsheetDocument"

    def test_template_invalid_type_raises(self):
        """Invalid template type raises ValueError"""
        with pytest.raises(ValueError, match="Invalid template_type"):
            Template(name="Bad", template_type="InvalidType")

    def test_template_with_content(self):
        """Template with loaded content"""
        template = Template(
            name="Test",
            template_type="HTMLDocument",
            content="<html></html>"
        )
        assert template.content == "<html></html>"


class TestTemplateParser:
    """Tests for YAML template parsing"""

    def test_parse_html_template(self, tmp_path):
        """Parse HTMLDocument template from YAML"""
        # Create template file
        html_file = tmp_path / "email.html"
        html_file.write_text("<html><body>Hello</body></html>", encoding="utf-8")

        # Create YAML config
        yaml_content = """
processor:
  name: TestProcessor

templates:
  - name: EmailTemplate
    type: HTMLDocument
    file: email.html

forms:
  - name: Форма
    default: true
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content, encoding="utf-8")

        # Parse
        parser = YAMLParser(config_file)
        processor = parser.parse()

        assert processor is not None
        assert len(processor.templates) == 1
        assert processor.templates[0].name == "EmailTemplate"
        assert processor.templates[0].template_type == "HTMLDocument"
        assert processor.templates[0].content == "<html><body>Hello</body></html>"

    def test_parse_spreadsheet_template(self, tmp_path):
        """Parse SpreadsheetDocument template from YAML"""
        # Create MXL file (binary)
        mxl_file = tmp_path / "report.mxl"
        mxl_file.write_bytes(b'\x00\x01\x02\x03')  # Dummy binary

        yaml_content = """
processor:
  name: TestProcessor

templates:
  - name: ReportLayout
    type: SpreadsheetDocument
    file: report.mxl

forms:
  - name: Форма
    default: true
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content, encoding="utf-8")

        parser = YAMLParser(config_file)
        processor = parser.parse()

        assert len(processor.templates) == 1
        assert processor.templates[0].template_type == "SpreadsheetDocument"
        assert processor.templates[0].content_binary == b'\x00\x01\x02\x03'

    def test_parse_multiple_templates(self, tmp_path):
        """Parse multiple templates"""
        (tmp_path / "a.html").write_text("<html>A</html>", encoding="utf-8")
        (tmp_path / "b.mxl").write_bytes(b'MXL')

        yaml_content = """
processor:
  name: TestProcessor

templates:
  - name: TemplateA
    type: HTMLDocument
    file: a.html
  - name: TemplateB
    type: SpreadsheetDocument
    file: b.mxl

forms:
  - name: Форма
    default: true
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content, encoding="utf-8")

        parser = YAMLParser(config_file)
        processor = parser.parse()

        assert len(processor.templates) == 2

    def test_missing_template_file_returns_none(self, tmp_path):
        """Missing template file causes parse() to return None"""
        yaml_content = """
processor:
  name: TestProcessor

templates:
  - name: MissingTemplate
    type: HTMLDocument
    file: nonexistent.html

forms:
  - name: Форма
    default: true
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content, encoding="utf-8")

        parser = YAMLParser(config_file)
        # parser.parse() catches exceptions and returns None
        result = parser.parse()
        assert result is None

    def test_invalid_template_type_returns_none(self, tmp_path):
        """Invalid template type fails schema validation, returns None"""
        (tmp_path / "test.txt").write_text("test", encoding="utf-8")

        yaml_content = """
processor:
  name: TestProcessor

templates:
  - name: BadTemplate
    type: TextDocument
    file: test.txt

forms:
  - name: Форма
    default: true
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content, encoding="utf-8")

        parser = YAMLParser(config_file)
        # schema validation fails, returns None
        result = parser.parse()
        assert result is None


class TestTemplateGeneration:
    """Tests for template file generation"""

    def test_generate_html_template_structure(self, tmp_path):
        """Generate correct directory structure for HTML template"""
        # Create processor with template
        processor = Processor(name="TestProc")
        template = Template(
            name="HTMLTemplate",
            template_type="HTMLDocument",
            content="<html><body>Test</body></html>"
        )
        processor.templates.append(template)
        processor.forms.append(Form(name="Форма", default=True))

        # Generate
        generator = ProcessorGenerator(processor)
        result = generator.generate(str(tmp_path), save_snapshot=False)

        assert result is not None

        # Verify directory structure
        proc_root = tmp_path / "TestProc" / "TestProc"

        # Template metadata XML
        assert (proc_root / "Templates" / "HTMLTemplate.xml").exists()

        # Template Ext structure
        assert (proc_root / "Templates" / "HTMLTemplate" / "Ext" / "Template.xml").exists()

        # Template content - HTMLDocument uses language-specific files (ru.html, uk.html, en.html)
        content_dir = proc_root / "Templates" / "HTMLTemplate" / "Ext" / "Template"
        for lang in ["ru", "uk", "en"]:
            lang_file = content_dir / f"{lang}.html"
            assert lang_file.exists(), f"{lang}.html should exist at {lang_file}"
            assert lang_file.read_text(encoding="utf-8") == "<html><body>Test</body></html>"

    def test_generate_spreadsheet_template(self, tmp_path):
        """Generate SpreadsheetDocument template - MXL embedded in Template.xml"""
        processor = Processor(name="TestProc")
        # SpreadsheetDocument content_binary должен быть валидным UTF-8 XML
        # (MXL is embedded inline in Template.xml as UTF-8 text)
        mxl_content = b'<?xml version="1.0" encoding="UTF-8"?>\n<document xmlns="http://v8.1c.ru/8.2/data/spreadsheet"/>'
        template = Template(
            name="Report",
            template_type="SpreadsheetDocument",
            content_binary=mxl_content
        )
        processor.templates.append(template)
        processor.forms.append(Form(name="Форма", default=True))

        generator = ProcessorGenerator(processor)
        result = generator.generate(str(tmp_path), save_snapshot=False)

        proc_root = tmp_path / "TestProc" / "TestProc"
        # SpreadsheetDocument: MXL is embedded directly in Ext/Template.xml (not separate file)
        template_xml = proc_root / "Templates" / "Report" / "Ext" / "Template.xml"
        assert template_xml.exists()
        content = template_xml.read_text(encoding="utf-8-sig")
        assert '<document xmlns="http://v8.1c.ru/8.2/data/spreadsheet"/>' in content

    def test_main_xml_contains_template_reference(self, tmp_path):
        """Main processor XML contains Template reference"""
        processor = Processor(name="TestProc")
        processor.templates.append(Template(
            name="MyTemplate",
            template_type="HTMLDocument",
            content="<html></html>"
        ))
        processor.forms.append(Form(name="Форма", default=True))

        generator = ProcessorGenerator(processor)
        generator.generate(str(tmp_path), save_snapshot=False)

        main_xml = tmp_path / "TestProc" / "TestProc.xml"
        content = main_xml.read_text(encoding="utf-8-sig")

        assert "<Template>MyTemplate</Template>" in content

    def test_template_meta_xml_content(self, tmp_path):
        """Template metadata XML has correct structure"""
        processor = Processor(name="TestProc")
        processor.templates.append(Template(
            name="EmailTemplate",
            template_type="HTMLDocument",
            content="<html></html>"
        ))
        processor.forms.append(Form(name="Форма", default=True))

        generator = ProcessorGenerator(processor)
        generator.generate(str(tmp_path), save_snapshot=False)

        meta_xml = tmp_path / "TestProc" / "TestProc" / "Templates" / "EmailTemplate.xml"
        content = meta_xml.read_text(encoding="utf-8-sig")

        assert "<Name>EmailTemplate</Name>" in content
        assert "<TemplateType>HTMLDocument</TemplateType>" in content
        assert "uuid=" in content


# ============================================================================
# v2.41.0+ Template Automation Tests
# ============================================================================


class TestTemplatePlaceholderModel:
    """Tests for TemplatePlaceholder dataclass (v2.41.0+)"""

    def test_placeholder_with_bsl_value(self):
        """Create placeholder with BSL expression"""
        ph = TemplatePlaceholder(
            name="{{UserName}}",
            bsl_value="ТекущийПользователь().Имя"
        )
        assert ph.name == "{{UserName}}"
        assert ph.bsl_value == "ТекущийПользователь().Имя"
        assert ph.attribute is None

    def test_placeholder_with_attribute(self):
        """Create placeholder referencing attribute"""
        ph = TemplatePlaceholder(
            name="{{CompanyName}}",
            attribute="CompanyName"
        )
        assert ph.attribute == "CompanyName"
        assert ph.bsl_value is None


class TestTemplateAssetsModel:
    """Tests for TemplateAssets dataclass (v2.41.0+)"""

    def test_assets_with_styles(self):
        """Create assets with CSS styles"""
        assets = TemplateAssets(
            styles=[{"file": "styles.css", "content": ".header { color: red; }"}]
        )
        assert len(assets.styles) == 1
        assert assets.styles[0]["file"] == "styles.css"

    def test_assets_with_scripts(self):
        """Create assets with JS scripts"""
        assets = TemplateAssets(
            scripts=[{"inline": "console.log('test');"}]
        )
        assert len(assets.scripts) == 1


class TestTemplateAutomationFields:
    """Tests for Template auto_field (v2.41.0+)"""

    def test_template_auto_field_defaults(self):
        """Template auto_field defaults to False"""
        template = Template(
            name="Test",
            template_type="HTMLDocument"
        )
        assert template.auto_field is False
        assert template.field_name is None
        assert template.target_form is None

    def test_template_with_auto_field(self):
        """Template with auto_field enabled"""
        template = Template(
            name="EmailPreview",
            template_type="HTMLDocument",
            auto_field=True,
            field_name="PreviewField"
        )
        assert template.auto_field is True
        assert template.field_name == "PreviewField"


class TestAutomationFileParsing:
    """Tests for automation file parsing (v2.41.0+)"""

    def test_parse_automation_with_placeholders(self, tmp_path):
        """Parse automation file with placeholders"""
        # Create HTML template
        html_file = tmp_path / "email.html"
        html_file.write_text("<html>{{UserName}}</html>", encoding="utf-8")

        # Create automation file
        automation_file = tmp_path / "email.automation.yaml"
        automation_file.write_text("""
placeholders:
  - name: "{{UserName}}"
    bsl_value: "ТекущийПользователь().Имя"
  - name: "{{Date}}"
    attribute: DateField
""", encoding="utf-8")

        # Create config
        yaml_content = """
processor:
  name: TestProcessor

templates:
  - name: EmailTemplate
    type: HTMLDocument
    file: email.html
    automation: email.automation.yaml

forms:
  - name: Форма
    default: true
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content, encoding="utf-8")

        # Parse
        parser = YAMLParser(config_file)
        processor = parser.parse()

        assert processor is not None
        assert len(processor.templates) == 1
        template = processor.templates[0]
        assert len(template.placeholders) == 2
        assert template.placeholders[0].name == "{{UserName}}"
        assert template.placeholders[0].bsl_value == "ТекущийПользователь().Имя"
        assert template.placeholders[1].attribute == "DateField"

    def test_parse_auto_field_creates_form_attribute(self, tmp_path):
        """auto_field creates FormAttribute and HTMLDocumentField"""
        html_file = tmp_path / "preview.html"
        html_file.write_text("<html>Preview</html>", encoding="utf-8")

        yaml_content = """
processor:
  name: TestProcessor

templates:
  - name: PreviewTemplate
    type: HTMLDocument
    file: preview.html
    auto_field: true

forms:
  - name: Форма
    default: true
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content, encoding="utf-8")

        parser = YAMLParser(config_file)
        processor = parser.parse()

        assert processor is not None

        # Check that FormAttribute was created
        form = processor.forms[0]
        attr_names = [fa.name for fa in form.form_attributes]
        assert "PreviewTemplateHTML" in attr_names

        # Check that HTMLDocumentField element was created
        elem_names = [e.name for e in form.elements]
        assert "PreviewTemplateField" in elem_names

    def test_parse_auto_field_custom_field_name(self, tmp_path):
        """auto_field with custom field_name"""
        html_file = tmp_path / "email.html"
        html_file.write_text("<html></html>", encoding="utf-8")

        yaml_content = """
processor:
  name: TestProcessor

templates:
  - name: EmailTemplate
    type: HTMLDocument
    file: email.html
    auto_field: true
    field_name: CustomEmailField

forms:
  - name: Форма
    default: true
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content, encoding="utf-8")

        parser = YAMLParser(config_file)
        processor = parser.parse()

        form = processor.forms[0]
        elem_names = [e.name for e in form.elements]
        assert "CustomEmailField" in elem_names

    def test_parse_assets_inject_css(self, tmp_path):
        """Assets CSS injection into HTML"""
        html_file = tmp_path / "page.html"
        html_file.write_text("<html><head></head><body>Content</body></html>", encoding="utf-8")

        css_file = tmp_path / "styles.css"
        css_file.write_text(".header { color: blue; }", encoding="utf-8")

        automation_file = tmp_path / "page.automation.yaml"
        automation_file.write_text("""
assets:
  styles:
    - file: styles.css
""", encoding="utf-8")

        yaml_content = """
processor:
  name: TestProcessor

templates:
  - name: PageTemplate
    type: HTMLDocument
    file: page.html
    automation: page.automation.yaml

forms:
  - name: Форма
    default: true
"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(yaml_content, encoding="utf-8")

        parser = YAMLParser(config_file)
        processor = parser.parse()

        template = processor.templates[0]
        assert "<style>" in template.content
        assert ".header { color: blue; }" in template.content


class TestTemplateBSLGeneration:
    """Tests for BSL helper generation (v2.41.0+)"""

    def test_generate_helper_with_placeholders(self):
        """Generate BSL helper function for template with placeholders"""
        processor = Processor(name="TestProc")
        template = Template(
            name="EmailTemplate",
            template_type="HTMLDocument",
            content="<html>{{UserName}}</html>"
        )
        template.placeholders = [
            TemplatePlaceholder(name="{{UserName}}", bsl_value="ТекущийПользователь().Имя"),
            TemplatePlaceholder(name="{{Company}}", attribute="CompanyName"),
        ]
        processor.templates.append(template)

        bsl_code = generate_template_helpers(processor)

        assert "Функция ПолучитьТекстМакетаEmailTemplate()" in bsl_code
        assert 'СтрЗаменить(Результат, "{{UserName}}", ТекущийПользователь().Имя)' in bsl_code
        assert 'СтрЗаменить(Результат, "{{Company}}", Объект.CompanyName)' in bsl_code
        assert "&НаСервере" in bsl_code

    def test_no_helper_without_placeholders(self):
        """No BSL helper generated for template without placeholders"""
        processor = Processor(name="TestProc")
        template = Template(
            name="SimpleTemplate",
            template_type="HTMLDocument",
            content="<html></html>"
        )
        processor.templates.append(template)

        bsl_code = generate_template_helpers(processor)
        assert bsl_code == ""

    def test_multiple_templates_generate_multiple_helpers(self):
        """Multiple templates with placeholders generate multiple helpers"""
        processor = Processor(name="TestProc")

        t1 = Template(name="Template1", template_type="HTMLDocument")
        t1.placeholders = [TemplatePlaceholder(name="{{A}}", bsl_value='"A"')]

        t2 = Template(name="Template2", template_type="HTMLDocument")
        t2.placeholders = [TemplatePlaceholder(name="{{B}}", bsl_value='"B"')]

        processor.templates = [t1, t2]

        bsl_code = generate_template_helpers(processor)

        assert "ПолучитьТекстМакетаTemplate1" in bsl_code
        assert "ПолучитьТекстМакетаTemplate2" in bsl_code
