"""
Tests for v2.71.x properties (InputField buttons, Button, Table).

v2.71.0: InputField button controls (mark_negatives, open_button, etc.)
v2.71.1: DefaultButton, AutoMarkIncomplete
v2.71.2: Table properties (search_string_location, selection_mode, row_picture_data_path)
v2.71.3: ShapeRepresentation for Button
"""

import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib

models_module = importlib.import_module("1c_processor_generator.models")
generator_module = importlib.import_module("1c_processor_generator.generator")
schemas_module = importlib.import_module("1c_processor_generator.parsing.schemas")

Processor = models_module.Processor
FormElement = models_module.FormElement
Command = models_module.Command
Column = models_module.Column
ProcessorGenerator = generator_module.ProcessorGenerator
get_schema = schemas_module.get_schema


@pytest.fixture
def temp_dir(tmp_path):
    """Temporary directory for generated files."""
    return tmp_path


class TestV271SchemasRegistered:
    """Test that v2.71.x properties are registered in schemas.py"""

    def test_inputfield_button_properties_in_schema(self):
        """v2.71.0: InputField button controls registered in schema"""
        schema = get_schema("InputField")
        prop_keys = [p.key for p in schema.props]

        # v2.71.0 properties
        assert "mark_negatives" in prop_keys
        assert "open_button" in prop_keys
        assert "clear_button" in prop_keys
        assert "drop_list_button" in prop_keys
        assert "spin_button" in prop_keys
        assert "create_button" in prop_keys

        # v2.71.1 property
        assert "auto_mark_incomplete" in prop_keys

    def test_button_properties_in_schema(self):
        """v2.71.1 + v2.71.3: Button properties registered in schema"""
        schema = get_schema("Button")
        prop_keys = [p.key for p in schema.props]

        assert "default_button" in prop_keys  # v2.71.1
        assert "shape_representation" in prop_keys  # v2.71.3

    def test_table_properties_in_schema(self):
        """v2.71.2: Table properties registered in schema"""
        schema = get_schema("Table")
        prop_keys = [p.key for p in schema.props]

        assert "search_string_location" in prop_keys
        assert "row_picture_data_path" in prop_keys
        assert "selection_mode" in prop_keys


class TestV271InputFieldRendering:
    """Test v2.71.0 InputField button controls render to XML"""

    def test_mark_negatives_renders(self, temp_dir):
        """mark_negatives: true renders to <MarkNegatives>true</MarkNegatives>"""
        processor = Processor(name="TestMN")
        processor.add_attribute(name="Сумма", type="number")
        form = processor.add_form(name="Форма", default=True)
        form.elements.append(FormElement(
            element_type="InputField",
            name="СуммаПоле",
            attribute="Сумма",
            properties={"mark_negatives": True}
        ))

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_xml = temp_dir / "TestMN" / "TestMN" / "Forms" / "Форма" / "Ext" / "Form.xml"
        content = form_xml.read_text(encoding="utf-8")

        assert "<MarkNegatives>true</MarkNegatives>" in content

    def test_all_button_controls_render(self, temp_dir):
        """All 6 InputField button controls render correctly"""
        processor = Processor(name="TestButtons")
        processor.add_attribute(name="TestField", type="string")
        form = processor.add_form(name="Форма", default=True)
        form.elements.append(FormElement(
            element_type="InputField",
            name="TestInput",
            attribute="TestField",
            properties={
                "open_button": True,
                "clear_button": False,  # Explicit false
                "drop_list_button": True,
                "spin_button": True,
                "create_button": True,
            }
        ))

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_xml = temp_dir / "TestButtons" / "TestButtons" / "Forms" / "Форма" / "Ext" / "Form.xml"
        content = form_xml.read_text(encoding="utf-8")

        assert "<OpenButton>true</OpenButton>" in content
        assert "<ClearButton>false</ClearButton>" in content
        assert "<DropListButton>true</DropListButton>" in content
        assert "<SpinButton>true</SpinButton>" in content
        assert "<CreateButton>true</CreateButton>" in content

    def test_auto_mark_incomplete_renders(self, temp_dir):
        """v2.71.1: auto_mark_incomplete renders correctly"""
        processor = Processor(name="TestAMI")
        processor.add_attribute(name="Наименование", type="string")
        form = processor.add_form(name="Форма", default=True)
        form.elements.append(FormElement(
            element_type="InputField",
            name="НаименованиеПоле",
            attribute="Наименование",
            properties={"auto_mark_incomplete": True}
        ))

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_xml = temp_dir / "TestAMI" / "TestAMI" / "Forms" / "Форма" / "Ext" / "Form.xml"
        content = form_xml.read_text(encoding="utf-8")

        assert "<AutoMarkIncomplete>true</AutoMarkIncomplete>" in content


