import dataclasses
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


@dataclasses.dataclass(slots=True)
class InteractionData:
    __module__ = "dimi.typehinting"

    relative_rect: pygame.Rect
    absolute_rect: pygame.Rect
    style: Style
    computed_padding: Directions
    computed_margin: Directions
    computed_spacing: int
    children_overflow: pygame.Vector2


class Interaction:
    __module__ = "dimi.typehinting"

    def __init__(self, context: Context):
        self._is_parent = False
        self._is_element = True
        self._node = context._node

        self.context = context
        self.id = self._node.id

        self._data: InteractionData | None = None
        self._data_node: Node | None = self.context._node_memory.get(self.id, None)

        inherit_node: Node = self._data_node
        if self._data_node is None:
            inherit_node = self.context._dummy_node

        self.hover_status: HoverStatus = inherit_node.hover_status
        self.button: Button = Button(inherit_node.active_button)
        self.button_status: ButtonStatus = inherit_node.active_status

    @property
    def hovered(self) -> bool:
        return self.hover_status in (
            HoverStatus.HOVERED,
            HoverStatus.JUST_HOVERED,
        )

    @property
    def bounds_hovered(self) -> bool:
        return self.hover_status in (
            HoverStatus.HOVERED,
            HoverStatus.JUST_HOVERED,
            HoverStatus.JUST_UNHOVERED,
            HoverStatus.BOUNDS,
        )

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
    def data(self) -> InteractionData:
        if self._data is None:
            if self._data_node is None:
                data = InteractionData(
                    pygame.Rect(),
                    pygame.Rect(),
                    Style(),
                    Directions(),
                    Directions(),
                    0,
                    pygame.Vector2(),
                )
            else:
                data = InteractionData(
                    self._data_node.relative_rect.copy(),
                    self._data_node.absolute_rect.copy(),
                    self._data_node.style,
                    Directions(*self._data_node.pads_px),
                    Directions(*self._data_node.margins_px),
                    self._data_node.spacing_px,
                    self._data_node.children_overflow.copy(),
                )
            self._data = data
            return data
        return self._data

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
