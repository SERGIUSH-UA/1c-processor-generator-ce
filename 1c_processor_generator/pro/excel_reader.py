"""
Excel Reader for Excel → MXL conversion.

Reads Excel files using openpyxl and extracts structure for MXL generation:
- Cell values and formatting
- Named Ranges (→ named areas in MXL)
- Merged cells
- Column widths
- Parameters ({ParameterName} syntax)

Part of 1C Processor Generator PRO module.
Version: 2.58.0
"""
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

try:
    from openpyxl import load_workbook
    from openpyxl.worksheet.worksheet import Worksheet
    from openpyxl.cell.cell import Cell
    from openpyxl.styles import Font, Alignment, Border, PatternFill
    from openpyxl.utils import get_column_letter, column_index_from_string
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


# Parameter detection pattern: {ParameterName}
PARAMETER_PATTERN = re.compile(r'\{([A-Za-zА-Яа-яЁёҐґЇїІіЄє_][A-Za-zА-Яа-яЁёҐґЇїІіЄє0-9_]*)\}')


@dataclass
class CellData:
    """Represents a cell with its content and formatting."""
    row: int                    # 1-based row index
    col: int                    # 1-based column index
    value: Optional[str] = None
    parameters: List[str] = field(default_factory=list)  # Detected {parameters}

    # Formatting
    font_name: str = "Arial"
    font_size: float = 9.0
    font_bold: bool = False
    font_italic: bool = False
    font_underline: bool = False
    font_strikeout: bool = False

    horizontal_alignment: str = "Left"  # Left, Center, Right
    vertical_alignment: str = "Top"     # Top, Center, Bottom

    # Borders (True if has border)
    border_left: bool = False
    border_right: bool = False
    border_top: bool = False
    border_bottom: bool = False

    # Background color (hex without #)
    background_color: Optional[str] = None

    # Text wrapping
    wrap_text: bool = False


@dataclass
class MergeRange:
    """Represents a merged cell range."""
    start_row: int      # 1-based
    start_col: int      # 1-based
    end_row: int        # 1-based
    end_col: int        # 1-based

    @property
    def width(self) -> int:
        """Number of columns in merge (for MXL <w> element)."""
        return self.end_col - self.start_col


@dataclass
class NamedArea:
    """Represents a named area (Named Range in Excel → namedItem in MXL)."""
    name: str
    start_row: int      # 1-based
    end_row: int        # 1-based
    start_col: int      # 1-based, -1 = all columns
    end_col: int        # 1-based, -1 = all columns
    area_type: str = "Rows"  # Rows or Columns


@dataclass
class ColumnDef:
    """Column definition with width."""
    index: int          # 0-based for MXL
    width: float        # Width in pixels (approximate)


@dataclass
class RowDef:
    """Row definition with height."""
    index: int          # 0-based for MXL
    height: float       # Height in points


