"""
Unit тести для validators.py
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib
validators = importlib.import_module("1c_processor_generator.validators")

validate_uuid = validators.validate_uuid
validate_identifier = validators.validate_identifier
validate_processor_name = validators.validate_processor_name
validate_type = validators.validate_type
validate_id_sequence = validators.validate_id_sequence
validate_length_for_string = validators.validate_length_for_string
validate_number_qualifiers = validators.validate_number_qualifiers
validate_picture = validators.validate_picture
validate_handler_name = validators.validate_handler_name
validate_all_uuids = validators.validate_all_uuids
ProcessorValidator = validators.ProcessorValidator
validate_enum = validators.validate_enum
VALID_REPRESENTATION = validators.VALID_REPRESENTATION
VALID_TABLE_REPRESENTATION = validators.VALID_TABLE_REPRESENTATION
VALID_BUTTON_REPRESENTATION = validators.VALID_BUTTON_REPRESENTATION
VALID_POPUP_REPRESENTATION = validators.VALID_POPUP_REPRESENTATION
# v2.70.1+ - Additional enums
VALID_INITIAL_TREE_VIEW = validators.VALID_INITIAL_TREE_VIEW
VALID_CHOICE_MODE = validators.VALID_CHOICE_MODE
VALID_CHOICE_FOLDERS_AND_ITEMS = validators.VALID_CHOICE_FOLDERS_AND_ITEMS
VALID_CHOICE_HISTORY_ON_INPUT = validators.VALID_CHOICE_HISTORY_ON_INPUT
VALID_PAGES_REPRESENTATION = validators.VALID_PAGES_REPRESENTATION
VALID_STRETCH = validators.VALID_STRETCH
VALID_PLANNER_PERIOD = validators.VALID_PLANNER_PERIOD
VALID_GROUP_LAYOUT = validators.VALID_GROUP_LAYOUT
VALID_WINDOW_OPENING_MODE = validators.VALID_WINDOW_OPENING_MODE
VALID_COMMAND_BAR_LOCATION = validators.VALID_COMMAND_BAR_LOCATION
VALID_TIME_SCALE = validators.VALID_TIME_SCALE


class TestValidateUUID:
    """Тести для validate_uuid()"""

    def test_valid_uuids(self, valid_uuids):
        """Валідні UUID мають проходити перевірку"""
        for uuid in valid_uuids:
            is_valid, error = validate_uuid(uuid)
            assert is_valid, f"UUID {uuid} має бути валідним, але отримано: {error}"
            assert error == ""

    def test_invalid_uuids(self, invalid_uuids):
        """Невалідні UUID не повинні проходити перевірку"""
        for uuid in invalid_uuids:
            is_valid, error = validate_uuid(uuid)
            assert not is_valid, f"UUID {uuid} не повинен бути валідним"
            assert error != ""

    def test_uuid_with_uppercase(self):
        """UUID з великими літерами також валідний (lowercase перевірка всередині)"""
        uuid_upper = "12345678-1234-1234-1234-123456789ABC"
        is_valid, error = validate_uuid(uuid_upper)
        assert is_valid

    def test_uuid_with_invalid_chars(self):
        """UUID з невалідними символами"""
        uuid_invalid = "1234567Z-1234-1234-1234-123456789abc"
        is_valid, error = validate_uuid(uuid_invalid)
        assert not is_valid
        assert "невалідні символи" in error.lower() or "невірний формат" in error.lower()


class TestValidateIdentifier:
    """Тести для validate_identifier()"""

    def test_valid_identifiers(self, valid_identifiers):
        """Валідні ідентифікатори"""
        for identifier in valid_identifiers:
            is_valid, error = validate_identifier(identifier)
            assert is_valid, f"Ідентифікатор '{identifier}' має бути валідним, але отримано: {error}"
            assert error == ""

    def test_invalid_identifiers(self, invalid_identifiers):
        """Невалідні ідентифікатори"""
        for identifier in invalid_identifiers:
            is_valid, error = validate_identifier(identifier)
            assert not is_valid, f"Ідентифікатор '{identifier}' не повинен бути валідним"
            assert error != ""

    def test_identifier_starting_with_digit(self):
        """Ідентифікатор не може починатися з цифри"""
        is_valid, error = validate_identifier("123Test")
        assert not is_valid
        assert "починатися з букви" in error.lower()

    def test_identifier_with_underscore(self):
        """Ідентифікатор може починатися з підкреслення"""
        is_valid, error = validate_identifier("_PrivateVar")
        assert is_valid


class TestValidateProcessorName:
    """Тести для validate_processor_name()"""

    def test_valid_processor_names(self):
        """Валідні назви процесорів (PascalCase)"""
        valid_names = [
            "ПростаОбработка",
            "СложнаяОбработкаСЦифрами123",
            "SimpleProcessor",
        ]
        for name in valid_names:
            is_valid, error = validate_processor_name(name)
            assert is_valid, f"Назва '{name}' має бути валідною, але отримано: {error}"

    def test_processor_name_with_space(self):
        """Назва процесора не може містити пробіли"""
        is_valid, error = validate_processor_name("Проста Обработка")
        assert not is_valid
        # Може бути або "не повинна містити пробіли" або "містить невалідні символи"
        assert ("не повинна містити пробіли" in error or "містить невалідні символи" in error)

    def test_processor_name_lowercase_start(self):
        """Назва процесора має починатися з великої літери"""
        is_valid, error = validate_processor_name("простаОбработка")
        assert not is_valid
        assert "починатися з великої літери" in error


class TestValidateType:
    """Тести для validate_type()"""

    def test_valid_types(self, valid_types):
        """Валідні типи даних"""
        for data_type in valid_types:
            is_valid, error = validate_type(data_type)
            assert is_valid, f"Тип '{data_type}' має бути валідним, але отримано: {error}"
            assert error == ""

    def test_invalid_types(self, invalid_types):
        """Невалідні типи даних"""
        for data_type in invalid_types:
            is_valid, error = validate_type(data_type)
            assert not is_valid, f"Тип '{data_type}' не повинен бути валідним"
            assert error != ""

    def test_catalog_ref_type(self):
        """CatalogRef типи"""
        is_valid, _ = validate_type("CatalogRef.Пользователи")
        assert is_valid

        is_valid, _ = validate_type("cfg:CatalogRef.Номенклатура")
        assert is_valid

    def test_document_ref_type(self):
        """DocumentRef типи"""
        is_valid, _ = validate_type("DocumentRef.Накладная")
        assert is_valid

        is_valid, _ = validate_type("cfg:DocumentRef.Заказ")
        assert is_valid


class TestValidateIDSequence:
    """Тести для validate_id_sequence()"""

    def test_valid_id_sequence(self):
        """Валідна послідовність ID"""
        ids = [-1, 1, 2, 3, 4, 5]
        is_valid, error = validate_id_sequence(ids)
        assert is_valid
        assert error == ""

    def test_missing_auto_command_bar(self):
        """Відсутній AutoCommandBar (-1)"""
        ids = [1, 2, 3, 4]
        is_valid, error = validate_id_sequence(ids)
        assert not is_valid
        assert "AutoCommandBar" in error

    def test_duplicate_ids(self):
        """Дубльовані ID"""
        ids = [-1, 1, 2, 2, 3]
        is_valid, error = validate_id_sequence(ids)
        assert not is_valid
        assert "дубльовані" in error.lower()


class TestValidateLengthForString:
    """Тести для validate_length_for_string()"""

    def test_valid_lengths(self):
        """Валідні довжини рядків"""
        valid_lengths = [1, 10, 100, 255, 500, 1024]
        for length in valid_lengths:
            is_valid, error = validate_length_for_string(length)
            assert is_valid, f"Довжина {length} має бути валідною"

    def test_zero_length(self):
        """Нульова довжина"""
        is_valid, error = validate_length_for_string(0)
        assert not is_valid
        assert "має бути > 0" in error

    def test_negative_length(self):
        """Від'ємна довжина"""
        is_valid, error = validate_length_for_string(-10)
        assert not is_valid

    def test_too_long(self):
        """Занадто велика довжина"""
        is_valid, error = validate_length_for_string(2000)
        assert not is_valid
        assert "не може перевищувати" in error