class TestV271ButtonRendering:
    """Test v2.71.1 + v2.71.3 Button properties render to XML"""

    def test_default_button_renders(self, temp_dir):
        """v2.71.1: default_button renders correctly"""
        processor = Processor(name="TestDB")
        form = processor.add_form(name="Форма", default=True)
        form.commands.append(Command(name="ОК", title_ru="ОК", title_uk="ОК", action="ОК"))
        form.elements.append(FormElement(
            element_type="Button",
            name="ОККнопка",
            command="ОК",
            properties={"default_button": True}
        ))

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_xml = temp_dir / "TestDB" / "TestDB" / "Forms" / "Форма" / "Ext" / "Form.xml"
        content = form_xml.read_text(encoding="utf-8")

        assert "<DefaultButton>true</DefaultButton>" in content

    def test_shape_representation_renders(self, temp_dir):
        """v2.71.3: shape_representation renders correctly"""
        processor = Processor(name="TestSR")
        form = processor.add_form(name="Форма", default=True)
        form.commands.append(Command(name="Cmd1", title_ru="Always", title_uk="Always", action="Cmd1"))
        form.commands.append(Command(name="Cmd2", title_ru="WhenActive", title_uk="WhenActive", action="Cmd2"))
        form.commands.append(Command(name="Cmd3", title_ru="None", title_uk="None", action="Cmd3"))

        form.elements.append(FormElement(
            element_type="Button", name="Btn1", command="Cmd1",
            properties={"shape_representation": "Always"}
        ))
        form.elements.append(FormElement(
            element_type="Button", name="Btn2", command="Cmd2",
            properties={"shape_representation": "WhenActive"}
        ))
        form.elements.append(FormElement(
            element_type="Button", name="Btn3", command="Cmd3",
            properties={"shape_representation": "None"}
        ))

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_xml = temp_dir / "TestSR" / "TestSR" / "Forms" / "Форма" / "Ext" / "Form.xml"
        content = form_xml.read_text(encoding="utf-8")

        assert "<ShapeRepresentation>Always</ShapeRepresentation>" in content
        assert "<ShapeRepresentation>WhenActive</ShapeRepresentation>" in content
        assert "<ShapeRepresentation>None</ShapeRepresentation>" in content


class TestV271TableRendering:
    """Test v2.71.2 Table properties render to XML"""

    def test_search_string_location_renders(self, temp_dir):
        """search_string_location: CommandBar renders correctly"""
        processor = Processor(name="TestSSL")
        ts = processor.add_tabular_section(name="Товары")
        ts.columns.append(Column(name="Наименование", type="string"))
        form = processor.add_form(name="Форма", default=True)
        form.elements.append(FormElement(
            element_type="Table",
            name="ТоварыТаблица",
            tabular_section="Товары",
            properties={"search_string_location": "CommandBar"}
        ))

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_xml = temp_dir / "TestSSL" / "TestSSL" / "Forms" / "Форма" / "Ext" / "Form.xml"
        content = form_xml.read_text(encoding="utf-8")

        assert "<SearchStringLocation>CommandBar</SearchStringLocation>" in content

    def test_selection_mode_renders(self, temp_dir):
        """selection_mode: MultiRow renders correctly"""
        processor = Processor(name="TestSM")
        ts = processor.add_tabular_section(name="Строки")
        ts.columns.append(Column(name="Код", type="string"))
        form = processor.add_form(name="Форма", default=True)
        form.elements.append(FormElement(
            element_type="Table",
            name="СтрокиТаблица",
            tabular_section="Строки",
            properties={"selection_mode": "MultiRow"}
        ))

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_xml = temp_dir / "TestSM" / "TestSM" / "Forms" / "Форма" / "Ext" / "Form.xml"
        content = form_xml.read_text(encoding="utf-8")

        assert "<SelectionMode>MultiRow</SelectionMode>" in content

    def test_row_picture_data_path_renders(self, temp_dir):
        """row_picture_data_path renders correctly"""
        processor = Processor(name="TestRPDP")
        ts = processor.add_tabular_section(name="Элементы")
        ts.columns.append(Column(name="Имя", type="string"))
        ts.columns.append(Column(name="Картинка", type="number"))
        form = processor.add_form(name="Форма", default=True)
        form.elements.append(FormElement(
            element_type="Table",
            name="ЭлементыТаблица",
            tabular_section="Элементы",
            properties={"row_picture_data_path": "Элементы.Картинка"}
        ))

        generator = ProcessorGenerator(processor)
        generator.generate(str(temp_dir))

        form_xml = temp_dir / "TestRPDP" / "TestRPDP" / "Forms" / "Форма" / "Ext" / "Form.xml"
        content = form_xml.read_text(encoding="utf-8")

        assert "<RowPictureDataPath>Элементы.Картинка</RowPictureDataPath>" in content


