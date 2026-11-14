import enum
import typing

import pygame

from dimi._context import Context
from dimi._dimi import get_current_context, register_widget
from dimi._primitives import Absolute, Axis
from dimi._widgets.scroll import ScrollAxis, ScrollDict, scroll_set_scroll
from dimi.error import (
    IllegalWidgetOperationError,
    MissingActiveContexError,
    MissingElementForWidget,
)


class ScrollbarAxis(enum.StrEnum):
    X = "x"
    Y = "y"
    BOTH = "both"
    AUTO = "auto"


class ScrollbarAxisIntersection(enum.StrEnum):
    X_DOMINANT = "x_dominant"
    Y_DOMINANT = "y_dominant"
    NEITHER_DOMINANT = "neither_dominant"


class ScrollbarStyle(typing.NamedTuple):
    __module__ = "dimi.widget"

    axis: ScrollbarAxis = ScrollbarAxis.AUTO
    min_handle_size: int = 1
    axis_intersection: ScrollbarAxisIntersection = (
        ScrollbarAxisIntersection.NEITHER_DOMINANT
    )
    axis_intersection_size: int = 0
    handle_padding: int = 0


class ScrollbarStyleOverrides(typing.TypedDict, total=False):
    __module__ = "dimi.typehinting"

    axis: ScrollbarAxis
    min_handle_size: int
    axis_intersection: ScrollbarAxisIntersection
    axis_intersection_size: int
    handle_padding: int


SCROLLBAR_DEFAULT_STYLE = ScrollbarStyle()


class ScrollbarState:
    _scrollbar_stack: typing.ClassVar[list[ScrollbarDict | None]] = [None]

    __module__ = "dimi.typehinting"

    def __init__(self, _instance: ScrollbarDict):
        self._instance = _instance

    @property
    def absolute_position(self) -> Absolute:
        if self._instance["axis"] == ScrollbarAxis.Y:
            return self.absolute_position_y
        elif self._instance["axis"] == ScrollbarAxis.X:
            return self.absolute_position_x
        else:
            raise IllegalWidgetOperationError(
                "The absolute scrollbar position cannot be disambigued if the scrollbar is handling both axis. Use the axis-specific property instead"
            )

    @property
    def handle_size(self) -> float:
        if self._instance["axis"] == ScrollbarAxis.Y:
            return self.handle_size_y
        elif self._instance["axis"] == ScrollbarAxis.X:
            return self.handle_size_x
        else:
            raise IllegalWidgetOperationError(
                "The handle size cannot be disambigued if the scrollbar is handling both axis. Use the axis-specific property instead"
            )

    @property
    def handle_absolute_position(self) -> Absolute:
        if self._instance["axis"] == ScrollbarAxis.Y:
            return self.handle_absolute_position_y
        elif self._instance["axis"] == ScrollbarAxis.X:
            return self.handle_absolute_position_x
        else:
            raise IllegalWidgetOperationError(
                "The handle absolute position cannot be disambigued if the scrollbar is handling both axis. Use the axis-specific property instead"
            )

    @property
    def absolute_position_y(self) -> Absolute:
        return Absolute(
            top=0,
            bottom=self._instance["scroll_state"]["absolute_rect"].h
            - self._instance["y_size"],
            right=0,
        )

    @property
    def absolute_position_x(self) -> Absolute:
        return Absolute(
            left=0,
            right=self._instance["scroll_state"]["absolute_rect"].w
            - self._instance["x_size"],
            bottom=0,
        )

    @property
    def handle_size_y(self) -> float:
        return self._instance["y_handle_size"]

    @property
    def handle_size_x(self) -> float:
        return self._instance["x_handle_size"]

    @property
    def handle_absolute_position_y(self) -> Absolute:
        return Absolute(top=self._instance["y_handle_pos"], center_x="50%")

    @property
    def handle_absolute_position_x(self) -> Absolute:
        return Absolute(left=self._instance["x_handle_pos"], center_y="50%")

    def __enter__(self) -> typing.Self:
        ScrollbarState._scrollbar_stack.append(self._instance)
        return self

    def __exit__(self, *args, **kwargs):
        ScrollbarState._scrollbar_stack.pop()


class ScrollbarHandleState:
    __module__ = "dimi.typehinting"

    def __enter__(self) -> typing.Self:
        return self

    def __exit__(self, *args, **kwargs): ...