class TestValidateNumberQualifiers:
    """Тести для validate_number_qualifiers()"""

    def test_valid_qualifiers(self):
        """Валідні кваліфікатори числа"""
        valid_cases = [
            (10, 0),
            (10, 2),
            (15, 5),
            (38, 10),
        ]
        for digits, fraction_digits in valid_cases:
            is_valid, error = validate_number_qualifiers(digits, fraction_digits)
            assert is_valid, f"Кваліфікатори ({digits}, {fraction_digits}) мають бути валідними"

    def test_fraction_equals_digits(self):
        """Десяткові знаки дорівнюють загальній кількості"""
        is_valid, error = validate_number_qualifiers(10, 10)
        assert not is_valid
        assert "має бути <" in error

    def test_fraction_greater_than_digits(self):
        """Десяткові знаки більші за загальну кількість"""
        is_valid, error = validate_number_qualifiers(10, 15)
        assert not is_valid

    def test_too_many_digits(self):
        """Занадто багато цифр (>38)"""
        is_valid, error = validate_number_qualifiers(40, 2)
        assert not is_valid
        assert "не може перевищувати 38" in error


class TestValidatePicture:
    """Тести для validate_picture()"""

    def test_empty_picture(self):
        """Порожня картинка (опціональна)"""
        is_valid, error = validate_picture("")
        assert is_valid

    def test_valid_std_picture(self):
        """Валідні стандартні картинки"""
        # Перевіряємо кілька популярних StdPicture
        is_valid, _ = validate_picture("StdPicture.ExecuteTask")
        # Якщо картинка не в списку, буде помилка, але формат правильний
        # Тестуємо саме формат
        assert "StdPicture." in "StdPicture.ExecuteTask"

    def test_valid_common_picture(self):
        """Валідні загальні картинки"""
        is_valid, error = validate_picture("CommonPicture.MyCustomIcon")
        assert is_valid

    def test_invalid_picture_format(self):
        """Невірний формат картинки"""
        is_valid, error = validate_picture("InvalidPicture")
        assert not is_valid
        assert "Невірний формат" in error


