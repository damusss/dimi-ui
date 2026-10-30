import dataclasses
import enum

import pygame

from dimi._error import IllegalOperation


class Axis(enum.StrEnum):
    X = "x"
    Y = "y"


class ChooseAxis(enum.StrEnum):
    DEFAULT = "default"
    MIN = "min"
    MAX = "max"


class Align(enum.StrEnum):
    FIRST = "first"
    CENTER = "center"
    LAST = "last"


class FontAlign(enum.IntEnum):
    LEFT = pygame.FONT_LEFT
    CENTER = pygame.FONT_CENTER
    RIGHT = pygame.FONT_RIGHT


class FontDirection(enum.IntEnum):
    LTR = pygame.DIRECTION_LTR
    RTL = pygame.DIRECTION_RTL
    TTB = pygame.DIRECTION_TTB
    BTT = pygame.DIRECTION_BTT


class Anchor(enum.StrEnum):
    CENTER = "center"
    TOPLEFT = "topleft"
    MIDTOP = "midtop"
    TOPRIGHT = "topright"
    MIDRIGHT = "midright"
    BOTTOMRIGHT = "bottomright"
    MIDBOTTOM = "midbottom"
    BOTTOMLEFT = "bottomleft"
    MIDLEFT = "midleft"


class ScaleQuality(enum.IntEnum):
    NEAREST = enum.auto()
    LINEAR = enum.auto()


class ImageFit(enum.IntEnum):
    NONE = enum.auto()
    FIT = enum.auto()
    FIT_SCALE_DOWN = enum.auto()
    FIT_WIDTH = enum.auto()
    FIT_HEIGHT = enum.auto()
    COVER = enum.auto()
    STRETCH = enum.auto()

    @classmethod
    def NINE_PATCH(cls, inset_size: Measure) -> NinePatch:
        return NinePatch(inset_size)


class ImageRepeat(enum.IntEnum):
    NONE = enum.auto()
    X = enum.auto()
    Y = enum.auto()
    BOTH = enum.auto()


class RenderOrder(enum.IntEnum):
    DEFAULT = enum.auto()
    BELOW_CHILDREN = enum.auto()
    ABOVE_CHILDREN = enum.auto()


class SizeIntent:
    __module__ = "dimi.typehinting"

    @staticmethod
    def _sizefy(value: float | str | SizeIntent) -> SizeIntent:
        if isinstance(value, SizeIntent):
            return value
        if isinstance(value, str):
            return Percent(value)
        return Exact(value)

    def _measure(self, relative_x: float, relative_y: float, default_axis=None):
        raise IllegalOperation(
            f"The {type(self).__name__} size intent isn't designed to be used as a measure"
        )


class Exact(SizeIntent):
    __module__ = "dimi"

    def __init__(self, pixels):
        self.pixels = pixels

    def _measure(self, relative_x: float, relative_y: float, default_axis=None):
        return self.pixels

    def __str__(self) -> str:
        return f"Exact({self.pixels} pixels)"

    __repr__ = __str__


class Hug(SizeIntent):
    __module__ = "dimi"

    _default_singleton: Hug | None = None

    def __new__(cls):
        if cls._default_singleton is None:
            hug = super().__new__(cls)
            cls._default_singleton = hug
            return hug
        return cls._default_singleton

    def __str__(self) -> str:
        return "Hug()"

    __repr__ = __str__


class Fill(SizeIntent):
    __module__ = "dimi"

    _default_singleton: Fill | None = None

    def __new__(cls, weight: float = 1):
        if weight != 1:
            fill = super().__new__(cls)
            fill.weight = weight
            return fill
        if cls._default_singleton is None:
            fill = super().__new__(cls)
            fill.weight = 1
            cls._default_singleton = fill
            return fill
        return cls._default_singleton

    def __str__(self) -> str:
        return f"Fill({self.weight})"

    __repr__ = __str__