SCROLLBAR_HANDLE_STATE = ScrollbarHandleState()


class ScrollbarDict(typing.TypedDict):
    id: int
    scroll_state: ScrollDict
    style: ScrollbarStyle
    axis: ScrollbarAxis
    last_scroll_axis: ScrollAxis
    y_size: float
    x_size: float
    y_handle_size: float
    x_handle_size: float
    y_handle_pos: float
    x_handle_pos: float
    state: ScrollbarState


class ScrollbarHandleDict(typing.TypedDict):
    id: int
    mouse_pos: tuple[float, float] | None = None


def scrollbar_handle_init(id_: int) -> ScrollbarHandleDict:
    return {
        "id": id_,
        "mouse_pos": None,
    }


def scrollbar_init(id_: int, context: Context, style: ScrollbarStyle) -> ScrollbarDict:
    scroll_state: ScrollDict = context.get_widget_state("scroll", None, id_)
    if scroll_state is None:
        raise IllegalWidgetOperationError(
            "dimi.widget.scrollbar() must be called immediately after dimi.widget.scroll()"
        )
    axis = scrollbar_get_axis(style.axis, scroll_state)
    self = {
        "id": id_,
        "scroll_state": scroll_state,
        "style": style,
        "axis": axis,
        "last_scroll_axis": scroll_state["style"].axis,
        "y_size": 0,
        "x_size": 0,
        "y_handle_size": 0,
        "x_handle_size": 0,
        "y_handle_pos": 0,
        "x_handle_pos": 0,
    }
    state = ScrollbarState(self)
    self["state"] = state
    return self


def scrollbar_get_axis(axis: ScrollbarAxis, scroll_state: ScrollDict) -> ScrollbarAxis:
    if axis != ScrollbarAxis.AUTO:
        return axis
    scroll_axis = scroll_state["style"].axis
    if scroll_axis in (
        ScrollAxis.BOTH_PRIMARY_Y,
        ScrollAxis.BOTH_PRIMARY_X,
        ScrollAxis.BOTH_INHERIT_PRIMARY,
    ):
        axis = ScrollbarAxis.BOTH
    elif scroll_axis == ScrollAxis.X:
        axis = ScrollbarAxis.X
    elif scroll_axis == ScrollAxis.Y:
        axis = ScrollbarAxis.Y
    elif scroll_axis == ScrollAxis.INHERIT:
        if scroll_state["container_axis"] == Axis.X:
            axis = ScrollbarAxis.X
        elif scroll_state["container_axis"] == Axis.Y:
            axis = ScrollbarAxis.Y
    return axis


def scrollbar(
    style: ScrollbarStyle | None = None,
    **style_overrides: typing.Unpack[ScrollbarStyleOverrides],
) -> ScrollbarState:
    context = get_current_context()
    if context is None:
        raise MissingActiveContexError()

    if style is None:
        style = SCROLLBAR_DEFAULT_STYLE
    if style_overrides:
        style = style._replace(**style_overrides)

    self: ScrollbarDict = context.get_widget_state(
        "scrollbar", scrollbar_init, init_args=(context, style)
    )
    scroll_state = self["scroll_state"]

    scroll_axis = scroll_state["style"].axis
    if scroll_axis != self["last_scroll_axis"]:
        self["axis"] = scrollbar_get_axis(style.axis, scroll_state)
        self["last_scroll_axis"] = scroll_axis

    rect = scroll_state["absolute_rect"]
    x_size = rect.w
    y_size = rect.h
    if self["axis"] == ScrollbarAxis.BOTH:
        remove_x = style.axis_intersection_size
        remove_y = style.axis_intersection_size
        if style.axis_intersection == ScrollbarAxisIntersection.X_DOMINANT:
            remove_x = 0
        elif style.axis_intersection == ScrollbarAxisIntersection.Y_DOMINANT:
            remove_y = 0
        x_size -= remove_x
        y_size -= remove_y
    self["y_size"] = y_size
    self["x_size"] = x_size

    y_handle_size = y_handle_pos = x_handle_size = x_handle_pos = 0
    if (
        self["axis"] in (ScrollbarAxis.BOTH, ScrollbarAxis.Y)
        and scroll_state["overflow"].y > 0
    ):
        oy = scroll_state["overflow"].y
        total_y = rect.h + oy
        y_size_for_handle = y_size - style.handle_padding * 2
        if total_y != 0 and oy != 0:
            y_handle_size = (rect.h / total_y) * y_size_for_handle
            y_handle_size = max(style.min_handle_size, y_handle_size)
            y_handle_pos = style.handle_padding + (scroll_state["scroll"].y / oy) * (
                y_size_for_handle - y_handle_size
            )
    if (
        self["axis"] in (ScrollbarAxis.BOTH, ScrollbarAxis.X)
        and scroll_state["overflow"].x > 0
    ):
        ox = scroll_state["overflow"].x
        total_x = rect.w + ox
        x_size_for_handle = x_size - style.handle_padding * 2
        if total_x != 0 and ox != 0:
            x_handle_size = (rect.w / total_x) * x_size_for_handle
            x_handle_size = max(style.min_handle_size, x_handle_size)
            x_handle_pos = style.handle_padding + (scroll_state["scroll"].x / ox) * (
                x_size_for_handle - x_handle_size
            )

    self["y_handle_size"] = y_handle_size
    self["x_handle_size"] = x_handle_size
    self["y_handle_pos"] = y_handle_pos
    self["x_handle_pos"] = x_handle_pos

    return self["state"]