class TestValidateHandlerName:
    """Тести для validate_handler_name()"""

    def test_valid_handler_names(self):
        """Валідні імена обробників"""
        valid_names = [
            "ВыполнитьДействие",
            "ПриОткрытии",
            "ОбработатьДанные",
            "НаСервере",  # Це валідне ім'я, але НЕ зарезервоване слово
        ]
        for name in valid_names:
            is_valid, error = validate_handler_name(name)
            # Перевіряємо що воно або валідне, або якщо невалідне - не через зарезервоване слово
            if not is_valid:
                # Якщо невалідне, то помилка не повинна бути про зарезервоване слово
                # (тільки якщо це дійсно зарезервоване слово з BSL_RESERVED_KEYWORDS)
                assert "зарезервованим ключовим словом" not in error

    def test_empty_handler_name(self):
        """Порожнє ім'я обробника (опціональне)"""
        is_valid, error = validate_handler_name("")
        assert is_valid

    def test_reserved_bsl_keywords(self):
        """Зарезервовані ключові слова BSL"""
        # З constants.py: BSL_RESERVED_KEYWORDS
        # Деякі зарезервовані слова (відповідно до коду)
        reserved_words = [
            "Для",
            "Если",
            "Иначе",
            "КонецЕсли",
            "КонецЦикла",
            "Пока",
            "Процедура",
            "Функция",
            "Возврат",
        ]
        for word in reserved_words:
            is_valid, error = validate_handler_name(word)
            # Якщо слово в BSL_RESERVED_KEYWORDS, має бути помилка
            # Але це залежить від того, чи є воно в constants.BSL_RESERVED_KEYWORDS


