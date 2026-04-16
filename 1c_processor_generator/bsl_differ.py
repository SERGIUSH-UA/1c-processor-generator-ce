"""
BSL code comparison module for detecting changes in procedure/function implementations.

This module provides functionality to compare BSL code from original and modified processors,
detecting new, deleted, and modified procedures/functions.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set
import logging

logger = logging.getLogger(__name__)


class BSLChangeType(Enum):
    """Types of changes in BSL code."""
    PROCEDURE_ADDED = "procedure_added"
    PROCEDURE_DELETED = "procedure_deleted"
    PROCEDURE_MODIFIED = "procedure_modified"
    REGION_ADDED = "region_added"
    REGION_DELETED = "region_deleted"


@dataclass
class BSLProcedure:
    """Represents a BSL procedure or function."""
    name: str
    is_function: bool  # True for Функция, False for Процедура
    signature: str  # Full signature with directives (&НаКлиенте, etc)
    body: str  # Procedure body (normalized for comparison)
    full_text: str  # Full procedure text as-is
    line_number: int  # Starting line number
    directives: List[str]  # Directives like &НаКлиенте, &НаСервере

    def normalize_body(self) -> str:
        """
        Normalize body for comparison (remove extra whitespace, comments).

        Returns:
            Normalized body text
        """
        # Remove single-line comments
        body = re.sub(r'//.*?$', '', self.body, flags=re.MULTILINE)

        # Remove extra whitespace
        body = re.sub(r'\s+', ' ', body)

        # Remove leading/trailing whitespace
        return body.strip()


@dataclass
class BSLRegion:
    """Represents a BSL region (#Область ... #КонецОбласті)."""
    name: str
    content: str
    line_number: int


@dataclass
class BSLChange:
    """Represents a single change in BSL code."""
    change_type: BSLChangeType
    procedure_name: Optional[str] = None
    old_code: Optional[str] = None
    new_code: Optional[str] = None
    region_name: Optional[str] = None

    def __str__(self) -> str:
        """Human-readable description of change."""
        if self.change_type == BSLChangeType.PROCEDURE_ADDED:
            return f"Procedure added: {self.procedure_name}"
        elif self.change_type == BSLChangeType.PROCEDURE_DELETED:
            return f"Procedure deleted: {self.procedure_name}"
        elif self.change_type == BSLChangeType.PROCEDURE_MODIFIED:
            return f"Procedure modified: {self.procedure_name}"
        elif self.change_type == BSLChangeType.REGION_ADDED:
            return f"Region added: {self.region_name}"
        elif self.change_type == BSLChangeType.REGION_DELETED:
            return f"Region deleted: {self.region_name}"
        return str(self.change_type.value)


class BSLDiffer:
    """
    Compares BSL code from two sources and detects changes.

    Analyzes procedures, functions, and regions to determine what code has been
    added, deleted, or modified.
    """

    # Regex patterns for parsing BSL
    PROCEDURE_PATTERN = re.compile(
        r'(?P<directives>(?:&[А-ЯЁа-яёA-Za-z]+\s*)*)'
        r'(?P<type>Процедура|Функция)\s+'
        r'(?P<name>[А-ЯЁа-яёA-Za-z0-9_]+)'
        r'\s*\((?P<params>[^)]*)\)'
        r'(?P<export>\s+Экспорт)?'
        r'(?P<body>.*?)'
        r'Конец(?:Процедуры|Функции)',
        re.DOTALL | re.MULTILINE | re.IGNORECASE
    )

    REGION_PATTERN = re.compile(
        r'#Область\s+(?P<name>[^\r\n]+)'
        r'(?P<content>.*?)'
        r'#КонецОбласті',
        re.DOTALL | re.MULTILINE | re.IGNORECASE
    )

    def __init__(self, original_bsl: str, modified_bsl: str):
        """
        Initialize differ with BSL code strings.

        Args:
            original_bsl: Original BSL code (generated)
            modified_bsl: Modified BSL code (from Configurator)
        """
        self.original_bsl = original_bsl
        self.modified_bsl = modified_bsl
        self.changes: List[BSLChange] = []

        # Parse procedures
        self.original_procedures = self._parse_procedures(original_bsl)
        self.modified_procedures = self._parse_procedures(modified_bsl)

        # Parse regions
        self.original_regions = self._parse_regions(original_bsl)
        self.modified_regions = self._parse_regions(modified_bsl)

    def detect_changes(self) -> List[BSLChange]:
        """
        Detect all changes in BSL code.

        Returns:
            List of BSLChange objects describing all detected changes
        """
        logger.info("Detecting changes in BSL code...")
        self.changes = []

        self._compare_procedures()
        self._compare_regions()

        logger.info(f"Detected {len(self.changes)} BSL changes")
        return self.changes

    def _compare_procedures(self):
        """Compare procedures between original and modified code."""
        original_names = set(self.original_procedures.keys())
        modified_names = set(self.modified_procedures.keys())

        # Find added procedures
        added = modified_names - original_names
        for name in added:
            proc = self.modified_procedures[name]
            self.changes.append(BSLChange(
                change_type=BSLChangeType.PROCEDURE_ADDED,
                procedure_name=name,
                new_code=proc.full_text
            ))

        # Find deleted procedures
        deleted = original_names - modified_names
        for name in deleted:
            proc = self.original_procedures[name]
            self.changes.append(BSLChange(
                change_type=BSLChangeType.PROCEDURE_DELETED,
                procedure_name=name,
                old_code=proc.full_text
            ))

        # Find modified procedures
        common = original_names & modified_names
        for name in common:
            orig_proc = self.original_procedures[name]
            mod_proc = self.modified_procedures[name]

            # Compare normalized bodies
            if orig_proc.normalize_body() != mod_proc.normalize_body():
                self.changes.append(BSLChange(
                    change_type=BSLChangeType.PROCEDURE_MODIFIED,
                    procedure_name=name,
                    old_code=orig_proc.full_text,
                    new_code=mod_proc.full_text
                ))

    def _compare_regions(self):
        """Compare regions between original and modified code."""
        original_names = set(self.original_regions.keys())
        modified_names = set(self.modified_regions.keys())

        # Find added regions
        added = modified_names - original_names
        for name in added:
            self.changes.append(BSLChange(
                change_type=BSLChangeType.REGION_ADDED,
                region_name=name,
                new_code=self.modified_regions[name].content
            ))

        # Find deleted regions
        deleted = original_names - modified_names
        for name in deleted:
            self.changes.append(BSLChange(
                change_type=BSLChangeType.REGION_DELETED,
                region_name=name,
                old_code=self.original_regions[name].content
            ))

    def _parse_procedures(self, code: str) -> Dict[str, BSLProcedure]:
        """
        Parse all procedures and functions from BSL code.

        Args:
            code: BSL code string

        Returns:
            Dictionary {procedure_name: BSLProcedure}
        """
        procedures = {}

        for match in self.PROCEDURE_PATTERN.finditer(code):
            directives_text = match.group('directives') or ''
            proc_type = match.group('type')
            name = match.group('name')
            params = match.group('params') or ''
            export = match.group('export') or ''
            body = match.group('body')

            # Parse directives
            directives = re.findall(r'&([А-ЯЁа-яёA-Za-z]+)', directives_text)

            # Build signature
            signature = f"{directives_text}{proc_type} {name}({params}){export}"

            # Get full procedure text
            full_text = match.group(0)

            # Get line number
            line_number = code[:match.start()].count('\n') + 1

            is_function = proc_type.lower() == 'функция'

            procedures[name] = BSLProcedure(
                name=name,
                is_function=is_function,
                signature=signature,
                body=body,
                full_text=full_text,
                line_number=line_number,
                directives=directives
            )

        return procedures

    def _parse_regions(self, code: str) -> Dict[str, BSLRegion]:
        """
        Parse all regions from BSL code.

        Args:
            code: BSL code string

        Returns:
            Dictionary {region_name: BSLRegion}
        """
        regions = {}

        for match in self.REGION_PATTERN.finditer(code):
            name = match.group('name').strip()
            content = match.group('content')
            line_number = code[:match.start()].count('\n') + 1

            regions[name] = BSLRegion(
                name=name,
                content=content,
                line_number=line_number
            )

        return regions

    def get_added_procedures(self) -> List[BSLChange]:
        """Get all added procedures."""
        return [c for c in self.changes
                if c.change_type == BSLChangeType.PROCEDURE_ADDED]

    def get_deleted_procedures(self) -> List[BSLChange]:
        """Get all deleted procedures."""
        return [c for c in self.changes
                if c.change_type == BSLChangeType.PROCEDURE_DELETED]

    def get_modified_procedures(self) -> List[BSLChange]:
        """Get all modified procedures."""
        return [c for c in self.changes
                if c.change_type == BSLChangeType.PROCEDURE_MODIFIED]

    def print_summary(self):
        """Print human-readable summary of detected BSL changes."""
        if not self.changes:
            print("No BSL changes detected.")
            return

        print(f"\n{'='*70}")
        print(f"Detected {len(self.changes)} BSL changes:")
        print(f"{'='*70}\n")

        # Group by change type
        added_procs = self.get_added_procedures()
        deleted_procs = self.get_deleted_procedures()
        modified_procs = self.get_modified_procedures()

        if added_procs:
            print(f"\nADDED PROCEDURES ({len(added_procs)}):")
            print("-" * 70)
            for change in added_procs:
                print(f"  • {change.procedure_name}")

        if deleted_procs:
            print(f"\nDELETED PROCEDURES ({len(deleted_procs)}):")
            print("-" * 70)
            for change in deleted_procs:
                print(f"  • {change.procedure_name}")

        if modified_procs:
            print(f"\nMODIFIED PROCEDURES ({len(modified_procs)}):")
            print("-" * 70)
            for change in modified_procs:
                print(f"  • {change.procedure_name}")

        print(f"\n{'='*70}\n")

    def get_procedure_diff(self, procedure_name: str) -> Optional[tuple]:
        """
        Get detailed diff for a specific procedure.

        Args:
            procedure_name: Name of procedure to get diff for

        Returns:
            Tuple of (old_code, new_code) or None if procedure not modified
        """
        for change in self.changes:
            if (change.change_type == BSLChangeType.PROCEDURE_MODIFIED and
                change.procedure_name == procedure_name):
                return (change.old_code, change.new_code)
        return None


class BSLCodeExtractor:
    """
    Utility class to extract BSL code from XML files.

    Used to extract Module.bsl content from processor XML for comparison.
    """

    @staticmethod
    def extract_from_xml(xml_path: str) -> str:
        """
        Extract BSL code from processor XML file.

        Args:
            xml_path: Path to XML file (processor or form)

        Returns:
            Extracted BSL code as string
        """
        from lxml import etree

        try:
            tree = etree.parse(xml_path)

            # Try to find Module content (can be in different locations)
            # For form: Form/FormModule
            # For processor: ExternalDataProcessor/ObjectModule

            module_paths = [
                ".//FormModule",
                ".//ObjectModule",
                ".//Module"
            ]

            for path in module_paths:
                module = tree.find(path)
                if module is not None and module.text:
                    return module.text.strip()

            logger.warning(f"No BSL module found in {xml_path}")
            return ""

        except Exception as e:
            logger.error(f"Failed to extract BSL from {xml_path}: {e}")
            return ""

    @staticmethod
    def extract_from_bsl_file(bsl_path: str) -> str:
        """
        Read BSL code from .bsl file.

        Args:
            bsl_path: Path to .bsl file

        Returns:
            BSL code content
        """
        try:
            with open(bsl_path, 'r', encoding='utf-8-sig') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read BSL file {bsl_path}: {e}")
            return ""
