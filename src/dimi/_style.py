import typing

import pygame

from dimi._primitives import (
    Absolute,
    Align,
    Anchor,
    Axis,
    Constraint,
    Corners,
    DirectionalMeasure,
    Font,
    FontAlign,
    FontDirection,
    ImageFit,
    ImageRepeat,
    Measure,
    NinePatch,
    PointsOrigin,
    RenderOrder,
    ScaleQuality,
    Size,
    Transform,
    Wrap,
)

# todo implement element wrapping


class Style(typing.NamedTuple):
    __module__ = "dimi"

    width: Size = 0
    height: Size = 0

    width_constraint: Constraint | None = None
    height_constraint: Constraint | None = None

    padding: DirectionalMeasure = 5
    margin: DirectionalMeasure = 0
    spacing: Measure = 3

    z: float = 0
    blocking: bool = True
    clip_graphics: bool = True
    position: Absolute | None = None

    self_offset: pygame.typing.Point = (0, 0)
    children_offset: pygame.typing.Point = (0, 0)

    axis: Axis = Axis.Y
    align_children: Align = Align.FIRST
    align_self: Align = Align.FIRST

    wrap_children: Wrap | None = None

    def _fast_replace(self, kwargs) -> Style:
        if not kwargs:
            return self
        g = kwargs.get
        return Style(
            g("width", self[0]),
            g("height", self[1]),
            g("width_constraint", self[2]),
            g("height_constraint", self[3]),
            g("padding", self[4]),
            g("margin", self[5]),
            g("spacing", self[6]),
            g("z", self[7]),
            g("blocking", self[8]),
            g("clip_graphics", self[9]),
            g("position", self[10]),
            g("self_offset", self[11]),
            g("children_offset", self[12]),
            g("axis", self[13]),
            g("align_children", self[14]),
            g("align_self", self[15]),
            g("wrap_children", self[16]),
        )


class StyleOverrides(typing.TypedDict, total=False):
    __module__ = "dimi.typehinting"

    width: Size
    height: Size

    width_constraint: Constraint | None
    height_constraint: Constraint | None

    padding: DirectionalMeasure
    margin: DirectionalMeasure
    spacing: Measure

    z: float
    blocking: bool
    clip_graphics: bool
    position: Absolute | None

    self_offset: pygame.typing.Point
    children_offset: pygame.typing.Point

    axis: Axis
    align_children: Align
    align_self: Align

    wrap_children: Wrap | None


# todo consider dash size/offset
class RectStyle(typing.NamedTuple):
    __module__ = "dimi"

    padding: DirectionalMeasure = 0
    offset: pygame.typing.Point = (0, 0)

    border_radius: Measure | Corners = 0
    border_width: Measure = 0

    color: pygame.typing.ColorLike | None = (0, 0, 0, 0)
    antialias: bool = True

    aspect_ratio: float | tuple[float, Axis, bool] = 0.0
    anchor: Anchor = Anchor.CENTER

    shape: bool = False
    render_order: RenderOrder = RenderOrder.DEFAULT
    z: float = 0

    def _fast_replace(self, kwargs) -> RectStyle:
        if not kwargs:
            return self
        g = kwargs.get
        return RectStyle(
            g("padding", self[0]),
            g("offset", self[1]),
            g("border_radius", self[2]),
            g("border_width", self[3]),
            g("color", self[4]),
            g("antialias", self[5]),
            g("aspect_ratio", self[6]),
            g("anchor", self[7]),
            g("shape", self[8]),
            g("render_order", self[9]),
            g("z", self[10]),
        )


class RectStyleOverrides(typing.TypedDict, total=False):
    __module__ = "dimi.typehinting"

    padding: DirectionalMeasure
    offset: pygame.typing.Point

    border_radius: Measure | Corners
    border_width: Measure

    color: pygame.typing.ColorLike
    antialias: bool

    aspect_ratio: float | tuple[float, Axis, bool]
    anchor: Anchor

    shape: bool
    render_order: RenderOrder
    z: float


class EllipseStyle(typing.NamedTuple):
    __module__ = "dimi"

    padding: DirectionalMeasure = 0
    offset: pygame.typing.Point = (0, 0)

    border_width: Measure = 0

    color: pygame.typing.ColorLike | None = (0, 0, 0, 0)
    antialias: bool = True

    aspect_ratio: float | tuple[float, Axis, bool] = 0.0
    anchor: Anchor = Anchor.CENTER

    shape: bool = False
    render_order: RenderOrder = RenderOrder.DEFAULT
    z: float = 0

    def _fast_replace(self, kwargs) -> EllipseStyle:
        if not kwargs:
            return self
        g = kwargs.get
        return EllipseStyle(
            g("padding", self[0]),
            g("offset", self[1]),
            g("border_width", self[2]),
            g("color", self[3]),
            g("antialias", self[4]),
            g("aspect_ratio", self[5]),
            g("anchor", self[6]),
            g("shape", self[7]),
            g("render_order", self[8]),
            g("z", self[9]),
        )


class EllipseStyleOverrides(typing.TypedDict, total=False):
    __module__ = "dimi.typehinting"

    padding: DirectionalMeasure
    offset: pygame.typing.Point

    border_width: Measure

    color: pygame.typing.ColorLike | None
    antialias: bool

    aspect_ratio: float | tuple[float, Axis, bool]
    anchor: Anchor

    shape: bool
    render_order: RenderOrder
    z: float