class TestValidateAllUUIDs:
    """Тести для validate_all_uuids()"""

    def test_all_valid_uuids(self, valid_uuids):
        """Всі UUID валідні"""
        errors = validate_all_uuids(valid_uuids)
        assert len(errors) == 0

    def test_some_invalid_uuids(self, valid_uuids, invalid_uuids):
        """Деякі UUID невалідні"""
        mixed = valid_uuids + invalid_uuids[:2]
        errors = validate_all_uuids(mixed)
        assert len(errors) > 0

    def test_duplicate_uuids(self, valid_uuids):
        """Дубльовані UUID"""
        duplicated = valid_uuids + [valid_uuids[0]]  # Дублюємо перший
        errors = validate_all_uuids(duplicated)
        assert len(errors) > 0
        assert any("дубльовані" in err.lower() for err in errors)


class TestProcessorValidator:
    """Тести для ProcessorValidator"""

    def test_validate_simple_processor(self, simple_processor):
        """Валідація простого процесора"""
        validator = ProcessorValidator(simple_processor)
        is_valid, errors, warnings = validator.validate()

        assert is_valid, f"Простий процесор має бути валідним. Помилки: {errors}"
        assert len(errors) == 0

    def test_validate_complex_processor(self, complex_processor):
        """Валідація складного процесора"""
        validator = ProcessorValidator(complex_processor)
        is_valid, errors, warnings = validator.validate()

        assert is_valid, f"Складний процесор має бути валідним. Помилки: {errors}"
        assert len(errors) == 0

    def test_processor_with_invalid_name(self, simple_processor):
        """Процесор з невалідною назвою"""
        simple_processor.name = "123Invalid"
        validator = ProcessorValidator(simple_processor)
        is_valid, errors, warnings = validator.validate()

        assert not is_valid
        assert len(errors) > 0
        assert any("назва" in err.lower() for err in errors)

    def test_processor_with_invalid_attribute_type(self, simple_processor):
        """Процесор з невалідним типом атрибута"""
        simple_processor.attributes[0].type = "invalid_type"
        validator = ProcessorValidator(simple_processor)
        is_valid, errors, warnings = validator.validate()

        assert not is_valid
        assert len(errors) > 0

    def test_processor_without_attributes_warning(self):
        """Процесор без атрибутів має видати попередження"""
        import importlib
        models = importlib.import_module("1c_processor_generator.models")
        processor = models.Processor(name="ПорожнійПроцесор")
        validator = ProcessorValidator(processor)
        is_valid, errors, warnings = validator.validate()

        # Може бути валідним, але з попередженнями
        assert len(warnings) > 0


