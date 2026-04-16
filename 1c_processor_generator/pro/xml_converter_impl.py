"""
XML Converter - конверсія та трансформація XML файлів процесорів

Модуль забезпечує трансформації:
1. ExternalDataProcessor → DataProcessor (для включення в Configuration)
2. Додавання cfg: префіксів до CatalogRef/DocumentRef типів
3. Batch конверсія всіх XML файлів в директорії

Використання:
    >>> converter = XMLConverter()
    >>> converter.convert_external_to_internal(source_xml, target_xml)
    >>> converter.add_cfg_prefix(processor_xml_path)
"""

import re
from pathlib import Path
from typing import List, Optional
import logging

try:
    # When running as compiled .pyd
    from utils import generate_uuid
except ImportError:
    # When running as part of package
    from .utils import generate_uuid

logger = logging.getLogger(__name__)


class XMLConverter:
    """
    Конвертор XML файлів процесорів.

    Надає методи для трансформації XML між різними форматами:
    - ExternalDataProcessor ↔ DataProcessor
    - Додавання cfg: namespace префіксів
    - Batch операції над директоріями

    Example:
        >>> converter = XMLConverter()
        >>> converter.convert_external_to_internal(
        ...     source=Path("External.xml"),
        ...     target=Path("Internal.xml")
        ... )
        >>> converter.add_cfg_prefix(Path("Processor.xml"))
    """

    # Regex patterns для трансформацій
    CATALOG_REF_PATTERN = re.compile(r'<v8:Type>CatalogRef\.')
    DOCUMENT_REF_PATTERN = re.compile(r'<v8:Type>DocumentRef\.')
    OBJECT_TYPE_PATTERN = re.compile(
        r'(<xr:GeneratedType name="DataProcessorObject\.([^"]+)" category="Object">.*?</xr:GeneratedType>)',
        re.DOTALL
    )
    CONTAINED_OBJECT_PATTERN = re.compile(
        r'\s*<xr:ContainedObject>.*?</xr:ContainedObject>\s*',
        re.DOTALL
    )

    def convert_external_to_internal(
        self,
        source_xml: Path,
        target_xml: Path,
        add_cfg_prefix: bool = True,
        rename_to: str = None,
        generate_new_uuid: bool = False
    ) -> None:
        """
        Конвертує ExternalDataProcessor XML в DataProcessor XML.

        ExternalDataProcessor (EPF) має тільки Object GeneratedType.
        DataProcessor (внутрішня обробка) потребує Object + Manager GeneratedType.

        Виконує трансформації:
        - ExternalDataProcessor → DataProcessor теги
        - ExternalDataProcessorObject → DataProcessorObject
        - Додавання Manager GeneratedType
        - Видалення ContainedObject з InternalInfo
        - Додавання UseStandardCommands та інших Properties
        - (опціонально) Додавання cfg: префіксів
        - (опціонально) Перейменування processor
        - (опціонально) Генерація нового UUID

        Args:
            source_xml: Шлях до вихідного ExternalDataProcessor XML
            target_xml: Шлях для збереження DataProcessor XML
            add_cfg_prefix: Чи додавати cfg: префікси до CatalogRef/DocumentRef
                           (за замовчуванням True)
            rename_to: Нова назва для DataProcessor (опціонально)
            generate_new_uuid: Чи генерувати новий UUID для DataProcessor
                              (потрібно для уникнення конфлікту з External, за замовчуванням False)

        Raises:
            FileNotFoundError: Якщо source_xml не існує

        Example:
            >>> converter = XMLConverter()
            >>> converter.convert_external_to_internal(
            ...     source_xml=Path("MyProcessor.xml"),
            ...     target_xml=Path("Configuration/DataProcessors/MyProcessor.xml"),
            ...     rename_to="MyProcessor_Validation",
            ...     generate_new_uuid=True
            ... )
        """
        if not source_xml.exists():
            raise FileNotFoundError(f"Source XML не знайдено: {source_xml}")

        logger.info(f"Конверсія ExternalDataProcessor → DataProcessor: {source_xml}")
        if rename_to:
            logger.info(f"  Перейменування: {source_xml.stem} → {rename_to}")
        if generate_new_uuid:
            logger.info(f"  Генерація нового UUID для уникнення конфлікту")

        # Читаємо вихідний XML
        content = source_xml.read_text(encoding="utf-8")

        # Генерація нового UUID (якщо потрібно) - робимо ПЕРШИМ для уникнення конфлікту
        if generate_new_uuid:
            content = self._generate_new_uuid(content)

        # Перейменування (якщо потрібно) - робимо ДО інших трансформацій
        if rename_to:
            original_name = source_xml.stem
            content = self._rename_processor(content, original_name, rename_to)

        # Генерація нових TypeId/ValueId (ПЕРЕД трансформаціями, щоб уникнути конфліктів)
        if generate_new_uuid:
            content = self._replace_generated_type_ids(content)

        # Виконуємо трансформації
        content = self._replace_tags(content)
        content = self._replace_generated_types(content)
        content = self._replace_default_form_references(content)
        content = self._add_manager_type_if_missing(content)
        content = self._remove_contained_object(content)

        if add_cfg_prefix:
            content = self._inject_cfg_prefix(content)

        content = self._add_use_standard_commands(content)
        content = self._add_additional_properties(content)

        # Записуємо конвертований файл
        target_xml.write_text(content, encoding="utf-8")

        logger.info(f"✓ Конвертовано успішно: {target_xml}")

    def add_cfg_prefix(self, processor_xml_path: Path) -> int:
        """
        Додає cfg: префікси до CatalogRef/DocumentRef у всіх XML файлах процесора.

        Модифікує XML файли рекурсивно (всі .xml файли в структурі процесора),
        додаючи cfg: namespace prefix до типів CatalogRef/DocumentRef.

        Args:
            processor_xml_path: Шлях до головного XML файлу процесора або директорії

        Returns:
            Кількість модифікованих файлів

        Example:
            >>> converter = XMLConverter()
            >>> modified_count = converter.add_cfg_prefix(Path("MyProcessor/MyProcessor.xml"))
            >>> print(f"Модифіковано {modified_count} файлів")
        """
        # Визначаємо директорію для пошуку
        if processor_xml_path.is_file():
            processor_dir = processor_xml_path.parent
        else:
            processor_dir = processor_xml_path

        # Знаходимо всі XML файли
        xml_files = list(processor_dir.rglob("*.xml"))

        logger.debug(f"Додавання cfg: префіксів до {len(xml_files)} XML файлів")

        modified_count = 0

        for xml_file in xml_files:
            try:
                content = xml_file.read_text(encoding="utf-8")

                # Перевіряємо чи потрібна модифікація
                if 'CatalogRef.' not in content and 'DocumentRef.' not in content:
                    continue

                # Додаємо cfg: префікс
                modified_content = self._inject_cfg_prefix(content)

                if modified_content != content:
                    xml_file.write_text(modified_content, encoding="utf-8")
                    modified_count += 1
                    logger.debug(f"   ✅ Додано cfg: prefix: {xml_file.relative_to(processor_dir)}")

            except Exception as e:
                logger.warning(f"Помилка обробки {xml_file}: {e}")

        logger.info(f"✓ cfg: префікси додано до {modified_count} файлів")
        return modified_count

    def convert_all_xml_in_directory(
        self,
        directory: Path,
        transformation: str = "external_to_internal",
        rename_to: str = None,
        original_name: str = None,
        generate_new_uuids: bool = False
    ) -> int:
        """
        Конвертує всі XML файли в директорії (рекурсивно).

        Args:
            directory: Директорія для обробки
            transformation: Тип трансформації:
                - "external_to_internal": ExternalDataProcessor → DataProcessor
                - "add_cfg_prefix": Додати cfg: префікси
            rename_to: Нова назва processor (опціонально)
            original_name: Оригінальна назва processor для заміни (опціонально, визначається автоматично)
            generate_new_uuids: Чи генерувати нові UUID для всіх об'єктів (процесор + форми)

        Returns:
            Кількість модифікованих файлів

        Example:
            >>> converter = XMLConverter()
            >>> count = converter.convert_all_xml_in_directory(
            ...     Path("Configuration/DataProcessors/MyProcessor_Validation"),
            ...     transformation="external_to_internal",
            ...     rename_to="MyProcessor_Validation",
            ...     original_name="MyProcessor",
            ...     generate_new_uuids=True
            ... )
        """
        xml_files = list(directory.rglob("*.xml"))
        logger.info(f"Обробка {len(xml_files)} XML файлів в {directory}")

        # Визначаємо original_name автоматично з directory (якщо rename_to передан)
        if rename_to and not original_name:
            # Витягуємо назву з suffix (наприклад, "MyProcessor_Validation" → "MyProcessor")
            if "_Validation" in rename_to:
                original_name = rename_to.replace("_Validation", "")
            else:
                logger.warning(f"Не вдалось визначити original_name для rename_to={rename_to}")

        modified_count = 0

        for xml_file in xml_files:
            try:
                content = xml_file.read_text(encoding="utf-8")
                modified = False

                if transformation == "external_to_internal":
                    # Замінюємо всі посилання ExternalDataProcessor → DataProcessor
                    # Включаючи ExternalDataProcessorObject, ExternalDataProcessorManager, etc.
                    if "ExternalDataProcessor" in content:
                        content = content.replace("ExternalDataProcessorObject", "DataProcessorObject")
                        content = content.replace("ExternalDataProcessorManager", "DataProcessorManager")
                        content = content.replace("ExternalDataProcessor", "DataProcessor")
                        modified = True

                    # Після конвертації External → Internal, додаємо cfg: префікси
                    # (Configuration DataProcessor потребує cfg: для всіх metadata типів)
                    cfg_content = self._inject_cfg_prefix(content)
                    if cfg_content != content:
                        content = cfg_content
                        modified = True

                elif transformation == "add_cfg_prefix":
                    new_content = self._inject_cfg_prefix(content)
                    if new_content != content:
                        content = new_content
                        modified = True

                # Перейменування processor (якщо потрібно)
                if rename_to and original_name:
                    old_content = content
                    content = self._rename_processor(content, original_name, rename_to)
                    if content != old_content:
                        modified = True

                # Генерація нових UUID (якщо потрібно)
                if generate_new_uuids:
                    old_content = content
                    content = self._replace_uuid_in_xml(content)
                    if content != old_content:
                        modified = True

                if modified:
                    xml_file.write_text(content, encoding="utf-8")
                    modified_count += 1
                    logger.debug(f"   ✅ Конвертовано: {xml_file.relative_to(directory)}")

            except Exception as e:
                logger.warning(f"Помилка обробки {xml_file}: {e}")

        logger.info(f"✓ Конвертовано {modified_count} файлів")
        return modified_count

    # ========================================================================
    # Private helper methods
    # ========================================================================

    def _generate_new_uuid(self, content: str) -> str:
        """
        Генерує новий UUID для DataProcessor (для уникнення конфлікту з ExternalDataProcessor).

        Замінює uuid="старий-uuid" в тегах ExternalDataProcessor/DataProcessor.

        Args:
            content: XML контент

        Returns:
            Модифікований XML з новим UUID
        """
        # Шукаємо uuid="..." в тегу ExternalDataProcessor або DataProcessor
        uuid_pattern = re.compile(r'(<(?:ExternalDataProcessor|DataProcessor)\s+uuid=")([a-f0-9\-]+)(")')
        match = uuid_pattern.search(content)

        if not match:
            logger.warning("   ⚠️ UUID не знайдено в XML, пропускаємо генерацію")
            return content

        old_uuid = match.group(2)
        new_uuid = generate_uuid()

        # Замінюємо UUID
        content = uuid_pattern.sub(rf'\g<1>{new_uuid}\g<3>', content)

        logger.info(f"   ✅ UUID замінено: {old_uuid} → {new_uuid}")

        return content

    def _replace_generated_type_ids(self, content: str) -> str:
        """
        Замінює TypeId та ValueId в GeneratedType блоках.

        КРИТИЧНО: TypeId та ValueId повинні бути УНІКАЛЬНИМИ для кожного процесора!
        Якщо Configuration має DataProcessor з TypeId=X, а External має такий же TypeId=X,
        то виникає XDTO Exception при компіляції External.

        Args:
            content: XML контент процесора

        Returns:
            Модифікований XML з новими TypeId та ValueId
        """
        # Pattern для TypeId в GeneratedType
        type_id_pattern = re.compile(r'(<xr:TypeId>)([a-f0-9\-]+)(</xr:TypeId>)')
        value_id_pattern = re.compile(r'(<xr:ValueId>)([a-f0-9\-]+)(</xr:ValueId>)')

        # Замінюємо всі TypeId
        type_ids_replaced = 0
        def replace_type_id(match):
            nonlocal type_ids_replaced
            type_ids_replaced += 1
            return f'{match.group(1)}{generate_uuid()}{match.group(3)}'

        content = type_id_pattern.sub(replace_type_id, content)

        # Замінюємо всі ValueId
        value_ids_replaced = 0
        def replace_value_id(match):
            nonlocal value_ids_replaced
            value_ids_replaced += 1
            return f'{match.group(1)}{generate_uuid()}{match.group(3)}'

        content = value_id_pattern.sub(replace_value_id, content)

        if type_ids_replaced > 0 or value_ids_replaced > 0:
            logger.info(f"   ✅ Згенеровано нові IDs: {type_ids_replaced} TypeId, {value_ids_replaced} ValueId")

        return content

    def _replace_uuid_in_xml(self, content: str) -> str:
        """
        Замінює UUID в будь-якому XML файлі (DataProcessor, Form, тощо).

        Універсальний метод для заміни uuid="..." в різних типах XML файлів.

        Args:
            content: XML контент

        Returns:
            Модифікований XML з новим UUID (якщо UUID був знайдений)
        """
        # Універсальний pattern для uuid="..." в будь-якому тегу
        uuid_pattern = re.compile(r'(\s+uuid=")([a-f0-9\-]+)(")')
        match = uuid_pattern.search(content)

        if not match:
            # UUID немає в цьому файлі - це нормально (не всі XML мають UUID)
            return content

        old_uuid = match.group(2)
        new_uuid = generate_uuid()

        # Замінюємо UUID
        content = uuid_pattern.sub(rf'\g<1>{new_uuid}\g<3>', content)

        logger.debug(f"      UUID: {old_uuid} → {new_uuid}")

        return content

    def _rename_processor(self, content: str, original_name: str, new_name: str) -> str:
        """
        Переім'яновує всі входження processor name в XML.

        Замінює:
        - <Name>УстановкаРоли</Name> → <Name>УстановкаРоли_Validation</Name>
        - <Synonym> tags (якщо містять original_name)
        - DefaultForm references: УстановкаРоли.Form.Форма
        - CommandModule references
        - DataProcessor.УстановкаРоли

        Args:
            content: XML контент
            original_name: Оригінальна назва processor
            new_name: Нова назва processor

        Returns:
            Модифікований XML
        """
        # 1. Замінюємо <Name>OriginalName</Name>
        content = re.sub(
            rf'(<Name>){re.escape(original_name)}(</Name>)',
            rf'\1{new_name}\2',
            content
        )

        # 2. Замінюємо всі входження "DataProcessor.OriginalName"
        content = re.sub(
            rf'(DataProcessor\.){re.escape(original_name)}(\W)',
            rf'\1{new_name}\2',
            content
        )

        # 3. Замінюємо DefaultForm та інші посилання: "OriginalName.Form.Форма"
        # Шукаємо original_name з крапкою після нього (Form, Command, etc.)
        content = re.sub(
            rf'\b{re.escape(original_name)}(\.[A-Za-zА-Яа-яІіЇїЄєҐґ])',
            rf'{new_name}\1',
            content
        )

        # 4. Замінюємо назву коли після неї йде XML тег або кінець рядка
        # Наприклад: "УстановкаРоли</v8:Type>" → "УстановкаРоли_Validation</v8:Type>"
        content = re.sub(
            rf'\b{re.escape(original_name)}(<|$)',
            rf'{new_name}\1',
            content
        )

        # 5. v2.67.1: Замінюємо GeneratedType name атрибути
        # <xr:GeneratedType name="ExternalDataProcessorObject.Original" → name="...Object.New"
        # <xr:GeneratedType name="DataProcessorManager.Original" → name="...Manager.New"
        # Примітка: External prefix є опціональним бо _rename_processor викликається
        # ДО _replace_generated_types в convert_external_to_internal
        # Критично для 8.3.17 та старших версій платформи!
        content = re.sub(
            rf'(<xr:GeneratedType\s+name="(?:External)?(?:DataProcessorObject|DataProcessorManager)\.){re.escape(original_name)}"',
            rf'\1{new_name}"',
            content
        )

        logger.debug(f"Перейменовано processor: {original_name} → {new_name}")
        return content

    def _replace_tags(self, content: str) -> str:
        """Замінює ExternalDataProcessor теги на DataProcessor."""
        content = content.replace("<ExternalDataProcessor ", "<DataProcessor ")
        content = content.replace("</ExternalDataProcessor>", "</DataProcessor>")
        return content

    def _replace_generated_types(self, content: str) -> str:
        """Замінює ExternalDataProcessorObject на DataProcessorObject."""
        content = content.replace("ExternalDataProcessorObject.", "DataProcessorObject.")
        return content

    def _replace_default_form_references(self, content: str) -> str:
        """Замінює DefaultForm посилання."""
        content = content.replace(">ExternalDataProcessor.", ">DataProcessor.")
        return content

    def _add_manager_type_if_missing(self, content: str) -> str:
        """
        Додає Manager GeneratedType якщо його немає.

        DataProcessor потребує Manager type окрім Object type.
        """
        if 'category="Manager"' in content:
            logger.debug("   Manager type вже існує, пропускаємо")
            return content

        match = self.OBJECT_TYPE_PATTERN.search(content)
        if not match:
            logger.warning("   ⚠️ Object GeneratedType не знайдено")
            return content

        processor_name = match.group(2)
        object_block = match.group(1)

        # Генеруємо нові UUID для Manager
        manager_type_id = generate_uuid()
        manager_value_id = generate_uuid()

        # Створюємо Manager GeneratedType блок
        manager_block = f'''
\t\t\t<xr:GeneratedType name="DataProcessorManager.{processor_name}" category="Manager">
\t\t\t\t<xr:TypeId>{manager_type_id}</xr:TypeId>
\t\t\t\t<xr:ValueId>{manager_value_id}</xr:ValueId>
\t\t\t</xr:GeneratedType>'''

        # Вставляємо Manager після Object
        content = content.replace(object_block, object_block + manager_block)

        logger.info(f"   ✅ Згенеровано Manager type: DataProcessorManager.{processor_name}")
        logger.debug(f"      TypeId: {manager_type_id}")
        logger.debug(f"      ValueId: {manager_value_id}")

        return content

    def _remove_contained_object(self, content: str) -> str:
        """Видаляє ContainedObject з InternalInfo (DataProcessor не має цього)."""
        if self.CONTAINED_OBJECT_PATTERN.search(content):
            content = self.CONTAINED_OBJECT_PATTERN.sub('\n', content)
            logger.debug("   ✅ Видалено ContainedObject з InternalInfo")

        return content

    def _inject_cfg_prefix(self, content: str) -> str:
        """
        Додає cfg: prefix до типів Configuration metadata (CatalogRef/DocumentRef/DataProcessorObject).

        ВАЖЛИВО: НЕ додавати cfg: до ExternalDataProcessorObject!
        Тільки до внутрішніх DataProcessorObject в Configuration.
        """
        modified = False

        # Додаємо cfg: до CatalogRef, DocumentRef та DataProcessorObject
        if 'CatalogRef.' in content:
            content = content.replace('<v8:Type>CatalogRef.', '<v8:Type>cfg:CatalogRef.')
            modified = True

        if 'DocumentRef.' in content:
            content = content.replace('<v8:Type>DocumentRef.', '<v8:Type>cfg:DocumentRef.')
            modified = True

        # Додаємо cfg: до DataProcessorObject (але НЕ до ExternalDataProcessorObject!)
        if 'DataProcessorObject.' in content and 'cfg:DataProcessorObject.' not in content:
            # Переконуємось що це не External (External вже має правильний тип)
            if 'ExternalDataProcessorObject.' not in content:
                content = content.replace('<v8:Type>DataProcessorObject.', '<v8:Type>cfg:DataProcessorObject.')
                modified = True

        if modified:
            logger.debug("   ✅ Додано cfg: prefix до Configuration metadata types")

        return content

    def _add_use_standard_commands(self, content: str) -> str:
        """Додає UseStandardCommands після Comment."""
        if '<UseStandardCommands>' in content:
            return content

        # В Properties блоці, після Comment додаємо UseStandardCommands
        content = content.replace(
            '<Comment/>\n\t\t\t<DefaultForm>',
            '<Comment/>\n\t\t\t<UseStandardCommands>true</UseStandardCommands>\n\t\t\t<DefaultForm>'
        )
        logger.debug("   ✅ Додано UseStandardCommands до Properties")

        return content

    def _add_additional_properties(self, content: str) -> str:
        """Додає додаткові Properties поля після DefaultForm."""
        if '<DefaultForm>DataProcessor.' not in content:
            return content

        if '<IncludeHelpInContents>' in content:
            return content

        if '<AuxiliaryForm/>' in content:
            # AuxiliaryForm вже є, додаємо решту полів після нього
            content = content.replace(
                '<AuxiliaryForm/>',
                '<AuxiliaryForm/>\n\t\t\t<IncludeHelpInContents>false</IncludeHelpInContents>\n\t\t\t<ExtendedPresentation/>\n\t\t\t<Explanation/>'
            )
        else:
            # AuxiliaryForm немає, додаємо всі поля разом
            content = re.sub(
                r'(</DefaultForm>)\s*(</Properties>)',
                r'\1\n\t\t\t<AuxiliaryForm/>\n\t\t\t<IncludeHelpInContents>false</IncludeHelpInContents>\n\t\t\t<ExtendedPresentation/>\n\t\t\t<Explanation/>\n\t\t\2',
                content
            )

        logger.debug("   ✅ Додано додаткові Properties поля")

        return content