class LineStyle(typing.NamedTuple):
    __module__ = "dimi"

    padding: DirectionalMeasure = 0
    offset: pygame.typing.Point = (0, 0)

    size: Measure = 1
    points_origin: PointsOrigin = PointsOrigin.CENTER

    color: pygame.typing.ColorLike = (0, 0, 0, 0)
    antialias: bool = True

    render_order: RenderOrder = RenderOrder.DEFAULT
    z: float = 0

    def _fast_replace(self, kwargs) -> LineStyle:
        if not kwargs:
            return self
        g = kwargs.get
        return LineStyle(
            g("padding", self[0]),
            g("offset", self[1]),
            g("size", self[2]),
            g("points_origin", self[3]),
            g("color", self[4]),
            g("antialias", self[5]),
            g("render_order", self[6]),
            g("z", self[7]),
        )


class LineStyleOverrides(typing.TypedDict, total=False):
    __module__ = "dimi.typehinting"

    padding: DirectionalMeasure
    offset: pygame.typing.Point

    size: Measure
    points_origin: PointsOrigin

    color: pygame.typing.ColorLike
    antialias: bool

    render_order: RenderOrder
    z: float


class TextStyle(typing.NamedTuple):
    __module__ = "dimi"

    font: pygame.Font | Font | None = None
    size: Measure | None = None

    padding: DirectionalMeasure = (5, 3)
    anchor: Anchor = Anchor.CENTER
    offset: pygame.typing.Point = (0, 0)

    align: FontAlign = FontAlign.CENTER
    direction: FontDirection = FontDirection.LTR
    line_skip: Measure | None = None
    wrap: bool = True

    bold: bool = False
    italic: bool = False
    underline: bool = False
    strikethrough: bool = False

    antialias: bool = True
    color: pygame.typing.ColorLike | None = (255, 255, 255, 255)
    background_color: pygame.typing.ColorLike | None = None

    outline_width: int = 0
    outline_color: pygame.typing.ColorLike = (0, 0, 0, 255)

    render_order: RenderOrder = RenderOrder.DEFAULT
    z: float = 0

    def _fast_replace(self, kwargs) -> TextStyle:
        if not kwargs:
            return self
        g = kwargs.get
        return TextStyle(
            g("font", self[0]),
            g("size", self[1]),
            g("padding", self[2]),
            g("anchor", self[3]),
            g("offset", self[4]),
            g("align", self[5]),
            g("direction", self[6]),
            g("line_skip", self[7]),
            g("wrap", self[8]),
            g("bold", self[9]),
            g("italic", self[10]),
            g("underline", self[11]),
            g("strikethrough", self[12]),
            g("antialias", self[13]),
            g("color", self[14]),
            g("background_color", self[15]),
            g("outline_width", self[16]),
            g("outline_color", self[17]),
            g("render_order", self[18]),
            g("z", self[19]),
        )


class TextStyleOverrides(typing.TypedDict, total=False):
    __module__ = "dimi.typehinting"

    font: pygame.Font | Font | None
    size: Measure | None

    padding: DirectionalMeasure
    anchor: Anchor
    offset: pygame.typing.Point

    align: FontAlign
    direction: FontDirection
    line_skip: int | None
    wrap: bool

    bold: bool
    italic: bool
    underline: bool
    strikethrough: bool

    antialias: bool
    color: pygame.typing.ColorLike
    background_color: pygame.typing.ColorLike | None

    outline_width: int
    outline_color: pygame.typing.ColorLike | None

    render_order: RenderOrder
    z: float


class ImageStyle(typing.NamedTuple):
    __module__ = "dimi"

    padding: DirectionalMeasure = 0
    anchor: Anchor = Anchor.CENTER
    transform: Transform | None = None

    fit: ImageFit | NinePatch = ImageFit.FIT
    repeat: ImageRepeat = ImageRepeat.NONE
    border_radius: Measure | Corners = 0

    scale_quality: ScaleQuality | None = None
    color_modifier: pygame.typing.ColorLike | None = None
    alpha_modifier: int | None = None
    blend_mode: int | None = None

    shape: bool = False
    render_order: RenderOrder = RenderOrder.DEFAULT
    z: float = 0

    def _fast_replace(self, kwargs) -> ImageStyle:
        if not kwargs:
            return self
        g = kwargs.get
        return ImageStyle(
            g("padding", self[0]),
            g("anchor", self[1]),
            g("transform", self[2]),
            g("fit", self[3]),
            g("repeat", self[4]),
            g("border_radius", self[5]),
            g("scale_quality", self[6]),
            g("color_modifier", self[7]),
            g("alpha_modifier", self[8]),
            g("blend_mode", self[9]),
            g("shape", self[10]),
            g("render_order", self[11]),
            g("z", self[12]),
        )


class ImageStyleOverrides(typing.TypedDict, total=False):
    __module__ = "dimi.typehinting"

    padding: DirectionalMeasure
    anchor: Anchor
    transform: Transform | None

    fit: ImageFit | NinePatch
    repeat: ImageRepeat
    border_radius: Measure | Corners

    scale_quality: ScaleQuality | None
    color_modifier: pygame.typing.ColorLike | None
    alpha_modifier: int | None
    blend_mode: int | None

    shape: bool
    render_order: RenderOrder
    z: float
