"""
Excel → MXL Converter for 1C SpreadsheetDocument templates.

Converts Excel (.xlsx) files to MXL (1C SpreadsheetDocument XML) format.
This enables creating print form templates in Excel and using them in 1C.

Features (v2.58.0):
- Cell values and basic formatting
- Named Ranges → Named Areas (Заголовок, СтрокаТаблицы, Подвал)
- Parameter detection ({ParameterName} syntax)
- Column widths
- Merged cells
- Multilingual support (ru, uk)

Part of 1C Processor Generator PRO module.
Version: 2.58.0
"""
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    # When running as compiled .pyd
    from excel_reader import (
        ExcelReader, CellData, MergeRange, NamedArea,
        ColumnDef, RowDef, check_openpyxl_available, PARAMETER_PATTERN
    )
    from mxl_builder import MXLBuilder, MXLCell, MXLRow
except ImportError:
    # When running as part of package
    from .excel_reader import (
        ExcelReader, CellData, MergeRange, NamedArea,
        ColumnDef, RowDef, check_openpyxl_available, PARAMETER_PATTERN
    )
    from .mxl_builder import MXLBuilder, MXLCell, MXLRow


class ExcelToMXLConverter:
    """
    Converts Excel files to MXL format.

    Usage:
        converter = ExcelToMXLConverter()
        mxl_content = converter.convert("template.xlsx")

        # Or with output file
        converter.convert("template.xlsx", "template.mxl")

        # Get as binary for 1C template
        binary = converter.convert_to_binary("template.xlsx")
    """

    # Standard BSP area names
    BSP_AREA_ALIASES = {
        # Header area
        "header": "Заголовок",
        "заголовок": "Заголовок",
        "шапка": "Заголовок",

        # Table header
        "tableheader": "ШапкаТаблицы",
        "шапкатаблицы": "ШапкаТаблицы",
        "columnheaders": "ШапкаТаблицы",

        # Row template
        "row": "СтрокаТаблицы",
        "строка": "СтрокаТаблицы",
        "строкатаблицы": "СтрокаТаблицы",
        "datarow": "СтрокаТаблицы",

        # Footer
        "footer": "Подвал",
        "подвал": "Подвал",
        "итого": "Итого",
        "total": "Итого",
    }

    def __init__(
        self,
        languages: Optional[List[str]] = None,
        default_language: str = "ru"
    ):
        """
        Initialize converter.

        Args:
            languages: Languages for localization (default: ["ru", "uk"])
            default_language: Default language code
        """
        if not check_openpyxl_available():
            raise ImportError(
                "openpyxl is required for Excel → MXL conversion. "
                "Install it with: pip install openpyxl>=3.1.0"
            )

        self.languages = languages or ["ru", "uk"]
        self.default_language = default_language

    def convert(
        self,
        excel_path: str,
        output_path: Optional[str] = None,
        sheet_name: Optional[str] = None
    ) -> str:
        """
        Convert Excel file to MXL format.

        Args:
            excel_path: Path to .xlsx file
            output_path: Optional output .mxl file path
            sheet_name: Optional sheet name (default: active sheet)

        Returns:
            MXL XML content as string
        """
        with ExcelReader(excel_path, sheet_name) as reader:
            mxl_content = self._convert_workbook(reader)

        if output_path:
            Path(output_path).write_text(mxl_content, encoding="utf-8-sig")

        return mxl_content

    def convert_to_binary(
        self,
        excel_path: str,
        sheet_name: Optional[str] = None
    ) -> bytes:
        """
        Convert Excel to MXL and return as bytes.

        Args:
            excel_path: Path to .xlsx file
            sheet_name: Optional sheet name

        Returns:
            MXL content as UTF-8 bytes (with BOM)
        """
        mxl_content = self.convert(excel_path, sheet_name=sheet_name)
        # UTF-8 with BOM for 1C compatibility
        return mxl_content.encode("utf-8-sig")

    def _convert_workbook(self, reader: ExcelReader) -> str:
        """Convert workbook to MXL."""
        builder = MXLBuilder(default_language=self.default_language)
        builder.add_language_settings(self.languages)

        # Get data from Excel
        cells = reader.get_cells()
        columns = reader.get_columns()
        merged = reader.get_merged_cells()
        named_areas = reader.get_named_areas()
        min_row, min_col, max_row, max_col = reader.get_dimensions()

        # Add columns
        for col_def in columns:
            builder.add_column(col_def.index, int(col_def.width))

        # Build rows with cells
        self._build_rows(builder, reader, cells, min_row, max_row, min_col, max_col)

        # Add merged cells
        for merge in merged:
            # Convert to 0-based for MXL
            builder.add_merge(
                row=merge.start_row - 1,
                col=merge.start_col - 1,
                width=merge.width
            )

        # Add named areas
        for area in named_areas:
            self._add_named_area(builder, area)

        return builder.build()

    def _build_rows(
        self,
        builder: MXLBuilder,
        reader: ExcelReader,
        cells: Dict[Tuple[int, int], CellData],
        min_row: int,
        max_row: int,
        min_col: int,
        max_col: int
    ):
        """Build all rows with cells."""
        rows = reader.get_rows()
        row_heights = {r.index: r.height for r in rows}

        for row_idx in range(min_row, max_row + 1):
            row_cells = []

            for col_idx in range(min_col, max_col + 1):
                cell_data = cells.get((row_idx, col_idx))
                if cell_data:
                    mxl_cell = self._create_cell(builder, cell_data)
                    row_cells.append(mxl_cell)

            # Get row height (0-based index)
            height = row_heights.get(row_idx - 1)
            height_int = int(height) if height and height != 15.0 else None

            builder.add_row(
                index=row_idx - 1,  # 0-based for MXL
                cells=row_cells,
                height=height_int
            )

    def _create_cell(self, builder: MXLBuilder, cell_data: CellData) -> MXLCell:
        """Create MXL cell from Excel cell data."""
        # Prepare text
        text = cell_data.value
        text_localized = None
        parameter = None
        has_parameter = False

        # Check for parameters
        if text and cell_data.parameters:
            has_parameter = True

            # If cell contains ONLY a parameter placeholder, extract it
            if len(cell_data.parameters) == 1:
                match = PARAMETER_PATTERN.fullmatch(text.strip())
                if match:
                    # Cell is just {ParameterName} - use as parameter
                    parameter = cell_data.parameters[0]
                    text = None

        # Create localized text if we have text
        if text:
            text_localized = {lang: text for lang in self.languages}

        # Prepare borders
        borders = None
        if any([cell_data.border_left, cell_data.border_right,
                cell_data.border_top, cell_data.border_bottom]):
            borders = {
                "left": cell_data.border_left,
                "right": cell_data.border_right,
                "top": cell_data.border_top,
                "bottom": cell_data.border_bottom,
            }

        return builder.create_cell(
            col_index=cell_data.col - 1,  # 0-based for MXL
            text_localized=text_localized,
            parameter=parameter,
            font_name=cell_data.font_name,
            font_bold=cell_data.font_bold,
            font_italic=cell_data.font_italic,
            font_underline=cell_data.font_underline,
            font_strikeout=cell_data.font_strikeout,
            font_size=cell_data.font_size,
            horizontal_alignment=cell_data.horizontal_alignment,
            vertical_alignment=cell_data.vertical_alignment,
            has_parameter=has_parameter,
            wrap_text=cell_data.wrap_text,
            borders=borders
        )

    def _add_named_area(self, builder: MXLBuilder, area: NamedArea):
        """Add named area with BSP alias mapping."""
        # Normalize name for BSP
        name = area.name
        name_lower = name.lower().replace("_", "").replace(" ", "")

        # Check for BSP aliases
        if name_lower in self.BSP_AREA_ALIASES:
            name = self.BSP_AREA_ALIASES[name_lower]

        # Convert coordinates to 0-based for MXL
        begin_row = area.start_row - 1 if area.start_row > 0 else -1
        end_row = area.end_row - 1 if area.end_row > 0 else -1
        begin_col = area.start_col - 1 if area.start_col > 0 else -1
        end_col = area.end_col - 1 if area.end_col > 0 else -1

        builder.add_named_area(
            name=name,
            area_type=area.area_type,
            begin_row=begin_row,
            end_row=end_row,
            begin_col=begin_col,
            end_col=end_col
        )


def convert_excel_to_mxl(
    excel_path: str,
    output_path: Optional[str] = None,
    languages: Optional[List[str]] = None
) -> str:
    """
    Convenience function to convert Excel to MXL.

    Args:
        excel_path: Path to .xlsx file
        output_path: Optional output .mxl file path
        languages: Languages for localization

    Returns:
        MXL XML content
    """
    converter = ExcelToMXLConverter(languages=languages)
    return converter.convert(excel_path, output_path)
