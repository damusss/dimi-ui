import enum
import typing

import pygame

from dimi._components import Component
from dimi._error import IllegalOperation
from dimi._primitives import Directions
from dimi._style import (
    EllipseStyle,
    EllipseStyleOverrides,
    ImageStyle,
    ImageStyleOverrides,
    RectStyle,
    RectStyleOverrides,
    Style,
    TextStyle,
    TextStyleOverrides,
)

if typing.TYPE_CHECKING:
    from dimi._context import Context
    from dimi._node import Node


class Button(enum.IntEnum):
    NONE = -1
    LEFT = enum.auto()
    MIDDLE = enum.auto()
    RIGHT = enum.auto()
    X1 = enum.auto()
    X2 = enum.auto()


class ButtonStatus(enum.IntEnum):
    NONE = -1
    HELD = enum.auto()
    JUST_PRESSED = enum.auto()
    JUST_RELEASED = enum.auto()
    CLICKED = enum.auto()


class HoverStatus(enum.IntEnum):
    NONE = -1
    HOVERED = enum.auto()
    JUST_HOVERED = enum.auto()
    JUST_UNHOVERED = enum.auto()
    BOUNDS = enum.auto()


DEFAULT_STYLE = Style()


class ComputedLayout(typing.NamedTuple):
    padding: Directions
    margin: Directions
    spacing: int

    __module__ = "dimi.typehinting"


HOVERED_STATUSES = (HoverStatus.HOVERED, HoverStatus.JUST_HOVERED)


class Interaction:
    __module__ = "dimi.typehinting"

    def __init__(self, context: Context, memory: Node | None):
        self._is_parent = False
        self._is_element = True
        self._node = context._node
        self.context: Context = context

        self._data_node: Node | None = memory
        inherit_node: Node = memory
        if memory is None:
            inherit_node = self.context._dummy_node

        self.hover_status: HoverStatus = inherit_node.hover_status
        self.button: Button = inherit_node.active_button
        self.button_status: ButtonStatus = inherit_node.active_status

    @property
    def hovered(self) -> bool:
        return self.hover_status in HOVERED_STATUSES

    @property
    def bounds_hovered(self) -> bool:
        return self.hover_status != HoverStatus.NONE

    @property
    def held(self) -> bool:
        return self.button == Button.LEFT and self.button_status == ButtonStatus.HELD

    @property
    def just_pressed(self) -> bool:
        return (
            self.button == Button.LEFT
            and self.button_status == ButtonStatus.JUST_PRESSED
        )

    @property
    def just_released(self) -> bool:
        return (
            self.button == Button.LEFT
            and self.button_status == ButtonStatus.JUST_RELEASED
        )

    @property
    def clicked(self) -> bool:
        return self.button == Button.LEFT and self.button_status == ButtonStatus.CLICKED

    @property
    def middle_clicked(self) -> bool:
        return (
            self.button == Button.MIDDLE and self.button_status == ButtonStatus.CLICKED
        )

    @property
    def right_clicked(self) -> bool:
        return (
            self.button == Button.RIGHT and self.button_status == ButtonStatus.CLICKED
        )

    @property
    def id(self) -> int:
        return self._node.id

    @property
    def relative_rect(self) -> pygame.Rect:
        if self._data_node is None:
            return pygame.Rect()
        return self._data_node.relative_rect

    @property
    def absolute_rect(self) -> pygame.Rect:
        if self._data_node is None:
            return pygame.Rect()
        return self._data_node.absolute_rect

    @property
    def style(self) -> Style:
        if self._data_node is None:
            return DEFAULT_STYLE
        return self._data_node.style

    @property
    def children_overflow(self) -> tuple[float, float]:
        if self._data_node is None:
            return 0, 0
        return self._data_node.children_overflow

    @property
    def computed(self) -> ComputedLayout:
        if self._data_node is None:
            return ComputedLayout(
                Directions(),
                Directions(),
                0,
            )
        return ComputedLayout(
            Directions(*self._data_node.pads_px),
            Directions(*self._data_node.margins_px),
            self._data_node.spacing_px,
        )

    def __enter__(self):
        if self._is_element and not self._is_parent:
            self.context._element_stack.append(self._node)
        return self

    def __exit__(self, *args, **kwargs):
        if self._is_parent:
            self.context._end()
        elif self._is_element:
            self.context._element_stack.pop(-1)

    def _validate_shortcut(self):
        if self._is_parent or self.context._element_stack[-1] is self._node:
            raise IllegalOperation(
                "Component shortcuts are intended to be used for childless elements without context managers."
            )

    def rect(
        self,
        style: RectStyle | None = None,
        **style_overrides: typing.Unpack[RectStyleOverrides],
    ) -> typing.Self:
        self._validate_shortcut()
        with self:
            self.context._component(Component.RECT, None, style, style_overrides)
        return self

    def ellipse(
        self,
        style: EllipseStyle | None,
        **style_overrides: typing.Unpack[EllipseStyleOverrides],
    ) -> typing.Self:
        self._validate_shortcut()
        with self:
            self.context._component(Component.ELLIPSE, None, style, style_overrides)
        return self

    def text(
        self,
        text: str,
        style: TextStyle | None = None,
        **style_overrides: typing.Unpack[TextStyleOverrides],
    ) -> typing.Self:
        self._validate_shortcut()
        with self:
            self.context._component(
                Component.TEXT,
                text if isinstance(text, str) else str(text),
                style,
                style_overrides,
            )
        return self

    def image(
        self,
        image,
        style: ImageStyle | None = None,
        **style_overrides: typing.Unpack[ImageStyleOverrides],
    ) -> typing.Self:
        self._validate_shortcut()
        with self:
            self.context._component(Component.IMAGE, image, style, style_overrides)
        return self
