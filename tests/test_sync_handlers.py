"""
Tests for sync handlers (v2.42.0+).

Tests the new handler-based sync architecture.
"""

import pytest
from unittest.mock import MagicMock


class TestHandlerRegistry:
    """Tests for HandlerRegistry."""

    def test_registry_singleton(self):
        """Test that registry is a singleton."""
        import importlib
        sync = importlib.import_module('1c_processor_generator.sync')

        r1 = sync.HandlerRegistry.instance()
        r2 = sync.HandlerRegistry.instance()

        assert r1 is r2

    def test_all_handlers_registered(self):
        """Test that all expected handlers are registered."""
        import importlib
        sync = importlib.import_module('1c_processor_generator.sync')

        registry = sync.HandlerRegistry.instance()

        expected_handlers = [
            'attribute',
            'form_element',
            'command',
            'tabular_section',
            'value_table',
            'form_attribute',
            'form',
            'template',        # NEW in v2.42.0
            'form_parameter',  # NEW in v2.42.0
        ]

        for handler_name in expected_handlers:
            assert handler_name in registry, f"Handler '{handler_name}' not registered"

    def test_get_handler(self):
        """Test getting handler by name."""
        import importlib
        sync = importlib.import_module('1c_processor_generator.sync')

        registry = sync.HandlerRegistry.instance()

        handler = registry.get('attribute')
        assert handler is not None
        assert handler.element_type_name == 'attribute'

    def test_get_unknown_handler(self):
        """Test getting unknown handler returns None."""
        import importlib
        sync = importlib.import_module('1c_processor_generator.sync')

        registry = sync.HandlerRegistry.instance()

        handler = registry.get('unknown_type')
        assert handler is None