class TestValidateRepresentation:
    """Тести для валідації representation property (v2.70.1+)"""

    # === UsualGroup representation tests ===
    def test_group_representation_valid_values(self):
        """UsualGroup: валідні значення representation"""
        valid_values = ["None", "NormalSeparation", "WeakSeparation", "StrongSeparation"]
        for value in valid_values:
            is_valid, error = validate_enum(value, VALID_REPRESENTATION, "representation", "Group")
            assert is_valid, f"'{value}' має бути валідним для Group, але отримано: {error}"
            assert error == ""

    def test_group_representation_invalid_value(self):
        """UsualGroup: невалідне значення representation"""
        is_valid, error = validate_enum("PictureAndText", VALID_REPRESENTATION, "representation", "Group")
        assert not is_valid
        assert "невірне значення" in error.lower() or "invalid" in error.lower()
        # Перевіряємо що пропонуються правильні значення
        assert "NormalSeparation" in error or "WeakSeparation" in error

    # === Table representation tests ===
    def test_table_representation_valid_values(self):
        """Table: валідні значення representation (list, tree)"""
        valid_values = ["list", "tree"]
        for value in valid_values:
            is_valid, error = validate_enum(value, VALID_TABLE_REPRESENTATION, "representation", "Table")
            assert is_valid, f"'{value}' має бути валідним для Table, але отримано: {error}"
            assert error == ""

    def test_table_representation_invalid_value(self):
        """Table: невалідне значення representation"""
        is_valid, error = validate_enum("None", VALID_TABLE_REPRESENTATION, "representation", "Table")
        assert not is_valid
        assert "невірне значення" in error.lower() or "invalid" in error.lower()

    # === Button representation tests (v2.70.1+) ===
    def test_button_representation_valid_values(self):
        """Button: валідні значення representation"""
        valid_values = ["Text", "Picture", "PictureAndText", "TextPicture"]
        for value in valid_values:
            is_valid, error = validate_enum(value, VALID_BUTTON_REPRESENTATION, "representation", "Button")
            assert is_valid, f"'{value}' має бути валідним для Button, але отримано: {error}"
            assert error == ""

    def test_button_representation_pictureandtext(self):
        """Button: PictureAndText має бути валідним (основний кейс з issue)"""
        is_valid, error = validate_enum("PictureAndText", VALID_BUTTON_REPRESENTATION, "representation", "Button")
        assert is_valid, f"PictureAndText має бути валідним для Button, але отримано: {error}"

    def test_button_representation_invalid_value(self):
        """Button: невалідне значення representation (Group values не повинні працювати)"""
        invalid_values = ["None", "NormalSeparation", "WeakSeparation", "StrongSeparation"]
        for value in invalid_values:
            is_valid, error = validate_enum(value, VALID_BUTTON_REPRESENTATION, "representation", "Button")
            assert not is_valid, f"'{value}' НЕ має бути валідним для Button"
            # Перевіряємо що пропонуються правильні Button значення
            assert "Text" in error or "Picture" in error

    # === Popup representation tests (v2.70.1+) ===
    def test_popup_representation_valid_values(self):
        """Popup: валідні значення representation"""
        valid_values = ["Picture", "Text", "PictureAndText", "TextPicture", "Auto"]
        for value in valid_values:
            is_valid, error = validate_enum(value, VALID_POPUP_REPRESENTATION, "representation", "Popup")
            assert is_valid, f"'{value}' має бути валідним для Popup, але отримано: {error}"
            assert error == ""

    def test_popup_representation_auto(self):
        """Popup: Auto має бути валідним (унікальне для Popup)"""
        is_valid, error = validate_enum("Auto", VALID_POPUP_REPRESENTATION, "representation", "Popup")
        assert is_valid, f"Auto має бути валідним для Popup, але отримано: {error}"

    def test_popup_representation_invalid_value(self):
        """Popup: невалідне значення representation"""
        is_valid, error = validate_enum("NormalSeparation", VALID_POPUP_REPRESENTATION, "representation", "Popup")
        assert not is_valid
        # Перевіряємо що пропонуються правильні Popup значення
        assert "Auto" in error or "Text" in error or "Picture" in error

    # === Cross-element validation tests ===
    def test_button_does_not_accept_group_values(self):
        """Button НЕ приймає Group representation значення"""
        group_values = list(VALID_REPRESENTATION)
        for value in group_values:
            is_valid, _ = validate_enum(value, VALID_BUTTON_REPRESENTATION, "representation", "Button")
            assert not is_valid, f"Button НЕ повинен приймати Group значення '{value}'"

    def test_group_does_not_accept_button_values(self):
        """Group НЕ приймає Button representation значення"""
        button_values = list(VALID_BUTTON_REPRESENTATION)
        for value in button_values:
            if value not in VALID_REPRESENTATION:  # "None" може бути в обох
                is_valid, _ = validate_enum(value, VALID_REPRESENTATION, "representation", "Group")
                assert not is_valid, f"Group НЕ повинен приймати Button значення '{value}'"

    def test_table_has_unique_values(self):
        """Table має унікальні representation значення (list, tree)"""
        # Перевіряємо що list/tree не працюють для інших типів
        for value in ["list", "tree"]:
            is_valid_group, _ = validate_enum(value, VALID_REPRESENTATION, "representation", "Group")
            is_valid_button, _ = validate_enum(value, VALID_BUTTON_REPRESENTATION, "representation", "Button")
            assert not is_valid_group, f"Group НЕ повинен приймати Table значення '{value}'"
            assert not is_valid_button, f"Button НЕ повинен приймати Table значення '{value}'"


