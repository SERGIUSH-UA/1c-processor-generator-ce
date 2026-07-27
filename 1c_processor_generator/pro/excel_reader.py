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

# Standard Office theme palette (v2.78.0+).
# Theme colors are stored in Excel as an index + tint, not as RGB, so they have to
# be resolved against the workbook theme. Files using a custom theme will resolve
# slightly off - still far better than dropping the color entirely.
OFFICE_THEME_COLORS = [
    "FFFFFF",  # 0 lt1 / background 1
    "000000",  # 1 dk1 / text 1
    "EEECE1",  # 2 lt2 / background 2
    "1F497D",  # 3 dk2 / text 2
    "4F81BD",  # 4 accent1
    "C0504D",  # 5 accent2
    "9BBB59",  # 6 accent3
    "8064A2",  # 7 accent4
    "4BACC6",  # 8 accent5
    "F79646",  # 9 accent6
    "0000FF",  # 10 hyperlink
    "800080",  # 11 followed hyperlink
]


def _apply_tint(hex_rgb: str, tint: float) -> str:
    """
    Apply an Excel tint to a hex color.

    Excel tints in HLS space: negative darkens, positive lightens the luminance.
    """
    import colorsys

    if not tint:
        return hex_rgb

    r, g, b = (int(hex_rgb[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    h, l, s = colorsys.rgb_to_hls(r, g, b)

    if tint < 0:
        l = l * (1 + tint)
    else:
        l = l * (1 - tint) + tint

    l = max(0.0, min(1.0, l))
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return "{:02X}{:02X}{:02X}".format(round(r * 255), round(g * 255), round(b * 255))


def _color_to_hex(color) -> Optional[str]:
    """
    Convert an openpyxl Color to a 6-char hex string (no '#'), or None.

    Handles all three ways Excel stores a color: explicit rgb, a theme index
    with a tint, and a legacy indexed palette entry.
    """
    if color is None:
        return None

    color_type = getattr(color, "type", None)

    if color_type == "rgb" or getattr(color, "rgb", None):
        rgb = color.rgb
        if isinstance(rgb, str) and len(rgb) >= 6:
            # ARGB - fully transparent means "not set"
            if len(rgb) == 8 and rgb[:2] == "00":
                return None
            return rgb[-6:].upper()

    if color_type == "theme":
        theme = getattr(color, "theme", None)
        if isinstance(theme, int) and 0 <= theme < len(OFFICE_THEME_COLORS):
            return _apply_tint(OFFICE_THEME_COLORS[theme], getattr(color, "tint", 0.0) or 0.0)

    if color_type == "indexed":
        try:
            from openpyxl.styles.colors import COLOR_INDEX
            idx = getattr(color, "indexed", None)
            if isinstance(idx, int) and 0 <= idx < len(COLOR_INDEX):
                value = COLOR_INDEX[idx]
                if isinstance(value, str) and len(value) >= 6:
                    if len(value) == 8 and value[:2] == "00":
                        return None
                    return value[-6:].upper()
        except Exception:
            return None

    return None


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

    # Font color (hex without #), v2.78.0+
    font_color: Optional[str] = None

    horizontal_alignment: str = "Left"  # Left, Center, Right
    vertical_alignment: str = "Top"     # Top, Center, Bottom
    indent: int = 0                     # Alignment indent, v2.78.0+

    # Borders (True if has border)
    border_left: bool = False
    border_right: bool = False
    border_top: bool = False
    border_bottom: bool = False

    # Border styles as reported by Excel (thin/medium/double/...), v2.78.0+
    # None means "no border on this side"
    border_left_style: Optional[str] = None
    border_right_style: Optional[str] = None
    border_top_style: Optional[str] = None
    border_bottom_style: Optional[str] = None

    # Border color (hex without #), v2.78.0+ - MXL keeps one color per cell
    border_color: Optional[str] = None

    # Background color (hex without #)
    background_color: Optional[str] = None

    # Excel number format string (e.g. '#,##0.00'), v2.78.0+
    number_format: Optional[str] = None

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

        def border_style(side) -> Optional[str]:
            return side.style if has_border(side) else None

        # Background color
        bg_color = _color_to_hex(fill.fgColor) if fill else None
        # Excel marks "no fill" as pattern-less; fgColor may still carry a stale value
        if fill is not None and getattr(fill, "patternType", None) in (None, "none"):
            bg_color = None

        # Border color: MXL stores one color per cell, so take the first side that has one
        border_color = None
        if border:
            for side in (border.left, border.right, border.top, border.bottom):
                if has_border(side):
                    border_color = _color_to_hex(getattr(side, "color", None))
                    if border_color:
                        break

        number_format = cell.number_format
        if number_format in (None, "General", "@"):
            number_format = None

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
            font_color=_color_to_hex(font.color) if font else None,
            horizontal_alignment=h_align_map.get(alignment.horizontal, "Left") if alignment else "Left",
            vertical_alignment=v_align_map.get(alignment.vertical, "Top") if alignment else "Top",
            indent=int(alignment.indent) if alignment and alignment.indent else 0,
            border_left=has_border(border.left) if border else False,
            border_right=has_border(border.right) if border else False,
            border_top=has_border(border.top) if border else False,
            border_bottom=has_border(border.bottom) if border else False,
            border_left_style=border_style(border.left) if border else None,
            border_right_style=border_style(border.right) if border else None,
            border_top_style=border_style(border.top) if border else None,
            border_bottom_style=border_style(border.bottom) if border else None,
            border_color=border_color,
            background_color=bg_color,
            number_format=number_format,
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

    def get_images(self) -> List[Dict[str, Any]]:
        """
        Get images embedded in the worksheet (v2.78.0+)

        openpyxl exposes them via the private ws._images; each carries an anchor
        with the source/target cell and pixel offsets.

        Returns:
            List of dicts: data (bytes), anchor coordinates, size
        """
        images = []

        for image in getattr(self.ws, "_images", []) or []:
            try:
                data = image.ref
                if hasattr(data, "read"):
                    data.seek(0)
                    data = data.read()
                elif hasattr(data, "_data"):
                    data = data._data()
                elif not isinstance(data, bytes):
                    with open(str(data), "rb") as fh:
                        data = fh.read()

                anchor = getattr(image, "anchor", None)
                frm = getattr(anchor, "_from", None)
                to = getattr(anchor, "to", None)

                images.append({
                    "data": data,
                    "format": (getattr(image, "format", None) or "png"),
                    "from_col": getattr(frm, "col", 0) or 0,
                    "from_col_off": getattr(frm, "colOff", 0) or 0,
                    "from_row": getattr(frm, "row", 0) or 0,
                    "from_row_off": getattr(frm, "rowOff", 0) or 0,
                    "to_col": getattr(to, "col", None),
                    "to_col_off": getattr(to, "colOff", 0) or 0,
                    "to_row": getattr(to, "row", None),
                    "to_row_off": getattr(to, "rowOff", 0) or 0,
                    "width": getattr(image, "width", None),
                    "height": getattr(image, "height", None),
                })
            except Exception:
                # A picture we cannot read is reported as lost, not fatal
                images.append({"data": None, "format": None})

        return images

    def get_unsupported_features(self) -> Dict[str, int]:
        """
        Count source features that will not survive the conversion (v2.78.0+)

        Used to warn the user instead of silently dropping content.

        Returns:
            Dict of feature name -> count (only non-zero entries)
        """
        stats: Dict[str, int] = {}

        charts = len(getattr(self.ws, "_charts", []) or [])
        if charts:
            stats["charts"] = charts

        unreadable = sum(1 for img in self.get_images() if img.get("data") is None)
        if unreadable:
            stats["unreadable_images"] = unreadable

        return stats

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
