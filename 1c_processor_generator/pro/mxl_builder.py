"""
MXL Builder for Excel → MXL conversion.

Builds 1C SpreadsheetDocument XML (MXL format) from structured data.

MXL is XML-based with namespace http://v8.1c.ru/8.2/data/spreadsheet.
Key elements:
- languageSettings: Languages (ru, uk)
- columns: Column definitions with formatIndex
- rowsItem: Rows with cells
- namedItem: Named areas (for BSP Print Forms: Заголовок, СтрокаТаблицы, etc.)
- format: Format definitions (width, height, borders, alignment)
- font: Font definitions
- merge: Merged cells

Part of 1C Processor Generator PRO module.
Version: 2.58.0
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from xml.etree import ElementTree as ET


# MXL XML namespaces
MXL_NS = "http://v8.1c.ru/8.2/data/spreadsheet"
STYLE_NS = "http://v8.1c.ru/8.1/data/ui/style"
V8_NS = "http://v8.1c.ru/8.1/data/core"
V8UI_NS = "http://v8.1c.ru/8.1/data/ui"
XS_NS = "http://www.w3.org/2001/XMLSchema"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"

# Namespace prefixes
NS_MAP = {
    "": MXL_NS,
    "style": STYLE_NS,
    "v8": V8_NS,
    "v8ui": V8UI_NS,
    "xs": XS_NS,
    "xsi": XSI_NS,
}


def _normalize_color(value: Optional[str]) -> Optional[str]:
    """
    Normalize a hex color to MXL form '#RRGGBB' (v2.78.0+)

    Accepts 'RRGGBB', '#RRGGBB' or ARGB 'AARRGGBB'.
    """
    if not value:
        return None

    text = str(value).strip().lstrip("#")
    if len(text) == 8:      # ARGB from Excel
        text = text[-6:]
    if len(text) != 6:
        return None

    try:
        int(text, 16)
    except ValueError:
        return None

    return f"#{text.upper()}"


@dataclass
class MXLFont:
    """Font definition for MXL."""
    face_name: str = "Arial"
    height: float = 9.0
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strikeout: bool = False

    def to_key(self) -> tuple:
        """Return hashable key for font registry."""
        return (self.face_name, self.height, self.bold, self.italic, self.underline, self.strikeout)


@dataclass
class MXLFormat:
    """Format definition for MXL cells/rows/columns."""
    width: Optional[int] = None
    height: Optional[int] = None
    font_index: Optional[int] = None
    horizontal_alignment: Optional[str] = None  # Left, Center, Right
    vertical_alignment: Optional[str] = None    # Top, Center, Bottom
    left_border: Optional[int] = None           # Line index
    right_border: Optional[int] = None
    top_border: Optional[int] = None
    bottom_border: Optional[int] = None
    fill_type: Optional[str] = None             # "Parameter" for fill cells
    text_placement: Optional[str] = None        # "Cut", "Wrap"
    number_format: Optional[str] = None         # Number format string (1C syntax)

    # Colors as #RRGGBB, v2.78.0+
    text_color: Optional[str] = None
    back_color: Optional[str] = None
    border_color: Optional[str] = None
    indent: Optional[int] = None

    def to_key(self) -> tuple:
        """
        Return hashable key for format registry.

        Every field must be part of the key: a field left out makes two
        visually different formats collapse into one registry entry.
        """
        return (
            self.width, self.height, self.font_index,
            self.horizontal_alignment, self.vertical_alignment,
            self.left_border, self.right_border, self.top_border, self.bottom_border,
            self.fill_type, self.text_placement, self.number_format,
            self.text_color, self.back_color, self.border_color, self.indent
        )


@dataclass
class MXLDrawing:
    """
    Floating picture anchored to cells (v2.78.0+).

    picture_index is the 0-based index in the picture registry. In XML it is
    emitted as 1-based: 1C treats <pictureIndex>0</pictureIndex> as "no picture"
    and then discards the registry entry entirely.
    """
    picture_index: int
    begin_row: int
    begin_row_offset: int
    end_row: int
    end_row_offset: int
    begin_column: int
    begin_column_offset: int
    end_column: int
    end_column_offset: int
    drawing_id: int = 0
    format_index: int = 0
    z_order: int = 1
    picture_size: str = "Proportionally"   # Proportionally, Stretch, RealSize
    auto_size: bool = False


@dataclass
class MXLCell:
    """Cell data for MXL."""
    col_index: int              # 0-based column index
    format_index: int           # Reference to format
    text: Optional[Dict[str, str]] = None  # Localized text {lang: content}
    parameter: Optional[str] = None         # Parameter name
    detail_parameter: Optional[str] = None  # Detail parameter


@dataclass
class MXLRow:
    """Row data for MXL."""
    index: int                  # 0-based row index
    format_index: Optional[int] = None  # Row height format
    cells: List[MXLCell] = field(default_factory=list)
    columns_id: Optional[str] = None    # Reference to alternate columns set


@dataclass
class MXLMerge:
    """Merged cells definition."""
    row: int        # 0-based
    col: int        # 0-based
    width: int      # Number of columns to merge


@dataclass
class MXLNamedArea:
    """Named area (namedItem) definition."""
    name: str
    area_type: str = "Rows"     # Rows or Columns
    begin_row: int = -1         # 0-based, -1 = all
    end_row: int = -1
    begin_col: int = -1         # 0-based, -1 = all
    end_col: int = -1
    columns_id: Optional[str] = None


class MXLBuilder:
    """
    Builds MXL XML document.

    Usage:
        builder = MXLBuilder()
        builder.add_language_settings(["ru", "uk"])
        builder.add_column(0, width=64)
        builder.add_row(0, cells=[...])
        builder.add_named_area("Заголовок", "Rows", begin_row=0, end_row=3)
        xml = builder.build()
    """

    # Language descriptions
    LANGUAGE_INFO = {
        "ru": {"code": "Русский", "description": "Русский"},
        "uk": {"code": "Украинский", "description": "Украинский"},
        "en": {"code": "English", "description": "English"},
    }

    def __init__(self, default_language: str = "ru"):
        """
        Initialize builder.

        Args:
            default_language: Default language code (ru, uk, en)
        """
        self.default_language = default_language
        self.languages: List[str] = []

        # Registries for deduplication
        self._fonts: Dict[tuple, int] = {}
        self._formats: Dict[tuple, int] = {}
        self._lines: List[Dict] = []

        # Data
        self._columns: List[Tuple[int, int]] = []  # (index, format_index)
        self._rows: List[MXLRow] = []
        self._merges: List[MXLMerge] = []
        self._named_areas: List[MXLNamedArea] = []
        self._drawings: List[MXLDrawing] = []
        self._pictures: List[bytes] = []

        # Track dimensions
        self._max_row = 0
        self._max_col = 0

        # Add default formats
        self._add_default_formats()

    def _add_default_formats(self):
        """Add default format and font entries."""
        # Default font (index 0)
        default_font = MXLFont()
        self._register_font(default_font)

        # Bold font (index 1)
        bold_font = MXLFont(bold=True)
        self._register_font(bold_font)

        # NOTE: Do NOT register empty default format!
        # 1C ignores empty <format/> elements, causing index shift.
        # Formats will be registered as needed by add_column() and create_cell().

        # Add default line style (solid, width 1)
        self._lines.append({"width": 1, "style": "Solid"})

    def _register_font(self, font: MXLFont) -> int:
        """Register font and return its index."""
        key = font.to_key()
        if key not in self._fonts:
            self._fonts[key] = len(self._fonts)
        return self._fonts[key]

    def _register_format(self, fmt: MXLFormat) -> int:
        """Register format and return its index."""
        key = fmt.to_key()
        if key not in self._formats:
            self._formats[key] = len(self._formats)
        return self._formats[key]

    def _register_line(self, style: str = "Solid", width: int = 1) -> int:
        """
        Register a border line style and return its index (v2.78.0+)

        Previously every border reused line 0 (solid, width 1), so thick,
        double and dashed Excel borders all rendered identically.
        """
        entry = {"width": width, "style": style}
        for index, existing in enumerate(self._lines):
            if existing == entry:
                return index
        self._lines.append(entry)
        return len(self._lines) - 1

    def add_picture(self, data: bytes) -> int:
        """Register picture bytes, return its index (v2.78.0+)."""
        self._pictures.append(data)
        return len(self._pictures) - 1

    def add_drawing(self, drawing: MXLDrawing) -> MXLDrawing:
        """Add a floating picture anchored to cells (v2.78.0+)."""
        if not drawing.drawing_id:
            drawing.drawing_id = len(self._drawings) + 1
        self._drawings.append(drawing)
        return drawing

    def add_language_settings(self, languages: List[str]):
        """
        Set languages for the document.

        Args:
            languages: List of language codes (e.g., ["ru", "uk"])
        """
        self.languages = languages

    def add_column(self, index: int, width: int) -> int:
        """
        Add column definition.

        Args:
            index: 0-based column index
            width: Width in pixels

        Returns:
            Format index for this column
        """
        fmt = MXLFormat(width=width)
        format_index = self._register_format(fmt)
        self._columns.append((index, format_index))
        self._max_col = max(self._max_col, index)
        return format_index

    def add_row(
        self,
        index: int,
        cells: Optional[List[MXLCell]] = None,
        height: Optional[int] = None
    ) -> MXLRow:
        """
        Add row with cells.

        Args:
            index: 0-based row index
            cells: List of MXLCell objects
            height: Optional row height

        Returns:
            MXLRow object
        """
        format_index = None
        if height:
            fmt = MXLFormat(height=height)
            format_index = self._register_format(fmt)

        row = MXLRow(
            index=index,
            format_index=format_index,
            cells=cells or []
        )
        self._rows.append(row)
        self._max_row = max(self._max_row, index)

        # Track max column
        for cell in row.cells:
            self._max_col = max(self._max_col, cell.col_index)

        return row

    def create_cell(
        self,
        col_index: int,
        text: Optional[str] = None,
        text_localized: Optional[Dict[str, str]] = None,
        parameter: Optional[str] = None,
        font_name: str = "Arial",
        font_bold: bool = False,
        font_italic: bool = False,
        font_underline: bool = False,
        font_strikeout: bool = False,
        font_size: float = 9.0,
        horizontal_alignment: str = "Left",
        vertical_alignment: str = "Top",
        has_parameter: bool = False,
        wrap_text: bool = False,
        borders: Optional[Dict[str, Any]] = None,
        font_color: Optional[str] = None,
        background_color: Optional[str] = None,
        border_color: Optional[str] = None,
        number_format: Optional[str] = None,
        indent: int = 0
    ) -> MXLCell:
        """
        Create a cell with formatting.

        Args:
            col_index: 0-based column index
            text: Simple text (will be used for all languages)
            text_localized: Localized text {lang: content}
            parameter: Parameter name (for fill)
            font_name: Font face name (default: Arial)
            font_bold: Bold font
            font_italic: Italic font
            font_underline: Underline font
            font_strikeout: Strikeout font
            font_size: Font size
            horizontal_alignment: Left, Center, Right
            vertical_alignment: Top, Center, Bottom
            has_parameter: True if cell contains {parameter}
            wrap_text: Enable text wrapping
            borders: Dict with left/right/top/bottom keys. Values may be a bool
                (legacy: default solid line) or a dict {"style": ..., "width": ...}
            font_color: Text color as hex RRGGBB (v2.78.0+)
            background_color: Fill color as hex RRGGBB (v2.78.0+)
            border_color: Border color as hex RRGGBB (v2.78.0+)
            number_format: 1C format string, e.g. "ЧЦ=15; ЧДЦ=2" (v2.78.0+)
            indent: Text indent (v2.78.0+)

        Returns:
            MXLCell object
        """
        # Register font with all attributes
        font = MXLFont(
            face_name=font_name,
            height=font_size,
            bold=font_bold,
            italic=font_italic,
            underline=font_underline,
            strikeout=font_strikeout
        )
        font_index = self._register_font(font)

        # Prepare borders - each side gets its own registered line style
        border_indices = {}
        if borders:
            for side in ["left", "right", "top", "bottom"]:
                spec = borders.get(side)
                if not spec:
                    continue
                if isinstance(spec, dict):
                    line_index = self._register_line(
                        style=spec.get("style", "Solid"),
                        width=spec.get("width", 1),
                    )
                else:
                    # Legacy bool: default solid line
                    line_index = self._register_line()
                border_indices[f"{side}_border"] = line_index

        # Register format
        fmt = MXLFormat(
            font_index=font_index,
            horizontal_alignment=horizontal_alignment if horizontal_alignment != "Left" else None,
            vertical_alignment=vertical_alignment if vertical_alignment != "Top" else None,
            fill_type="Parameter" if has_parameter or parameter else None,
            text_placement="Wrap" if wrap_text else None,
            # Black is the 1C default; Excel reports it for ordinary text, and
            # emitting it everywhere would multiply format entries for nothing
            text_color=_normalize_color(font_color) if _normalize_color(font_color) != "#000000" else None,
            back_color=_normalize_color(background_color),
            border_color=_normalize_color(border_color) if border_indices else None,
            number_format=number_format,
            indent=indent or None,
            **border_indices
        )
        format_index = self._register_format(fmt)

        # Prepare text
        text_dict = None
        if text_localized:
            text_dict = text_localized
        elif text:
            # Use same text for all languages
            text_dict = {lang: text for lang in (self.languages or ["ru"])}

        return MXLCell(
            col_index=col_index,
            format_index=format_index,
            text=text_dict,
            parameter=parameter
        )

    def add_merge(self, row: int, col: int, width: int):
        """
        Add merged cell range.

        Args:
            row: 0-based row index
            col: 0-based start column
            width: Number of columns to merge
        """
        self._merges.append(MXLMerge(row=row, col=col, width=width))

    def add_named_area(
        self,
        name: str,
        area_type: str = "Rows",
        begin_row: int = -1,
        end_row: int = -1,
        begin_col: int = -1,
        end_col: int = -1
    ):
        """
        Add named area (for BSP Print Forms).

        Args:
            name: Area name (e.g., "Заголовок", "СтрокаТаблицы")
            area_type: "Rows" or "Columns"
            begin_row: Start row (0-based), -1 = all
            end_row: End row (0-based), -1 = all
            begin_col: Start column (0-based), -1 = all
            end_col: End column (0-based), -1 = all
        """
        self._named_areas.append(MXLNamedArea(
            name=name,
            area_type=area_type,
            begin_row=begin_row,
            end_row=end_row,
            begin_col=begin_col,
            end_col=end_col
        ))

    def build(self) -> str:
        """
        Build and return MXL XML string.

        Returns:
            XML string (UTF-8)
        """
        # Register namespaces (for proper prefix handling)
        # We use these for v8:item, v8ui:style etc.
        ET.register_namespace("v8", V8_NS)
        ET.register_namespace("v8ui", V8UI_NS)
        ET.register_namespace("xsi", XSI_NS)

        # Create root document (no namespace for now, we'll add xmlns in post-processing)
        root = ET.Element("document")

        # Add language settings
        self._build_language_settings(root)

        # Add columns
        self._build_columns(root)

        # Add rows
        self._build_rows(root)

        # Add drawings (pictures anchored to cells) - must follow rowsItem
        self._build_drawings(root)

        # Add template mode and dimensions
        ET.SubElement(root, "templateMode").text = "true"
        ET.SubElement(root, "defaultFormatIndex").text = "0"
        ET.SubElement(root, "height").text = str(self._max_row + 1)
        ET.SubElement(root, "vgRows").text = str(self._max_row + 1)

        # Add merges
        self._build_merges(root)

        # Add named areas
        self._build_named_areas(root)

        # Add lines
        self._build_lines(root)

        # Add fonts
        self._build_fonts(root)

        # Add formats
        self._build_formats(root)

        # Add picture registry - goes last, after formats
        self._build_pictures(root)

        # Generate XML string
        return self._to_xml_string(root)

    def _build_language_settings(self, root: ET.Element):
        """Build languageSettings element."""
        if not self.languages:
            self.languages = ["ru", "uk"]

        lang_settings = ET.SubElement(root, "languageSettings")
        ET.SubElement(lang_settings, "currentLanguage").text = self.languages[0]
        ET.SubElement(lang_settings, "defaultLanguage").text = self.default_language

        for lang in self.languages:
            info = self.LANGUAGE_INFO.get(lang, {"code": lang, "description": lang})
            lang_info = ET.SubElement(lang_settings, "languageInfo")
            ET.SubElement(lang_info, "id").text = lang
            ET.SubElement(lang_info, "code").text = info["code"]
            ET.SubElement(lang_info, "description").text = info["description"]

    def _build_columns(self, root: ET.Element):
        """Build columns element."""
        if not self._columns:
            return

        columns = ET.SubElement(root, "columns")
        ET.SubElement(columns, "size").text = str(self._max_col + 1)

        for index, format_index in sorted(self._columns):
            col_item = ET.SubElement(columns, "columnsItem")
            ET.SubElement(col_item, "index").text = str(index)
            col = ET.SubElement(col_item, "column")
            ET.SubElement(col, "formatIndex").text = str(format_index)

    def _build_rows(self, root: ET.Element):
        """Build rowsItem elements."""
        for row in sorted(self._rows, key=lambda r: r.index):
            row_item = ET.SubElement(root, "rowsItem")
            ET.SubElement(row_item, "index").text = str(row.index)

            row_elem = ET.SubElement(row_item, "row")

            if row.format_index is not None:
                ET.SubElement(row_elem, "formatIndex").text = str(row.format_index)

            if row.columns_id:
                ET.SubElement(row_elem, "columnsID").text = row.columns_id

            # Build cells
            for cell in row.cells:
                self._build_cell(row_elem, cell)

    def _build_cell(self, row_elem: ET.Element, cell: MXLCell):
        """Build cell element."""
        c_outer = ET.SubElement(row_elem, "c")

        # Column index (only if not sequential)
        if cell.col_index > 0:
            ET.SubElement(c_outer, "i").text = str(cell.col_index)

        c_inner = ET.SubElement(c_outer, "c")
        ET.SubElement(c_inner, "f").text = str(cell.format_index)

        # Localized text
        if cell.text:
            tl = ET.SubElement(c_inner, "tl")
            for lang, content in cell.text.items():
                item = ET.SubElement(tl, "{%s}item" % V8_NS)
                ET.SubElement(item, "{%s}lang" % V8_NS).text = lang
                ET.SubElement(item, "{%s}content" % V8_NS).text = content

        # Parameter
        if cell.parameter:
            ET.SubElement(c_inner, "parameter").text = cell.parameter

        if cell.detail_parameter:
            ET.SubElement(c_inner, "detailParameter").text = cell.detail_parameter

    def _build_merges(self, root: ET.Element):
        """Build merge elements."""
        for merge in self._merges:
            merge_elem = ET.SubElement(root, "merge")
            ET.SubElement(merge_elem, "r").text = str(merge.row)
            ET.SubElement(merge_elem, "c").text = str(merge.col)
            ET.SubElement(merge_elem, "w").text = str(merge.width)

    def _build_named_areas(self, root: ET.Element):
        """Build namedItem elements."""
        for area in self._named_areas:
            named_item = ET.SubElement(root, "namedItem")
            named_item.set("{%s}type" % XSI_NS, "NamedItemCells")

            ET.SubElement(named_item, "name").text = area.name

            area_elem = ET.SubElement(named_item, "area")
            ET.SubElement(area_elem, "type").text = area.area_type
            ET.SubElement(area_elem, "beginRow").text = str(area.begin_row)
            ET.SubElement(area_elem, "endRow").text = str(area.end_row)
            ET.SubElement(area_elem, "beginColumn").text = str(area.begin_col)
            ET.SubElement(area_elem, "endColumn").text = str(area.end_col)

            if area.columns_id:
                ET.SubElement(area_elem, "columnsID").text = area.columns_id

    def _build_drawings(self, root: ET.Element):
        """Build drawing elements for anchored pictures (v2.78.0+)."""
        for drawing in self._drawings:
            elem = ET.SubElement(root, "drawing")

            ET.SubElement(elem, "drawingType").text = "Picture"
            ET.SubElement(elem, "id").text = str(drawing.drawing_id)
            ET.SubElement(elem, "formatIndex").text = str(drawing.format_index)
            ET.SubElement(elem, "beginRow").text = str(drawing.begin_row)
            ET.SubElement(elem, "beginRowOffset").text = str(drawing.begin_row_offset)
            ET.SubElement(elem, "endRow").text = str(drawing.end_row)
            ET.SubElement(elem, "endRowOffset").text = str(drawing.end_row_offset)
            ET.SubElement(elem, "beginColumn").text = str(drawing.begin_column)
            ET.SubElement(elem, "beginColumnOffset").text = str(drawing.begin_column_offset)
            ET.SubElement(elem, "endColumn").text = str(drawing.end_column)
            ET.SubElement(elem, "endColumnOffset").text = str(drawing.end_column_offset)
            ET.SubElement(elem, "autoSize").text = "true" if drawing.auto_size else "false"
            ET.SubElement(elem, "pictureSize").text = drawing.picture_size
            ET.SubElement(elem, "zOrder").text = str(drawing.z_order)
            # 1-based reference into the 0-based picture registry (see MXLDrawing)
            ET.SubElement(elem, "pictureIndex").text = str(drawing.picture_index + 1)

    def _build_pictures(self, root: ET.Element):
        """Build the picture registry referenced by drawings (v2.78.0+)."""
        import base64

        for index, data in enumerate(self._pictures):
            wrapper = ET.SubElement(root, "picture")
            ET.SubElement(wrapper, "index").text = str(index)

            payload = ET.SubElement(wrapper, "picture")
            payload.set("t", "false")
            payload.text = base64.b64encode(data).decode("ascii")

    def _build_lines(self, root: ET.Element):
        """Build line elements for borders."""
        for line in self._lines:
            line_elem = ET.SubElement(root, "line")
            line_elem.set("width", str(line.get("width", 1)))
            line_elem.set("gap", "false")

            style_elem = ET.SubElement(line_elem, "{%s}style" % V8UI_NS)
            style_elem.set("{%s}type" % XSI_NS, "v8ui:SpreadsheetDocumentCellLineType")
            style_elem.text = line.get("style", "Solid")

    def _build_fonts(self, root: ET.Element):
        """Build font elements."""
        # Sort fonts by index
        sorted_fonts = sorted(self._fonts.items(), key=lambda x: x[1])

        for font_key, _ in sorted_fonts:
            face_name, height, bold, italic, underline, strikeout = font_key

            font_elem = ET.SubElement(root, "font")
            font_elem.set("faceName", face_name)
            # Format height: use integer if whole number, else keep decimal
            height_str = str(int(height)) if height == int(height) else str(height)
            font_elem.set("height", height_str)
            font_elem.set("bold", "true" if bold else "false")
            font_elem.set("italic", "true" if italic else "false")
            font_elem.set("underline", "true" if underline else "false")
            font_elem.set("strikeout", "true" if strikeout else "false")
            font_elem.set("kind", "Absolute")
            font_elem.set("scale", "100")

    def _build_formats(self, root: ET.Element):
        """Build format elements."""
        # Sort formats by index
        sorted_formats = sorted(self._formats.items(), key=lambda x: x[1])

        for format_key, _ in sorted_formats:
            (width, height, font_index, h_align, v_align,
             left_b, right_b, top_b, bottom_b,
             fill_type, text_placement, number_format,
             text_color, back_color, border_color, indent) = format_key

            fmt_elem = ET.SubElement(root, "format")

            if width is not None:
                ET.SubElement(fmt_elem, "width").text = str(width)

            if height is not None:
                # Format height: use integer if whole number
                height_str = str(int(height)) if height == int(height) else str(height)
                ET.SubElement(fmt_elem, "height").text = height_str

            if font_index is not None:
                ET.SubElement(fmt_elem, "font").text = str(font_index)

            if left_b is not None:
                ET.SubElement(fmt_elem, "leftBorder").text = str(left_b)

            if top_b is not None:
                ET.SubElement(fmt_elem, "topBorder").text = str(top_b)

            if right_b is not None:
                ET.SubElement(fmt_elem, "rightBorder").text = str(right_b)

            if bottom_b is not None:
                ET.SubElement(fmt_elem, "bottomBorder").text = str(bottom_b)

            if border_color:
                ET.SubElement(fmt_elem, "borderColor").text = border_color

            if h_align:
                ET.SubElement(fmt_elem, "horizontalAlignment").text = h_align

            if v_align:
                ET.SubElement(fmt_elem, "verticalAlignment").text = v_align

            if text_placement:
                ET.SubElement(fmt_elem, "textPlacement").text = text_placement

            if text_color:
                ET.SubElement(fmt_elem, "textColor").text = text_color

            if back_color:
                ET.SubElement(fmt_elem, "backColor").text = back_color

            if fill_type:
                ET.SubElement(fmt_elem, "fillType").text = fill_type

            if indent:
                ET.SubElement(fmt_elem, "indent").text = str(indent)

            if number_format:
                # Number format is a localized nested <format> element
                nested = ET.SubElement(fmt_elem, "format")
                for lang in (self.languages or [self.default_language]):
                    item = ET.SubElement(nested, "{%s}item" % V8_NS)
                    ET.SubElement(item, "{%s}lang" % V8_NS).text = lang
                    ET.SubElement(item, "{%s}content" % V8_NS).text = number_format

    def _to_xml_string(self, root: ET.Element) -> str:
        """Convert ElementTree to formatted XML string."""
        # Use minidom for pretty printing
        from xml.dom import minidom

        rough_string = ET.tostring(root, encoding="unicode")

        # Parse and pretty print
        dom = minidom.parseString(rough_string)
        pretty = dom.toprettyxml(indent="\t", encoding=None)

        # Remove extra blank lines and xml declaration
        lines = pretty.split("\n")
        # Skip first line (xml declaration) - we'll add our own
        lines = [line for line in lines[1:] if line.strip()]

        # Add proper XML declaration
        xml_decl = '<?xml version="1.0" encoding="UTF-8"?>'
        content = "\n".join(lines)

        # Post-process: Add xmlns declarations to <document> element
        # ElementTree may have already added some xmlns:* attributes,
        # so we use regex to replace the entire opening tag
        import re
        ns_attrs = (
            f'xmlns="{MXL_NS}" '
            f'xmlns:style="{STYLE_NS}" '
            f'xmlns:v8="{V8_NS}" '
            f'xmlns:v8ui="{V8UI_NS}" '
            f'xmlns:xs="{XS_NS}" '
            f'xmlns:xsi="{XSI_NS}"'
        )
        # Match <document> or <document xmlns:...>
        content = re.sub(
            r'<document(?:\s+[^>]*)?>',
            f'<document {ns_attrs}>',
            content,
            count=1
        )

        return xml_decl + "\n" + content