class ExcelReader:
    """
    Reads Excel file and extracts structure for MXL generation.

    Usage:
        reader = ExcelReader("template.xlsx")
        cells = reader.get_cells()
        named_areas = reader.get_named_areas()
        merged = reader.get_merged_cells()
        columns = reader.get_columns()
    """

    # Default column width in Excel (8.43 characters ≈ 64 pixels)
    DEFAULT_COLUMN_WIDTH = 64

    # Character width multiplier (Excel width to pixels)
    CHAR_WIDTH_MULTIPLIER = 7.5

    def __init__(self, file_path: str, sheet_name: Optional[str] = None):
        """
        Initialize reader with Excel file.

        Args:
            file_path: Path to .xlsx file
            sheet_name: Optional sheet name (default: active sheet)
        """
        if not OPENPYXL_AVAILABLE:
            raise ImportError(
                "openpyxl is required for Excel reading. "
                "Install it with: pip install openpyxl>=3.1.0"
            )

        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {file_path}")

        self.wb = load_workbook(str(self.file_path), data_only=True)

        if sheet_name:
            if sheet_name not in self.wb.sheetnames:
                raise ValueError(f"Sheet '{sheet_name}' not found. Available: {self.wb.sheetnames}")
            self.ws: Worksheet = self.wb[sheet_name]
        else:
            self.ws: Worksheet = self.wb.active

        self._cells_cache: Optional[Dict[Tuple[int, int], CellData]] = None

    def get_dimensions(self) -> Tuple[int, int, int, int]:
        """
        Get worksheet dimensions.

        Returns:
            Tuple (min_row, min_col, max_row, max_col) - 1-based indices
        """
        return (
            self.ws.min_row or 1,
            self.ws.min_column or 1,
            self.ws.max_row or 1,
            self.ws.max_column or 1
        )

    def get_cells(self) -> Dict[Tuple[int, int], CellData]:
        """
        Get all cells with values and formatting.

        Returns:
            Dict mapping (row, col) to CellData
        """
        if self._cells_cache is not None:
            return self._cells_cache

        cells: Dict[Tuple[int, int], CellData] = {}

        min_row, min_col, max_row, max_col = self.get_dimensions()

        for row_idx in range(min_row, max_row + 1):
            for col_idx in range(min_col, max_col + 1):
                cell = self.ws.cell(row=row_idx, column=col_idx)
                cell_data = self._parse_cell(cell)
                cells[(row_idx, col_idx)] = cell_data

        self._cells_cache = cells
        return cells

    def _parse_cell(self, cell: "Cell") -> CellData:
        """Parse single cell into CellData."""
        value = str(cell.value) if cell.value is not None else None

        # Detect parameters in value
        parameters = []
        if value:
            parameters = PARAMETER_PATTERN.findall(value)

        # Extract formatting
        font = cell.font
        alignment = cell.alignment
        border = cell.border
        fill = cell.fill

        # Horizontal alignment mapping
        h_align_map = {
            "left": "Left",
            "center": "Center",
            "right": "Right",
            "general": "Left",
            None: "Left"
        }

        # Vertical alignment mapping
        v_align_map = {
            "top": "Top",
            "center": "Center",
            "bottom": "Bottom",
            None: "Top"
        }

        # Check borders
        def has_border(side) -> bool:
            return side is not None and side.style is not None and side.style != "none"

        # Background color
        bg_color = None
        if fill and fill.fgColor and fill.fgColor.rgb and fill.fgColor.rgb != "00000000":
            rgb = fill.fgColor.rgb
            if isinstance(rgb, str) and len(rgb) >= 6:
                bg_color = rgb[-6:]  # Last 6 chars (RGB without alpha)

        return CellData(
            row=cell.row,
            col=cell.column,
            value=value,
            parameters=parameters,
            font_name=font.name or "Arial",
            font_size=font.size or 9.0,
            font_bold=font.bold or False,
            font_italic=font.italic or False,
            font_underline=bool(font.underline) if font.underline else False,
            font_strikeout=font.strike or False,
            horizontal_alignment=h_align_map.get(alignment.horizontal, "Left") if alignment else "Left",
            vertical_alignment=v_align_map.get(alignment.vertical, "Top") if alignment else "Top",
            border_left=has_border(border.left) if border else False,
            border_right=has_border(border.right) if border else False,
            border_top=has_border(border.top) if border else False,
            border_bottom=has_border(border.bottom) if border else False,
            background_color=bg_color,
            wrap_text=alignment.wrap_text if alignment and alignment.wrap_text else False
        )

    def get_merged_cells(self) -> List[MergeRange]:
        """
        Get all merged cell ranges.

        Returns:
            List of MergeRange objects
        """
        merged = []
        for merge_range in self.ws.merged_cells.ranges:
            merged.append(MergeRange(
                start_row=merge_range.min_row,
                start_col=merge_range.min_col,
                end_row=merge_range.max_row,
                end_col=merge_range.max_col
            ))
        return merged

    def get_named_areas(self) -> List[NamedArea]:
        """
        Get named areas from workbook's defined names.

        Only includes names that reference this worksheet.

        Returns:
            List of NamedArea objects
        """
        areas = []

        # openpyxl 3.x: defined_names is directly iterable (DefinedNameDict)
        # We iterate over the dict values or use list()
        try:
            # Try new API (openpyxl 3.x)
            defined_names_list = list(self.wb.defined_names.values())
        except AttributeError:
            # Fallback to old API (openpyxl 2.x)
            defined_names_list = self.wb.defined_names.definedName

        for defined_name in defined_names_list:
            name = defined_name.name

            # Skip Excel internal names
            if name.startswith("_"):
                continue

            # Get destinations (sheet, range)
            try:
                for sheet_title, coord in defined_name.destinations:
                    if sheet_title != self.ws.title:
                        continue

                    # Parse coordinate (e.g., "$A$1:$C$5" or "$1:$3")
                    area = self._parse_range_coordinate(coord, name)
                    if area:
                        areas.append(area)
            except (AttributeError, ValueError):
                continue

        return areas

    def _parse_range_coordinate(self, coord: str, name: str) -> Optional[NamedArea]:
        """Parse Excel range coordinate into NamedArea."""
        # Remove $ signs
        coord = coord.replace("$", "")

        if ":" not in coord:
            # Single cell - not useful for named areas
            return None

        start, end = coord.split(":")

        # Check if it's row-based (e.g., "1:5") or column-based (e.g., "A:C")
        start_row, start_col = self._parse_cell_ref(start)
        end_row, end_col = self._parse_cell_ref(end)

        # Determine area type
        if start_col == -1 and end_col == -1:
            # Row range: "1:5"
            area_type = "Rows"
        elif start_row == -1 and end_row == -1:
            # Column range: "A:C"
            area_type = "Columns"
        else:
            # Cell range - treat as Rows
            area_type = "Rows"

        return NamedArea(
            name=name,
            start_row=start_row,
            end_row=end_row,
            start_col=start_col,
            end_col=end_col,
            area_type=area_type
        )

    def _parse_cell_ref(self, ref: str) -> Tuple[int, int]:
        """
        Parse cell reference like "A1", "1", or "A".

        Returns:
            Tuple (row, col) where -1 means "all"
        """
        # Try to extract column letters and row numbers
        col_match = re.match(r'^([A-Za-z]+)', ref)
        row_match = re.search(r'(\d+)$', ref)

        col = -1
        row = -1

        if col_match:
            col = column_index_from_string(col_match.group(1))

        if row_match:
            row = int(row_match.group(1))

        return row, col

    def get_columns(self) -> List[ColumnDef]:
        """
        Get column definitions with widths.

        Returns:
            List of ColumnDef objects (0-based index for MXL)
        """
        columns = []
        _, min_col, _, max_col = self.get_dimensions()

        for col_idx in range(min_col, max_col + 1):
            col_letter = get_column_letter(col_idx)
            col_dim = self.ws.column_dimensions.get(col_letter)

            if col_dim and col_dim.width:
                width = col_dim.width * self.CHAR_WIDTH_MULTIPLIER
            else:
                width = self.DEFAULT_COLUMN_WIDTH

            columns.append(ColumnDef(
                index=col_idx - 1,  # 0-based for MXL
                width=round(width)
            ))

        return columns

    def get_rows(self) -> List[RowDef]:
        """
        Get row definitions with heights.

        Returns:
            List of RowDef objects (0-based index for MXL)
        """
        rows = []
        min_row, _, max_row, _ = self.get_dimensions()

        for row_idx in range(min_row, max_row + 1):
            row_dim = self.ws.row_dimensions.get(row_idx)

            if row_dim and row_dim.height:
                height = row_dim.height
            else:
                height = 15.0  # Default row height

            rows.append(RowDef(
                index=row_idx - 1,  # 0-based for MXL
                height=height
            ))

        return rows

    def find_parameters(self) -> List[Tuple[int, int, str]]:
        """
        Find all cells with {Parameter} syntax.

        Returns:
            List of tuples (row, col, parameter_name) - 1-based indices
        """
        params = []
        cells = self.get_cells()

        for (row, col), cell_data in cells.items():
            for param_name in cell_data.parameters:
                params.append((row, col, param_name))

        return params

    def get_unique_fonts(self) -> List[Dict[str, Any]]:
        """
        Get unique font definitions used in the worksheet.

        Returns:
            List of font dictionaries
        """
        fonts = {}
        cells = self.get_cells()

        for cell_data in cells.values():
            font_key = (
                cell_data.font_name,
                cell_data.font_size,
                cell_data.font_bold,
                cell_data.font_italic,
                cell_data.font_underline,
                cell_data.font_strikeout
            )

            if font_key not in fonts:
                fonts[font_key] = {
                    "name": cell_data.font_name,
                    "size": cell_data.font_size,
                    "bold": cell_data.font_bold,
                    "italic": cell_data.font_italic,
                    "underline": cell_data.font_underline,
                    "strikeout": cell_data.font_strikeout
                }

        return list(fonts.values())

    def close(self):
        """Close the workbook."""
        self.wb.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def check_openpyxl_available() -> bool:
    """Check if openpyxl is available."""
    return OPENPYXL_AVAILABLE