class Percent(SizeIntent):
    __module__ = "dimi"

    def __init__(
        self, percent: float | str, relative_to: Axis | ChooseAxis = ChooseAxis.DEFAULT
    ):
        if isinstance(percent, str):
            if percent.endswith("%"):
                percent = float(percent[:-1])
            else:
                # todo change this if you need to support dynamic scaling of sorts using strings
                raise ValueError(
                    "Failed to interpret string as percentage: percentage strings must be a valid number ending with '%'."
                )
        self.weight = percent / 100
        self.relative_to: Axis | ChooseAxis = relative_to

    def _measure(
        self, relative_x, relative_y, default_axis: Axis | ChooseAxis | None = None
    ):
        if default_axis is not None and self.relative_to == ChooseAxis.DEFAULT:
            relative_to = default_axis
        else:
            relative_to = self.relative_to
        if relative_to == Axis.X:
            return self.weight * relative_x
        elif relative_to == Axis.Y:
            return self.weight * relative_y
        elif relative_to == ChooseAxis.MIN:
            return self.weight * min(relative_x, relative_y)
        elif relative_to == ChooseAxis.MAX:
            return self.weight * max(relative_x, relative_y)
        raise IllegalOperation("Invalid relative_to specifier.")

    def __str__(self) -> str:
        return f"Percent({self.weight * 100}% of {self.relative_to})"

    __repr__ = __str__


class Span(SizeIntent):
    __module__ = "dimi"

    def __init__(self, weight: float, count: int):
        self.weight = weight
        self.count = count

    def __str__(self) -> str:
        return f"Span({self.weight * 100}% between {self.count})"

    __repr__ = __str__


class Ratio(SizeIntent):
    __module__ = "dimi"

    def __init__(self, ratio_or_width: float, height: float | None = None):
        if height is not None:
            ratio_or_width = ratio_or_width / height
        self.ratio = ratio_or_width

    def __str__(self):
        return f"Ratio(width/height = {self.ratio})"

    __repr__ = __str__


@dataclasses.dataclass(slots=True, frozen=True)
class Directions:
    __module__ = "dimi"

    left: Measure = 0
    top: Measure = 0
    right: Measure = 0
    bottom: Measure = 0


@dataclasses.dataclass(slots=True, frozen=True)
class Corners:
    __module__ = "dimi"

    topleft: Measure = 0
    topright: Measure = 0
    bottomleft: Measure = 0
    bottomright: Measure = 0


type Size = SizeIntent | str | float
type Measure = Exact | Percent | str | float
type DirectionalMeasure = Measure | tuple[Measure, Measure] | Directions


@dataclasses.dataclass(slots=True, frozen=True)
class Constraint:
    __module__ = "dimi"

    min: Measure | None = None
    max: Measure | None = None


@dataclasses.dataclass(slots=True, frozen=True)
class Absolute:
    __module__ = "dimi"

    top: Measure | None = None
    left: Measure | None = None
    bottom: Measure | None = None
    right: Measure | None = None
    center_x: Measure | None = None
    center_y: Measure | None = None


@dataclasses.dataclass(slots=True, frozen=True)
class Wrap:
    __module__ = "dimi"

    line_align: Align = Align.FIRST
    line_spacing: Measure = 3


@dataclasses.dataclass(slots=True, frozen=True)
class Font:
    __module__ = "dimi"

    name: str
    is_sysfont: bool = False
    sysfont_bold: bool = False
    sysfont_italic: bool = False


@dataclasses.dataclass(slots=True, frozen=True)
class Transform:
    __module__ = "dimi"

    offset: pygame.typing.Point = (0, 0)
    scale: pygame.typing.Point = (1, 1)
    angle_deg: float = 0
    flip_x: bool = False
    flip_y: bool = False
    angle_origin: pygame.typing.Point | None = None
    scale_origin: pygame.typing.Point | None = None


@dataclasses.dataclass(slots=True, frozen=True)
class NinePatch:
    __module__ = "dimi"

    inset_size: Measure


TL = 0
TR = 1
BR = 2
BL = 3

L = 0
T = 1
R = 2
B = 3


def get_directional_measure(measure, max_w, max_h, name):
    if isinstance(measure, tuple):
        if len(measure) == 2:
            return tuple(
                SizeIntent._sizefy(m)._measure(max_w, max_h, axis)
                for m, axis in zip(
                    (measure[0], measure[1], measure[0], measure[1]),
                    (Axis.X, Axis.Y, Axis.X, Axis.Y),
                )
            )
        else:
            raise ValueError(
                f"A tuple for {name}s must be of the form ({name} x, {name} y)"
            )
    elif isinstance(measure, Directions):
        return tuple(
            SizeIntent._sizefy(m)._measure(max_w, max_h, axis)
            for m, axis in zip(
                (measure.left, measure.top, measure.right, measure.bottom),
                (Axis.X, Axis.Y, Axis.X, Axis.Y),
            )
        )
    m = SizeIntent._sizefy(measure)._measure(max_w, max_h, Axis.X)
    return (m, m, m, m)


def anchor_rect(rect: pygame.Rect, bounds: pygame.Rect, anchor: Anchor):
    setattr(rect, str(anchor), getattr(bounds, str(anchor)))