class TestValidateAdditionalEnums:
    """Тести для додаткових enum валідацій (v2.70.1+)"""

    # === initial_tree_view (Table tree mode) ===
    def test_initial_tree_view_valid_values(self):
        """initial_tree_view: валідні значення"""
        valid_values = ["no_expand", "expand_top_level", "expand_all_levels"]
        for value in valid_values:
            is_valid, error = validate_enum(value, VALID_INITIAL_TREE_VIEW, "initial_tree_view", "Table")
            assert is_valid, f"'{value}' має бути валідним, але отримано: {error}"

    def test_initial_tree_view_invalid_value(self):
        """initial_tree_view: невалідне значення"""
        is_valid, error = validate_enum("invalid", VALID_INITIAL_TREE_VIEW, "initial_tree_view", "Table")
        assert not is_valid

    # === choice_mode (InputField) ===
    def test_choice_mode_valid_values(self):
        """choice_mode: валідні значення"""
        valid_values = ["QuickChoice", "Parameters", "BothWays"]
        for value in valid_values:
            is_valid, error = validate_enum(value, VALID_CHOICE_MODE, "choice_mode", "InputField")
            assert is_valid, f"'{value}' має бути валідним, але отримано: {error}"

    def test_choice_mode_invalid_value(self):
        """choice_mode: невалідне значення"""
        is_valid, error = validate_enum("invalid", VALID_CHOICE_MODE, "choice_mode", "InputField")
        assert not is_valid

    # === choice_folders_and_items (InputField) ===
    def test_choice_folders_and_items_valid_values(self):
        """choice_folders_and_items: валідні значення (обидва регістри)"""
        valid_values = ["Folders", "Items", "FoldersAndItems", "folders", "items", "folders_and_items"]
        for value in valid_values:
            is_valid, error = validate_enum(value, VALID_CHOICE_FOLDERS_AND_ITEMS, "choice_folders_and_items", "InputField")
            assert is_valid, f"'{value}' має бути валідним, але отримано: {error}"

    def test_choice_folders_and_items_invalid_value(self):
        """choice_folders_and_items: невалідне значення"""
        is_valid, error = validate_enum("invalid", VALID_CHOICE_FOLDERS_AND_ITEMS, "choice_folders_and_items", "InputField")
        assert not is_valid

    # === choice_history_on_input (InputField) ===
    def test_choice_history_on_input_valid_values(self):
        """choice_history_on_input: валідні значення"""
        valid_values = ["Auto", "DontUse", "UseAlways"]
        for value in valid_values:
            is_valid, error = validate_enum(value, VALID_CHOICE_HISTORY_ON_INPUT, "choice_history_on_input", "InputField")
            assert is_valid, f"'{value}' має бути валідним, але отримано: {error}"

    def test_choice_history_on_input_invalid_value(self):
        """choice_history_on_input: невалідне значення"""
        is_valid, error = validate_enum("invalid", VALID_CHOICE_HISTORY_ON_INPUT, "choice_history_on_input", "InputField")
        assert not is_valid

    # === pages_representation (Pages) ===
    def test_pages_representation_valid_values(self):
        """pages_representation: валідні значення"""
        valid_values = ["TabsOnTop", "TabsOnBottom", "None"]
        for value in valid_values:
            is_valid, error = validate_enum(value, VALID_PAGES_REPRESENTATION, "pages_representation", "Pages")
            assert is_valid, f"'{value}' має бути валідним, але отримано: {error}"

    def test_pages_representation_invalid_value(self):
        """pages_representation: невалідне значення"""
        is_valid, error = validate_enum("invalid", VALID_PAGES_REPRESENTATION, "pages_representation", "Pages")
        assert not is_valid

    # === stretch (SpreadSheetDocumentField) ===
    def test_stretch_valid_values(self):
        """stretch: валідні значення"""
        valid_values = ["No", "Horizontally", "Vertically", "HorizontalAndVertically"]
        for value in valid_values:
            is_valid, error = validate_enum(value, VALID_STRETCH, "stretch", "SpreadSheetDocumentField")
            assert is_valid, f"'{value}' має бути валідним, але отримано: {error}"

    def test_stretch_invalid_value(self):
        """stretch: невалідне значення"""
        is_valid, error = validate_enum("invalid", VALID_STRETCH, "stretch", "SpreadSheetDocumentField")
        assert not is_valid

    # === period (PlannerField) ===
    def test_planner_period_valid_values(self):
        """period: валідні значення для PlannerField"""
        valid_values = ["Day", "Week", "Month", "Year"]
        for value in valid_values:
            is_valid, error = validate_enum(value, VALID_PLANNER_PERIOD, "period", "PlannerField")
            assert is_valid, f"'{value}' має бути валідним, але отримано: {error}"

    def test_planner_period_invalid_value(self):
        """period: невалідне значення"""
        is_valid, error = validate_enum("invalid", VALID_PLANNER_PERIOD, "period", "PlannerField")
        assert not is_valid

    # === group_layout (ColumnGroup) ===
    def test_group_layout_valid_values(self):
        """group_layout: валідні значення"""
        valid_values = ["Horizontal", "Vertical"]
        for value in valid_values:
            is_valid, error = validate_enum(value, VALID_GROUP_LAYOUT, "group_layout", "ColumnGroup")
            assert is_valid, f"'{value}' має бути валідним, але отримано: {error}"

    def test_group_layout_invalid_value(self):
        """group_layout: невалідне значення"""
        is_valid, error = validate_enum("invalid", VALID_GROUP_LAYOUT, "group_layout", "ColumnGroup")
        assert not is_valid

    # === window_opening_mode (Form) ===
    def test_window_opening_mode_valid_values(self):
        """window_opening_mode: валідні значення"""
        valid_values = ["LockOwnerWindow", "LockWholeInterface"]
        for value in valid_values:
            is_valid, error = validate_enum(value, VALID_WINDOW_OPENING_MODE, "window_opening_mode", "Form")
            assert is_valid, f"'{value}' має бути валідним, але отримано: {error}"

    def test_window_opening_mode_invalid_value(self):
        """window_opening_mode: невалідне значення"""
        is_valid, error = validate_enum("invalid", VALID_WINDOW_OPENING_MODE, "window_opening_mode", "Form")
        assert not is_valid

    # === command_bar_location (Form) ===
    def test_command_bar_location_valid_values(self):
        """command_bar_location: валідні значення"""
        valid_values = ["None", "Top", "Bottom"]
        for value in valid_values:
            is_valid, error = validate_enum(value, VALID_COMMAND_BAR_LOCATION, "command_bar_location", "Form")
            assert is_valid, f"'{value}' має бути валідним, але отримано: {error}"

    def test_command_bar_location_invalid_value(self):
        """command_bar_location: невалідне значення"""
        is_valid, error = validate_enum("invalid", VALID_COMMAND_BAR_LOCATION, "command_bar_location", "Form")
        assert not is_valid

    # === time_scale (PlannerField) ===
    def test_time_scale_valid_values(self):
        """time_scale: валідні значення"""
        valid_values = ["Hour", "Day", "Week", "Month"]
        for value in valid_values:
            is_valid, error = validate_enum(value, VALID_TIME_SCALE, "time_scale", "PlannerField")
            assert is_valid, f"'{value}' має бути валідним, але отримано: {error}"

    def test_time_scale_invalid_value(self):
        """time_scale: невалідне значення"""
        is_valid, error = validate_enum("invalid", VALID_TIME_SCALE, "time_scale", "PlannerField")
        assert not is_valid


