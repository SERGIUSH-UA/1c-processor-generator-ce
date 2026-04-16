"""
Аналізатор метаданих для визначення необхідних CatalogRef/DocumentRef типів
та атрибутів для заглушок метаданих (Smart Stub Generator).
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Set, Dict, List, Optional
from .models import Processor, DynamicListAttribute
from .query_text_parser import StubAttribute, extract_stub_attributes_for_dynamic_list

logger = logging.getLogger(__name__)


@dataclass
class StubMetadata:
    """Metadata stub with required attributes for DynamicList support."""
    name: str
    metadata_type: str  # "Document" or "Catalog"
    attributes: List[StubAttribute] = field(default_factory=list)

    def add_attribute(self, attr: StubAttribute) -> None:
        """Add attribute if not already present (by name)."""
        existing_names = {a.name for a in self.attributes}
        if attr.name not in existing_names:
            self.attributes.append(attr)


@dataclass
class MetadataRequirements:
    """Вимоги до метаданих для генерації Configuration.xml"""
    catalogs: Set[str] = field(default_factory=set)
    documents: Set[str] = field(default_factory=set)
    common_pictures: Set[str] = field(default_factory=set)
    common_modules: Set[str] = field(default_factory=set)  # v2.57.0+ BSP stub modules
    # Smart stub metadata with attributes (key: "Document.Name" or "Catalog.Name")
    stub_metadata: Dict[str, StubMetadata] = field(default_factory=dict)

    def is_empty(self) -> bool:
        """Перевірка чи потрібна генерація Configuration"""
        return (len(self.catalogs) == 0 and len(self.documents) == 0 and
                len(self.common_pictures) == 0 and len(self.common_modules) == 0)

    def has_metadata(self) -> bool:
        """Перевірка чи є метадані (CatalogRef/DocumentRef/CommonPicture) для генерації Configuration"""
        return not self.is_empty()

    def get_stub_attributes(self, metadata_type: str, name: str) -> List[StubAttribute]:
        """Get attributes for a specific stub."""
        key = f"{metadata_type}.{name}"
        if key in self.stub_metadata:
            return self.stub_metadata[key].attributes
        return []

    def add_stub_attribute(
        self,
        metadata_type: str,
        metadata_name: str,
        attribute: StubAttribute
    ) -> None:
        """Add attribute to stub metadata."""
        key = f"{metadata_type}.{metadata_name}"
        if key not in self.stub_metadata:
            self.stub_metadata[key] = StubMetadata(
                name=metadata_name,
                metadata_type=metadata_type,
            )
        self.stub_metadata[key].add_attribute(attribute)

    def __repr__(self) -> str:
        stub_info = f", stub_metadata={len(self.stub_metadata)} stubs" if self.stub_metadata else ""
        return f"MetadataRequirements(catalogs={sorted(self.catalogs)}, documents={sorted(self.documents)}, common_pictures={sorted(self.common_pictures)}{stub_info})"


class MetadataAnalyzer:
    """Аналізатор для витягування необхідних метаданих з Processor об'єкта"""

    # Regex patterns для пошуку типів
    CATALOG_REF_PATTERN = re.compile(r'CatalogRef\.(\w+)')
    DOCUMENT_REF_PATTERN = re.compile(r'DocumentRef\.(\w+)')
    CATALOG_MAIN_TABLE_PATTERN = re.compile(r'Catalog\.(\w+)')
    DOCUMENT_MAIN_TABLE_PATTERN = re.compile(r'Document\.(\w+)')
    COMMON_PICTURE_PATTERN = re.compile(r'CommonPicture\.(\w+)')

    # v2.57.0+ BSP Common Modules pattern (module.method calls)
    COMMON_MODULE_PATTERN = re.compile(r'\b([А-Яа-яЁё][А-Яа-яЁёA-Za-z0-9_]+)\.(Нужно|Вывести|Задать|Сведения|Выполнить|Получить|Установить)\w*\(', re.UNICODE)

    @staticmethod
    def analyze_processor(processor: Processor) -> MetadataRequirements:
        """
        Аналізує Processor об'єкт та витягує всі необхідні метадані

        Args:
            processor: Processor об'єкт з models.py

        Returns:
            MetadataRequirements з множинами назв довідників та документів
        """
        requirements = MetadataRequirements()

        # 1. Аналіз атрибутів процесора
        for attribute in processor.attributes:
            MetadataAnalyzer._extract_from_type(attribute.type, requirements)

        # 2. Аналіз колонок табличних частин
        for tabular_section in processor.tabular_sections:
            for column in tabular_section.columns:
                MetadataAnalyzer._extract_from_type(column.type, requirements)

        # 3. Аналіз форм
        for form in processor.forms:
            # 3.1. ValueTable атрибути
            for value_table in form.value_table_attributes:
                for column in value_table.columns:
                    MetadataAnalyzer._extract_from_type(column.type, requirements)

            # 3.2. DynamicList атрибути (main_table + stub attributes)
            for dynamic_list in form.dynamic_list_attributes:
                if dynamic_list.main_table:
                    MetadataAnalyzer._extract_from_main_table(dynamic_list.main_table, requirements)

                # Smart Stub: витягуємо атрибути для заглушок
                MetadataAnalyzer._extract_stub_attributes_from_dynamic_list(
                    dynamic_list, requirements
                )

            # 3.3. CommonPicture з команд
            for cmd in form.commands:
                if cmd.picture:
                    MetadataAnalyzer._extract_from_picture(cmd.picture, requirements)

            # 3.4. CommonPicture з елементів форми (рекурсивно)
            MetadataAnalyzer._extract_pictures_from_elements(form.elements, requirements)

        # 4. v2.57.0+ BSP Integration: автоматично додаємо необхідні BSP модулі
        if processor.bsp_config:
            MetadataAnalyzer._add_bsp_required_modules(processor.bsp_config, requirements)

        return requirements

    @staticmethod
    def _extract_from_type(type_string: str, requirements: MetadataRequirements) -> None:
        """
        Витягує назви довідників/документів з типу атрибута

        Підтримує:
        - Конкретні типи: "CatalogRef.Організації"
        - Composite типи: "CatalogRef.A, DocumentRef.B, string"
        - Універсальний CatalogRef/DocumentRef (без назви) - ігнорується

        Args:
            type_string: Рядок з типом (може містити кілька типів через кому)
            requirements: Об'єкт для збору вимог
        """
        if not type_string:
            return

        # Шукаємо всі CatalogRef.XXX
        for match in MetadataAnalyzer.CATALOG_REF_PATTERN.finditer(type_string):
            catalog_name = match.group(1)
            requirements.catalogs.add(catalog_name)

        # Шукаємо всі DocumentRef.XXX
        for match in MetadataAnalyzer.DOCUMENT_REF_PATTERN.finditer(type_string):
            document_name = match.group(1)
            requirements.documents.add(document_name)

    @staticmethod
    def _extract_from_main_table(main_table: str, requirements: MetadataRequirements) -> None:
        """
        Витягує назви довідників/документів з DynamicList.main_table

        Формати:
        - "Catalog.Організації"
        - "Document.ЗамовленняКлієнта"
        - "DocumentJournal.XXX" - ігнорується (не підтримується зараз)

        Args:
            main_table: Рядок з main_table
            requirements: Об'єкт для збору вимог
        """
        if not main_table:
            return

        # Шукаємо Catalog.XXX
        catalog_match = MetadataAnalyzer.CATALOG_MAIN_TABLE_PATTERN.search(main_table)
        if catalog_match:
            catalog_name = catalog_match.group(1)
            requirements.catalogs.add(catalog_name)

        # Шукаємо Document.XXX
        document_match = MetadataAnalyzer.DOCUMENT_MAIN_TABLE_PATTERN.search(main_table)
        if document_match:
            document_name = document_match.group(1)
            requirements.documents.add(document_name)

    @staticmethod
    def _extract_from_picture(picture_string: str, requirements: MetadataRequirements) -> None:
        """
        Витягує назви CommonPicture з поля picture

        Формати:
        - "CommonPicture.МояКартинка"
        - "StdPicture.Refresh" - ігнорується (вбудована картинка)

        Args:
            picture_string: Рядок з picture
            requirements: Об'єкт для збору вимог
        """
        if not picture_string:
            return

        # Шукаємо CommonPicture.XXX
        match = MetadataAnalyzer.COMMON_PICTURE_PATTERN.search(picture_string)
        if match:
            picture_name = match.group(1)
            requirements.common_pictures.add(picture_name)

    @staticmethod
    def _extract_pictures_from_elements(elements: list, requirements: MetadataRequirements) -> None:
        """
        Рекурсивно витягує CommonPicture з елементів форми

        Сканує:
        - properties['picture']
        - properties['choice_button_picture']
        - children (рекурсивно)

        Args:
            elements: Список елементів форми
            requirements: Об'єкт для збору вимог
        """
        if not elements:
            return

        for elem in elements:
            # Сканування picture та choice_button_picture
            for prop_name in ('picture', 'choice_button_picture'):
                value = elem.properties.get(prop_name, '') if elem.properties else ''
                if value:
                    MetadataAnalyzer._extract_from_picture(value, requirements)

            # Рекурсія для child_items (включаючи Page)
            if elem.child_items:
                MetadataAnalyzer._extract_pictures_from_elements(elem.child_items, requirements)

    @staticmethod
    def _add_bsp_required_modules(bsp_config, requirements: MetadataRequirements) -> None:
        """
        v2.57.0+ Додає необхідні BSP модулі залежно від типу обробки.

        Args:
            bsp_config: BSPConfig об'єкт
            requirements: Об'єкт для збору вимог
        """
        # PrintForm потребує УправлениеПечатью
        if bsp_config.type == "PrintForm":
            requirements.common_modules.add("УправлениеПечатью")
            logger.info("Added BSP module stub: УправлениеПечатью")

        # Інші типи можуть потребувати інших модулів
        # ObjectFilling, CreationOfRelatedObjects можуть використовувати
        # ДополнительныеОтчетыИОбработки, тощо

    @staticmethod
    def _extract_stub_attributes_from_dynamic_list(
        dynamic_list: DynamicListAttribute,
        requirements: MetadataRequirements
    ) -> None:
        """
        Витягує атрибути з DynamicList для генерації розширених заглушок.

        Парсить query_text або columns для визначення полів, які потрібні
        в заглушці Document/Catalog для валідації DataPath колонок.

        Args:
            dynamic_list: DynamicListAttribute об'єкт
            requirements: Об'єкт для збору вимог
        """
        # Skip if no main_table (no stub needed)
        if not dynamic_list.main_table:
            return

        # Check if skip_stub_validation is set
        skip_validation = getattr(dynamic_list, 'skip_stub_validation', False)
        if skip_validation:
            logger.debug(f"Skipping stub attribute extraction for {dynamic_list.name} (skip_stub_validation=True)")
            return

        # Extract stub attributes using parser
        stub_attrs = extract_stub_attributes_for_dynamic_list(
            query_text=dynamic_list.query_text,
            columns=dynamic_list.columns if hasattr(dynamic_list, 'columns') else None,
            main_table=dynamic_list.main_table
        )

        if not stub_attrs:
            return

        # Determine metadata type from main_table
        main_table = dynamic_list.main_table
        if main_table.lower().startswith("document.") or main_table.lower().startswith("документ."):
            metadata_type = "Document"
            metadata_name = main_table.split(".", 1)[1]
        elif main_table.lower().startswith("catalog.") or main_table.lower().startswith("справочник."):
            metadata_type = "Catalog"
            metadata_name = main_table.split(".", 1)[1]
        else:
            logger.warning(f"Unknown main_table format: {main_table}")
            return

        # Add attributes to requirements
        for attr in stub_attrs:
            requirements.add_stub_attribute(metadata_type, metadata_name, attr)

        logger.info(
            f"Extracted {len(stub_attrs)} stub attributes for {metadata_type}.{metadata_name} "
            f"from DynamicList '{dynamic_list.name}'"
        )

    @staticmethod
    def print_analysis(processor: Processor, requirements: MetadataRequirements) -> None:
        """
        Виводить детальний аналіз знайдених метаданих (для debugging)

        Args:
            processor: Processor об'єкт
            requirements: Результати аналізу
        """
        print(f"\n=== Metadata Analysis for '{processor.name}' ===")
        print(f"\nCatalogs found ({len(requirements.catalogs)}):")
        for catalog in sorted(requirements.catalogs):
            print(f"  - {catalog}")

        print(f"\nDocuments found ({len(requirements.documents)}):")
        for document in sorted(requirements.documents):
            print(f"  - {document}")

        print(f"\nCommonPictures found ({len(requirements.common_pictures)}):")
        for picture in sorted(requirements.common_pictures):
            print(f"  - {picture}")

        if requirements.is_empty():
            print("\n⚠️ No CatalogRef/DocumentRef/CommonPicture found - Configuration generation not needed")
        else:
            total = len(requirements.catalogs) + len(requirements.documents) + len(requirements.common_pictures)
            print(f"\n✅ Total metadata objects: {total}")
            print(f"   UUID count needed: {MetadataAnalyzer.calculate_uuid_count(requirements)}")

    @staticmethod
    def calculate_uuid_count(requirements: MetadataRequirements) -> int:
        """
        Розраховує необхідну кількість UUID для метаданих

        Формула:
        - Configuration: 1 UUID
        - Language (Русский): 1 UUID
        - Catalog: 11 UUID (1 catalog + 5 types × 2) + 1 per attribute
        - Document: 9 UUID (1 document + 4 types × 2) + 1 per attribute
        - CommonPicture: 1 UUID

        Args:
            requirements: Результати аналізу

        Returns:
            Кількість UUID
        """
        base_uuids = 2  # Configuration + Language
        catalog_uuids = len(requirements.catalogs) * 11
        document_uuids = len(requirements.documents) * 9
        picture_uuids = len(requirements.common_pictures) * 1

        # Add UUIDs for stub attributes
        stub_attr_uuids = sum(
            len(stub.attributes)
            for stub in requirements.stub_metadata.values()
        )

        return base_uuids + catalog_uuids + document_uuids + picture_uuids + stub_attr_uuids