class TestV271YamlParsing:
    """Test that v2.71.x properties parse correctly from YAML"""

    def test_inputfield_properties_from_yaml(self, temp_dir):
        """InputField v2.71.x properties parse from YAML config"""
        import yaml
        yaml_parser = importlib.import_module("1c_processor_generator.yaml_parser")

        config = {
            "processor": {"name": "TestYAML"},
            "attributes": [
                {"name": "Сумма", "type": "number", "digits": 10}
            ],
            "forms": [{
                "name": "Форма",
                "default": True,
                "elements": [{
                    "type": "InputField",
                    "name": "СуммаПоле",
                    "attribute": "Сумма",
                    "mark_negatives": True,
                    "open_button": True,
                    "auto_mark_incomplete": True
                }]
            }]
        }

        yaml_path = temp_dir / "config.yaml"
        yaml_path.write_text(yaml.dump(config, allow_unicode=True), encoding="utf-8")

        processor = yaml_parser.parse_yaml_config(yaml_path)
        form = processor.get_default_form()
        elem = form.elements[0]

        assert elem.properties.get("mark_negatives") is True
        assert elem.properties.get("open_button") is True
        assert elem.properties.get("auto_mark_incomplete") is True

    def test_button_properties_from_yaml(self, temp_dir):
        """Button v2.71.x properties parse from YAML config"""
        import yaml
        yaml_parser = importlib.import_module("1c_processor_generator.yaml_parser")

        config = {
            "processor": {"name": "TestYAML2"},
            "forms": [{
                "name": "Форма",
                "default": True,
                "commands": [
                    {"name": "ОК", "title_ru": "ОК", "handler": "ОК"}
                ],
                "elements": [{
                    "type": "Button",
                    "name": "ОККнопка",
                    "command": "ОК",
                    "default_button": True,
                    "shape_representation": "Always"
                }]
            }]
        }

        yaml_path = temp_dir / "config.yaml"
        yaml_path.write_text(yaml.dump(config, allow_unicode=True), encoding="utf-8")

        processor = yaml_parser.parse_yaml_config(yaml_path)
        form = processor.get_default_form()
        elem = form.elements[0]

        assert elem.properties.get("default_button") is True
        assert elem.properties.get("shape_representation") == "Always"

    def test_table_properties_from_yaml(self, temp_dir):
        """Table v2.71.x properties parse from YAML config"""
        import yaml
        yaml_parser = importlib.import_module("1c_processor_generator.yaml_parser")

        config = {
            "processor": {"name": "TestYAML3"},
            "tabular_sections": [{
                "name": "Товары",
                "columns": [{"name": "Наименование", "type": "string"}]
            }],
            "forms": [{
                "name": "Форма",
                "default": True,
                "elements": [{
                    "type": "Table",
                    "name": "ТоварыТаблица",
                    "tabular_section": "Товары",
                    "search_string_location": "CommandBar",
                    "selection_mode": "MultiRow"
                }]
            }]
        }

        yaml_path = temp_dir / "config.yaml"
        yaml_path.write_text(yaml.dump(config, allow_unicode=True), encoding="utf-8")

        processor = yaml_parser.parse_yaml_config(yaml_path)
        form = processor.get_default_form()
        elem = form.elements[0]

        assert elem.properties.get("search_string_location") == "CommandBar"
        assert elem.properties.get("selection_mode") == "MultiRow"