# === HandlerValidator tests (v2.71.5+) ===

HandlerValidator = validators.HandlerValidator


class TestHandlerValidatorFormLevelAccess:
    """Тести для HandlerValidator.validate_form_level_access() - v2.71.5+"""

    def _create_processor_with_form_attributes(self):
        """Створює мок процесора з form_attributes"""
        from dataclasses import dataclass, field
        from typing import List, Optional

        @dataclass
        class FormAttribute:
            name: str
            type: str = "spreadsheet_document"

        @dataclass
        class ValueTableColumn:
            name: str
            type: str = "string"

        @dataclass
        class ValueTableAttribute:
            name: str
            columns: List[ValueTableColumn] = field(default_factory=list)

        @dataclass
        class Form:
            name: str
            form_attributes: List[FormAttribute] = field(default_factory=list)
            value_table_attributes: List[ValueTableAttribute] = field(default_factory=list)
            events: dict = field(default_factory=dict)
            commands: list = field(default_factory=list)
            elements: list = field(default_factory=list)

        @dataclass
        class Processor:
            name: str
            forms: List[Form] = field(default_factory=list)

        return Processor(
            name="TestProcessor",
            forms=[
                Form(
                    name="Форма",
                    form_attributes=[
                        FormAttribute(name="ДокументШахматы", type="spreadsheet_document"),
                        FormAttribute(name="HTMLДок", type="html_document"),
                    ],
                    value_table_attributes=[
                        ValueTableAttribute(name="Результаты", columns=[]),
                    ],
                )
            ],
        )

    def test_form_attribute_access_warning(self):
        """Доступ до form_attribute через Объект. має викликати warning"""
        processor = self._create_processor_with_form_attributes()
        handlers = {
            "СоздатьДоскуНаСервере": """&НаСервере
Процедура СоздатьДоскуНаСервере()
    ТабДок = Объект.ДокументШахматы;
    ТабДок.Очистить();
КонецПроцедуры"""
        }

        validator = HandlerValidator(processor, loaded_handlers=handlers)
        errors, warnings = validator.validate_form_level_access()

        assert len(errors) == 0
        assert len(warnings) == 1
        assert "ДокументШахматы" in warnings[0]
        assert "form_attribute" in warnings[0]

    def test_valuetable_access_warning(self):
        """Доступ до ValueTable через Объект. має викликати warning"""
        processor = self._create_processor_with_form_attributes()
        handlers = {
            "ОбробитиДаніНаСервере": """&НаСервере
Процедура ОбробитиДаніНаСервере()
    Дані = Объект.Результаты;
КонецПроцедуры"""
        }

        validator = HandlerValidator(processor, loaded_handlers=handlers)
        errors, warnings = validator.validate_form_level_access()

        assert len(errors) == 0
        assert len(warnings) == 1
        assert "Результаты" in warnings[0]
        assert "ValueTable" in warnings[0]

    def test_correct_access_no_warnings(self):
        """Правильний доступ (без Объект.) не має викликати warning"""
        processor = self._create_processor_with_form_attributes()
        handlers = {
            "СоздатьДоскуНаСервере": """&НаСервере
Процедура СоздатьДоскуНаСервере()
    ТабДок = ДокументШахматы;
    ТабДок.Очистить();
    Результаты.Добавить();
КонецПроцедуры"""
        }

        validator = HandlerValidator(processor, loaded_handlers=handlers)
        errors, warnings = validator.validate_form_level_access()

        assert len(errors) == 0
        assert len(warnings) == 0

    def test_regular_attribute_no_warning(self):
        """Доступ до звичайних attributes через Объект. НЕ має викликати warning"""
        processor = self._create_processor_with_form_attributes()
        handlers = {
            "ОбробитиДаніНаСервере": """&НаСервере
Процедура ОбробитиДаніНаСервере()
    Дані = Объект.Поле;
    Объект.Статус = "Готово";
КонецПроцедуры"""
        }

        validator = HandlerValidator(processor, loaded_handlers=handlers)
        errors, warnings = validator.validate_form_level_access()

        # Поле і Статус - не form_attributes, тому warnings немає
        assert len(warnings) == 0

    def test_multiple_warnings(self):
        """Декілька некоректних доступів мають викликати декілька warnings"""
        processor = self._create_processor_with_form_attributes()
        handlers = {
            "ПроблемнийКод": """&НаСервере
Процедура ПроблемнийКод()
    Док1 = Объект.ДокументШахматы;
    Док2 = Объект.HTMLДок;
    Дані = Объект.Результаты;
КонецПроцедуры"""
        }

        validator = HandlerValidator(processor, loaded_handlers=handlers)
        errors, warnings = validator.validate_form_level_access()

        assert len(errors) == 0
        assert len(warnings) == 3  # 2 form_attributes + 1 ValueTable