class TestAttributeHandler:
    """Tests for AttributeHandler."""

    def test_element_type_name(self):
        """Test element type name."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.AttributeHandler()
        assert handler.element_type_name == 'attribute'

    def test_yaml_section(self):
        """Test YAML section."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.AttributeHandler()
        assert handler.yaml_section == 'attributes'

    def test_is_form_level(self):
        """Test that attribute is processor-level."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.AttributeHandler()
        assert handler.is_form_level is False

    def test_add_to_yaml(self):
        """Test adding attribute to YAML config."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.AttributeHandler()
        config = {'attributes': []}

        result = handler.add_to_yaml(config, {'name': 'TestAttr', 'type': 'string'})

        assert result is True
        assert len(config['attributes']) == 1
        assert config['attributes'][0]['name'] == 'TestAttr'

    def test_add_duplicate_attribute(self):
        """Test that adding duplicate attribute fails."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.AttributeHandler()
        config = {'attributes': [{'name': 'TestAttr', 'type': 'string'}]}

        result = handler.add_to_yaml(config, {'name': 'TestAttr', 'type': 'number'})

        assert result is False
        assert len(config['attributes']) == 1

    def test_delete_from_yaml(self):
        """Test deleting attribute from YAML config."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.AttributeHandler()
        config = {'attributes': [{'name': 'ToDelete', 'type': 'string'}]}

        result = handler.delete_from_yaml(config, 'ToDelete')

        assert result is True
        assert len(config['attributes']) == 0

    def test_check_references(self):
        """Test reference checking."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.AttributeHandler()
        config = {
            'forms': [{
                'elements': [{'name': 'Field1', 'attribute': 'TestAttr'}]
            }]
        }
        bsl_code = 'Объект.TestAttr = 123;'

        refs = handler.check_references(config, bsl_code, 'TestAttr')

        assert len(refs) == 2  # BSL + form element


class TestTemplateHandler:
    """Tests for TemplateHandler (v2.42.0+)."""

    def test_element_type_name(self):
        """Test element type name."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.TemplateHandler()
        assert handler.element_type_name == 'template'

    def test_yaml_section(self):
        """Test YAML section."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.TemplateHandler()
        assert handler.yaml_section == 'templates'

    def test_is_form_level(self):
        """Test that template is processor-level."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.TemplateHandler()
        assert handler.is_form_level is False

    def test_add_to_yaml(self):
        """Test adding template to YAML config."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.TemplateHandler()
        config = {}

        result = handler.add_to_yaml(config, {
            'name': 'Dashboard',
            'type': 'HTMLDocument'
        })

        assert result is True
        assert 'templates' in config
        assert len(config['templates']) == 1
        assert config['templates'][0]['name'] == 'Dashboard'
        assert config['templates'][0]['type'] == 'HTMLDocument'

    def test_add_duplicate_template(self):
        """Test that adding duplicate template fails."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.TemplateHandler()
        config = {'templates': [{'name': 'Dashboard', 'type': 'HTMLDocument'}]}

        result = handler.add_to_yaml(config, {'name': 'Dashboard', 'type': 'SpreadsheetDocument'})

        assert result is False
        assert len(config['templates']) == 1

    def test_delete_from_yaml(self):
        """Test deleting template from YAML config."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.TemplateHandler()
        config = {'templates': [{'name': 'ToDelete', 'type': 'HTMLDocument'}]}

        result = handler.delete_from_yaml(config, 'ToDelete')

        assert result is True
        assert len(config['templates']) == 0

    def test_check_references_bsl(self):
        """Test reference checking for BSL."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.TemplateHandler()
        config = {'templates': [{'name': 'Report', 'type': 'SpreadsheetDocument'}]}
        bsl_code = 'Макет = ПолучитьМакет("Report");'

        refs = handler.check_references(config, bsl_code, 'Report')

        assert len(refs) >= 1
        assert any('BSL' in ref for ref in refs)

    def test_check_references_auto_field(self):
        """Test reference checking for auto_field templates."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.TemplateHandler()
        config = {'templates': [{
            'name': 'Card',
            'type': 'HTMLDocument',
            'auto_field': True,
            'field_name': 'CardPreview'
        }]}

        refs = handler.check_references(config, '', 'Card')

        assert len(refs) >= 1
        assert any('auto_field' in ref for ref in refs)


class TestFormParameterHandler:
    """Tests for FormParameterHandler (v2.42.0+)."""

    def test_element_type_name(self):
        """Test element type name."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.FormParameterHandler()
        assert handler.element_type_name == 'form_parameter'

    def test_yaml_section(self):
        """Test YAML section."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.FormParameterHandler()
        assert handler.yaml_section == 'forms[].parameters'

    def test_is_form_level(self):
        """Test that form parameter is form-level."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.FormParameterHandler()
        assert handler.is_form_level is True

    def test_add_to_yaml(self):
        """Test adding form parameter to YAML config."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.FormParameterHandler()
        config = {'forms': [{'name': 'Форма'}]}

        result = handler.add_to_yaml(config, {
            'name': 'FilterDate',
            'type': 'date',
            'key_parameter': True
        }, form_index=0)

        assert result is True
        assert 'parameters' in config['forms'][0]
        assert len(config['forms'][0]['parameters']) == 1
        assert config['forms'][0]['parameters'][0]['name'] == 'FilterDate'

    def test_add_duplicate_parameter(self):
        """Test that adding duplicate parameter fails."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.FormParameterHandler()
        config = {'forms': [{'name': 'Форма', 'parameters': [
            {'name': 'FilterDate', 'type': 'date'}
        ]}]}

        result = handler.add_to_yaml(config, {'name': 'FilterDate', 'type': 'string'}, form_index=0)

        assert result is False
        assert len(config['forms'][0]['parameters']) == 1

    def test_add_to_nonexistent_form(self):
        """Test adding parameter to nonexistent form fails."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.FormParameterHandler()
        config = {'forms': []}

        result = handler.add_to_yaml(config, {'name': 'Param1', 'type': 'string'}, form_index=0)

        assert result is False

    def test_delete_from_yaml(self):
        """Test deleting form parameter from YAML config."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.FormParameterHandler()
        config = {'forms': [{'name': 'Форма', 'parameters': [
            {'name': 'ToDelete', 'type': 'date'}
        ]}]}

        result = handler.delete_from_yaml(config, 'ToDelete', form_index=0)

        assert result is True
        assert len(config['forms'][0]['parameters']) == 0

    def test_check_references(self):
        """Test reference checking for BSL."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.FormParameterHandler()
        config = {}
        bsl_code = 'Если Параметры.FilterDate <> Неопределено Тогда'

        refs = handler.check_references(config, bsl_code, 'FilterDate')

        assert len(refs) >= 1
        assert any('BSL' in ref for ref in refs)


class TestFormElementHandler:
    """Tests for FormElementHandler."""

    def test_supports_nesting(self):
        """Test that form elements support nesting."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.FormElementHandler()
        assert handler.supports_nesting is True

    def test_is_form_level(self):
        """Test that form elements are form-level."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.FormElementHandler()
        assert handler.is_form_level is True

    def test_tag_to_type_mapping(self):
        """Test XML tag to YAML type conversion (v2.42.0+)."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.FormElementHandler()

        # Test known mappings
        assert handler._tag_to_type('InputField') == 'InputField'
        assert handler._tag_to_type('UsualGroup') == 'Group'
        assert handler._tag_to_type('LabelDecoration') == 'LabelDecoration'
        assert handler._tag_to_type('HTMLDocumentField') == 'HTMLDocumentField'
        assert handler._tag_to_type('ColumnGroup') == 'ColumnGroup'

        # Test unknown tag (pass-through)
        assert handler._tag_to_type('UnknownType') == 'UnknownType'

    def test_get_property_int(self):
        """Test integer property extraction (v2.42.0+)."""
        import importlib
        from lxml import etree

        handlers = importlib.import_module('1c_processor_generator.sync.handlers')
        handler = handlers.FormElementHandler()

        # Create mock XML element with Width
        xml = """<InputField name="Test">
            <Width>150</Width>
        </InputField>"""
        elem = etree.fromstring(xml)

        # Test extraction
        width = handler._get_property(elem, "Width", "int")
        assert width == 150

        # Test missing property
        height = handler._get_property(elem, "Height", "int")
        assert height is None

    def test_get_property_bool(self):
        """Test boolean property extraction (v2.42.0+)."""
        import importlib
        from lxml import etree

        handlers = importlib.import_module('1c_processor_generator.sync.handlers')
        handler = handlers.FormElementHandler()

        # Create mock XML element with ReadOnly
        xml = """<InputField name="Test">
            <ReadOnly>true</ReadOnly>
            <MultiLine>false</MultiLine>
        </InputField>"""
        elem = etree.fromstring(xml)

        # Test true value
        readonly = handler._get_property(elem, "ReadOnly", "bool")
        assert readonly is True

        # Test false value
        multiline = handler._get_property(elem, "MultiLine", "bool")
        assert multiline is False

    def test_get_property_enum(self):
        """Test enum property extraction (v2.42.0+)."""
        import importlib
        from lxml import etree

        handlers = importlib.import_module('1c_processor_generator.sync.handlers')
        handler = handlers.FormElementHandler()

        # Create mock XML element with ChoiceMode
        xml = """<InputField name="Test">
            <ChoiceMode>QuickChoice</ChoiceMode>
            <HorizontalAlign>Right</HorizontalAlign>
        </InputField>"""
        elem = etree.fromstring(xml)

        # Test enum extraction
        choice_mode = handler._get_property(elem, "ChoiceMode", "enum")
        assert choice_mode == "QuickChoice"

        horizontal_align = handler._get_property(elem, "HorizontalAlign", "enum")
        assert horizontal_align == "Right"

    def test_extract_font(self):
        """Test font property extraction (v2.35.1+)."""
        import importlib
        from lxml import etree

        handlers = importlib.import_module('1c_processor_generator.sync.handlers')
        handler = handlers.FormElementHandler()

        # Create mock XML element with Font
        xml = """<LabelDecoration name="Title">
            <Font bold="true" height="14" faceName="Arial"/>
        </LabelDecoration>"""
        elem = etree.fromstring(xml)

        # Test font extraction
        font = handler._extract_font(elem, {})
        assert font is not None
        assert font['bold'] is True
        assert font['size'] == 14
        assert font['face_name'] == "Arial"

    def test_extract_font_empty(self):
        """Test font extraction when no font present."""
        import importlib
        from lxml import etree

        handlers = importlib.import_module('1c_processor_generator.sync.handlers')
        handler = handlers.FormElementHandler()

        # Create mock XML element without Font
        xml = """<LabelDecoration name="Title">
            <Title>Test Label</Title>
        </LabelDecoration>"""
        elem = etree.fromstring(xml)

        # Test font extraction returns None
        font = handler._extract_font(elem, {})
        assert font is None

    def test_add_to_yaml(self):
        """Test adding form element to YAML."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.FormElementHandler()
        config = {'forms': [{'name': 'Форма', 'elements': []}]}

        result = handler.add_to_yaml(config, {
            'name': 'NewField',
            'type': 'InputField',
            'width': 200
        }, form_index=0)

        assert result is True
        assert len(config['forms'][0]['elements']) == 1
        assert config['forms'][0]['elements'][0]['name'] == 'NewField'

    def test_delete_from_yaml(self):
        """Test deleting form element from YAML."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.FormElementHandler()
        config = {'forms': [{'name': 'Форма', 'elements': [
            {'name': 'ToDelete', 'type': 'InputField'}
        ]}]}

        result = handler.delete_from_yaml(config, 'ToDelete', form_index=0)

        assert result is True
        assert len(config['forms'][0]['elements']) == 0

    def test_check_references(self):
        """Test reference checking for BSL code."""
        import importlib
        handlers = importlib.import_module('1c_processor_generator.sync.handlers')

        handler = handlers.FormElementHandler()
        config = {}
        bsl_code = 'Элементы.TestField.Видимость = Истина;'

        refs = handler.check_references(config, bsl_code, 'TestField')

        assert len(refs) >= 1
        assert any('Элементы.TestField' in ref for ref in refs)
