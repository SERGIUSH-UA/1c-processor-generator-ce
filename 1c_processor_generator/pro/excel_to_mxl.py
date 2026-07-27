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
    from mxl_builder import MXLBuilder, MXLCell, MXLRow, MXLDrawing
except ImportError:
    # When running as part of package
    from .excel_reader import (
        ExcelReader, CellData, MergeRange, NamedArea,
        ColumnDef, RowDef, check_openpyxl_available, PARAMETER_PATTERN
    )
    from .mxl_builder import MXLBuilder, MXLCell, MXLRow, MXLDrawing


# Excel border style -> MXL line definition (v2.78.0+).
# MXL styles observed in real 1C templates: Solid, None, Dotted, Dashed,
# ThinDashed, LargeDashed, Double, ThickDashed; widths 0-3.
DEFAULT_BORDER_STYLE = {"style": "Solid", "width": 1}

EXCEL_BORDER_STYLES = {
    "thin": {"style": "Solid", "width": 1},
    "medium": {"style": "Solid", "width": 2},
    "thick": {"style": "Solid", "width": 3},
    "double": {"style": "Double", "width": 1},
    "hair": {"style": "Dotted", "width": 1},
    "dotted": {"style": "Dotted", "width": 1},
    "dashed": {"style": "Dashed", "width": 1},
    "mediumDashed": {"style": "Dashed", "width": 2},
    "dashDot": {"style": "Dashed", "width": 1},
    "mediumDashDot": {"style": "Dashed", "width": 2},
    "dashDotDot": {"style": "ThinDashed", "width": 1},
    "mediumDashDotDot": {"style": "ThinDashed", "width": 2},
    "slantDashDot": {"style": "Dashed", "width": 1},
}

# English Metric Units per pixel - Excel anchors offsets in EMU, MXL in pixels
EMU_PER_PIXEL = 9525

# Excel date/time tokens -> 1C ДФ tokens
_DATE_TOKEN_PATTERN = re.compile(r'(yyyy|yy|mmmm|mmm|mm|m|dd|d|hh|h|ss|s)')
_DATE_TOKEN_MAP = {
    "yyyy": "yyyy", "yy": "yy",
    "mmmm": "MMMM", "mmm": "MMM", "mm": "MM", "m": "M",
    "dd": "dd", "d": "d",
    "hh": "HH", "h": "H",
    "ss": "ss", "s": "s",
}


