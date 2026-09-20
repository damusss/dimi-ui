import typing
import dataclasses

import pygame

from dimi._primitives import (
    Constraint,
    Wrap,
    Absolute,
    Axis,
    Align,
    FontAlign,
    FontDirection,
    Size,
    Measure,
    DirectionalMeasure,
    Anchor,
    Corners,
    Font,
    Transform,
    Fill,
    ScaleQuality,
    ImageFit,
    ImageRepeat,
NinePatch,
RenderOrder,
)

# todo implement wrapping


@dataclasses.dataclass(slots=True, frozen=True)
class Style:
    __module__ = "dimi"

    width: Size = 0
    height: Size = 0

    width_constraint: Constraint | None = None
    height_constraint: Constraint | None = None

    padding: DirectionalMeasure = 5
    margin: DirectionalMeasure = 0
    spacing: Measure = 3

    z: int = 0
    blocking: bool = True
    clip_graphics: bool = True
    position: Absolute | None = None
    offset: pygame.typing.Point = (0, 0)

    axis: Axis = Axis.Y
    align_children: Align = Align.FIRST
    align_self: Align = Align.FIRST

    wrap_children: Wrap | None = None

class StyleOverrides(typing.TypedDict, total=False):
    __module__ = "dimi.typehinting"

    width: Size
    height: Size

    width_constraint: Constraint | None
    height_constraint: Constraint | None

    padding: DirectionalMeasure
    margin: DirectionalMeasure
    spacing: Measure

    z: int
    blocking: bool
    clip_graphics: bool
    position: Absolute | None
    offset: pygame.typing.Point

    axis: Axis
    align_children: Align
    align_self: Align

    wrap_children: Wrap | None


# todo consider dash size/offset. maybe not because border radius is not supported
@dataclasses.dataclass(slots=True, frozen=True)
class RectStyle:
    __module__ = "dimi"

    padding: DirectionalMeasure = 0
    offset: pygame.typing.Point = (0, 0)

    border_radius: Measure | Corners = 0
    border_width: Measure = 0

    color: pygame.typing.ColorLike | None = (0, 0, 0, 0)
    antialias: bool = True

    aspect_ratio: float = 0.0
    anchor: Anchor = Anchor.CENTER

    shape: bool = False
    render_order: RenderOrder = RenderOrder.DEFAULT


class RectStyleOverrides(typing.TypedDict, total=False):
    __module__ = "dimi.typehinting"

    padding: DirectionalMeasure
    offset: pygame.typing.Point

    border_radius: Measure | Corners
    border_width: Measure

    color: pygame.typing.ColorLike
    antialias: bool

    aspect_ratio: float
    anchor: Anchor

    shape: bool
    render_order: RenderOrder


@dataclasses.dataclass(slots=True, frozen=True)
class EllipseStyle:
    __module__ = "dimi"

    padding: DirectionalMeasure = 0
    offset: pygame.typing.Point = (0, 0)

    border_width: Measure = 0

    color: pygame.typing.ColorLike | None = (0, 0, 0, 0)
    antialias: bool = True

    aspect_ratio: float = 0.0
    anchor: Anchor = Anchor.CENTER

    shape: bool = False
    render_order: RenderOrder = RenderOrder.DEFAULT


class EllipseStyleOverrides(typing.TypedDict, total=False):
    __module__ = "dimi.typehinting"

    padding: DirectionalMeasure
    offset: pygame.typing.Point

    border_width: Measure

    color: pygame.typing.ColorLike | None
    antialias: bool

    aspect_ratio: float
    anchor: Anchor

    shape: bool
    render_order: RenderOrder


# todo support rich text


@dataclasses.dataclass(slots=True, frozen=True)
class TextStyle:
    __module__ = "dimi"

    font: pygame.Font | Font | None = None
    size: Measure | Fill | None = None

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
    wrap: bool = True

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


@dataclasses.dataclass(slots=True, frozen=True)
class ImageStyle:
    __module__ = "dimi"

    padding: DirectionalMeasure = 0
    anchor: Anchor = Anchor.CENTER
    transform: Transform | None = None

    fit: ImageFit | NinePatch = ImageFit.NONE
    repeat: ImageRepeat = ImageRepeat.NONE
    border_radius: Measure | Corners = 0

    scale_quality: ScaleQuality | None = None
    color_modifier: pygame.typing.ColorLike | None = None
    alpha_modifier: int | None = None
    blend_mode: int | None = None

    shape: bool = False
    render_order: RenderOrder = RenderOrder.DEFAULT

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