def scrollbar_handle(axis: Axis | None = None) -> ScrollbarHandleState:
    context = get_current_context()
    if context is None:
        raise MissingActiveContexError()

    interaction = context.get_last_interaction()
    if interaction is None:
        raise MissingElementForWidget("scrollbar_handle")

    scrollbar_state = ScrollbarState._scrollbar_stack[-1]
    if scrollbar_state is None:
        raise IllegalWidgetOperationError(
            "dimi.widget.scrollbar_handle() must be called inside the active context of a dimi.widget.scrollbar()"
        )

    if axis is None and scrollbar_state["axis"] == ScrollbarAxis.BOTH:
        raise IllegalWidgetOperationError(
            "The axis passed to dimi.widget.scrollbar_handle() cannot be None if the parent scrollbar is handling both axis"
        )

    if axis is None:
        if scrollbar_state["axis"] == ScrollbarAxis.X:
            axis = Axis.X
        elif scrollbar_state["axis"] == ScrollbarAxis.Y:
            axis = Axis.Y

    self: ScrollbarHandleDict = context.get_widget_state(
        "scrollbar_handle", scrollbar_handle_init
    )

    if interaction.just_pressed:
        self["mouse_pos"] = pygame.mouse.get_pos(True)
    elif interaction.just_released:
        self["mouse_pos"] = None
    elif interaction.held and self["mouse_pos"] is not None:
        mouse = pygame.mouse.get_pos(True)
        diff_x = mouse[0] - self["mouse_pos"][0]
        diff_y = mouse[1] - self["mouse_pos"][1]
        if axis == Axis.Y:
            new_pos = scrollbar_state["y_handle_pos"] + diff_y
            padding = scrollbar_state["style"].handle_padding
            available_size = (
                scrollbar_state["y_size"] - scrollbar_state["y_handle_size"]
            ) - padding * 2
            new_pos = min(available_size + padding, max(new_pos, padding))
            if available_size != 0 and new_pos != scrollbar_state["y_handle_pos"]:
                perc = (new_pos - padding) / available_size
                scroll_state = scrollbar_state["scroll_state"]
                new_scroll = perc * scroll_state["overflow"].y
                scroll_set_scroll(scroll_state, scroll_state["scroll"].x, new_scroll)
        elif axis == Axis.X:
            new_pos = scrollbar_state["x_handle_pos"] + diff_x
            padding = scrollbar_state["style"].handle_padding
            available_size = (
                scrollbar_state["x_size"] - scrollbar_state["x_handle_size"]
            ) - padding * 2
            new_pos = min(available_size + padding, max(new_pos, padding))
            if available_size != 0 and new_pos != scrollbar_state["x_handle_pos"]:
                perc = (new_pos - padding) / available_size
                scroll_state = scrollbar_state["scroll_state"]
                new_scroll = perc * scroll_state["overflow"].x
                scroll_set_scroll(scroll_state, new_scroll, scroll_state["scroll"].y)
        self["mouse_pos"] = mouse

    return SCROLLBAR_HANDLE_STATE


register_widget("scrollbar")
register_widget("scrollbar_handle")