def convert_number_format(excel_format: Optional[str]) -> Optional[str]:
    """
    Translate an Excel number format into a 1C format string (v2.78.0+)

    1C uses its own syntax: 'ЧЦ=15; ЧДЦ=2' for numbers, 'ДФ=dd.MM.yyyy' for dates.
    Only the common numeric and date cases are translated; anything exotic
    (currency symbols, conditional formats, scientific notation) returns None
    so the caller can report it as not carried over instead of emitting nonsense.

    Returns:
        1C format string, or None if the format cannot be represented
    """
    if not excel_format:
        return None

    fmt = excel_format.strip()
    if fmt in ("General", "@", ""):
        return None

    # Excel allows section-separated formats (positive;negative;zero;text) -
    # 1C has no equivalent, use the positive section
    fmt = fmt.split(";")[0].strip()

    # Strip locale/color prefixes like [$-409] or [Red]
    fmt = re.sub(r'\[[^\]]*\]', '', fmt).strip()
    if not fmt:
        return None

    # Date/time formats
    if re.search(r'[ymdhs]', fmt, re.IGNORECASE) and not re.search(r'[#0]', fmt):
        pattern = _DATE_TOKEN_PATTERN.sub(
            lambda m: _DATE_TOKEN_MAP.get(m.group(0).lower(), m.group(0)),
            fmt.lower()
        )
        pattern = pattern.replace('"', '').strip()
        return f"ДФ={pattern}" if pattern else None

    # Percentages have no direct 1C format string equivalent
    if "%" in fmt:
        return None

    # Numeric formats
    if re.search(r'[#0]', fmt):
        # Drop currency literals and quoted text - 1C formats them separately
        numeric_part = re.sub(r'["\'].*?["\']', '', fmt)
        numeric_part = re.sub(r'[^#0.,]', '', numeric_part)
        if not numeric_part:
            return None

        decimals = 0
        if "." in numeric_part:
            decimals = len(numeric_part.split(".")[-1].replace(",", ""))

        parts = ["ЧЦ=15", f"ЧДЦ={decimals}"]

        # A comma before the decimal separator means digit grouping
        integer_part = numeric_part.split(".")[0]
        if "," in integer_part:
            parts.append("ЧРГ=' '")

        return "; ".join(parts)

    return None


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

        # Features of the source file that did not survive the conversion (v2.78.0+)
        self.warnings: List[str] = []

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
        self.warnings = []

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

        # Add images (logos etc.)
        self._add_images(builder, reader)

        # Report anything the conversion could not carry over
        self._collect_warnings(reader, cells)

        return builder.build()

    def _add_images(self, builder: MXLBuilder, reader: ExcelReader) -> None:
        """Transfer embedded images as anchored MXL drawings (v2.78.0+)."""
        for image in reader.get_images():
            data = image.get("data")
            if not data:
                continue

            picture_index = builder.add_picture(data)

            from_col = image.get("from_col") or 0
            from_row = image.get("from_row") or 0

            to_col = image.get("to_col")
            to_row = image.get("to_row")

            # A one-cell anchor has no "to" - derive the span from the pixel size
            if to_col is None or to_row is None:
                width_px = int(image.get("width") or 0)
                height_px = int(image.get("height") or 0)
                to_col = from_col + max(1, round(width_px / 64)) if width_px else from_col + 1
                to_row = from_row + max(1, round(height_px / 20)) if height_px else from_row + 1
                to_col_off = 0
                to_row_off = 0
            else:
                to_col_off = self._emu_to_px(image.get("to_col_off"))
                to_row_off = self._emu_to_px(image.get("to_row_off"))

            builder.add_drawing(MXLDrawing(
                picture_index=picture_index,
                begin_row=from_row,
                begin_row_offset=self._emu_to_px(image.get("from_row_off")),
                end_row=to_row,
                end_row_offset=to_row_off,
                begin_column=from_col,
                begin_column_offset=self._emu_to_px(image.get("from_col_off")),
                end_column=to_col,
                end_column_offset=to_col_off,
            ))

    @staticmethod
    def _emu_to_px(value) -> int:
        """Excel anchors offsets in EMU; MXL uses pixels."""
        try:
            return int(round(int(value or 0) / EMU_PER_PIXEL))
        except (TypeError, ValueError):
            return 0

    def _collect_warnings(self, reader: ExcelReader, cells: Dict[Tuple[int, int], CellData]) -> None:
        """Record source features that were not carried over (v2.78.0+)."""
        unsupported = reader.get_unsupported_features()

        charts = unsupported.get("charts", 0)
        if charts:
            self.warnings.append(
                f"{charts} діаграм(и) не переносяться в MXL - додайте їх як зображення"
            )

        unreadable = unsupported.get("unreadable_images", 0)
        if unreadable:
            self.warnings.append(
                f"{unreadable} зображень не вдалося прочитати - вони будуть відсутні в макеті"
            )

        # Number formats we could not express in 1C syntax
        dropped_formats = sorted({
            cell.number_format
            for cell in cells.values()
            if cell.number_format and convert_number_format(cell.number_format) is None
        })
        if dropped_formats:
            shown = ", ".join(dropped_formats[:3])
            suffix = ", ..." if len(dropped_formats) > 3 else ""
            self.warnings.append(
                f"{len(dropped_formats)} формат(ів) чисел не мають відповідника в 1С "
                f"і не перенесені ({shown}{suffix})"
            )

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

        # Prepare borders - each side keeps its own Excel style
        borders = None
        sides = {
            "left": cell_data.border_left_style,
            "right": cell_data.border_right_style,
            "top": cell_data.border_top_style,
            "bottom": cell_data.border_bottom_style,
        }
        if any(sides.values()):
            borders = {
                side: EXCEL_BORDER_STYLES.get(style, DEFAULT_BORDER_STYLE)
                for side, style in sides.items() if style
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
            borders=borders,
            font_color=cell_data.font_color,
            background_color=cell_data.background_color,
            border_color=cell_data.border_color,
            number_format=convert_number_format(cell_data.number_format),
            indent=cell_data.indent,
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
    languages: Optional[List[str]] = None,
    warnings_out: Optional[List[str]] = None
) -> str:
    """
    Convenience function to convert Excel to MXL.

    Args:
        excel_path: Path to .xlsx file
        output_path: Optional output .mxl file path
        languages: Languages for localization
        warnings_out: Optional list collecting what did not survive conversion (v2.78.0+)

    Returns:
        MXL XML content
    """
    converter = ExcelToMXLConverter(languages=languages)
    content = converter.convert(excel_path, output_path)

    if warnings_out is not None:
        warnings_out.extend(converter.warnings)

    return content
