import dataclasses
import enum
import typing

import pygame

from dimi._context import Context
from dimi._dimi import _get_context
from dimi._primitives import Axis

# todo: middle click and drag for auto scrolling like browsers


class ScrollAxis(enum.StrEnum):
    X = "x"
    Y = "y"
    INHERIT = "inherit"
    BOTH_PRIMARY_Y = "both_primary_y"
    BOTH_PRIMARY_X = "both_primary_x"
    BOTH_INHERIT_PRIMARY = "both_inherit_primary"


@dataclasses.dataclass(slots=True, frozen=True)
class ScrollStyle:
    axis: ScrollAxis = ScrollAxis.BOTH_INHERIT_PRIMARY
    opposite_axis_modifier: int | None = pygame.KMOD_SHIFT
    speed: float = 40
    automatic_children_offset: bool = True
    keep_scroll_percentage_on_resize: bool = True


class ScrolLStyleOverrides(typing.TypedDict, total=False):
    axis: ScrollAxis
    opposite_axis_modifier: int | None
    speed: float
    automatic_children_offset: bool
    keep_scroll_percentage_on_resize: bool


DEFAULT_SCROLL_STYLE = ScrollStyle()


class ScrollState:
    _bounds_hovered_id = None

    __module__ = "dimi.typehinting"

    def __init__(self, _instance: ScrollDict):
        self._instance = _instance

    @property
    def children_offset(self) -> tuple[float, float]:
        return (-self._instance["scroll"].x, -self._instance["scroll"].y)

    def scroll(self, x: float = 0, y: float = 0, apply_axis_constraint: bool = True):
        scroll_scroll(self._instance, x, y, apply_axis_constraint)

    def set_scroll(
        self, x: float = 0, y: float = 0, apply_axis_constraint: bool = True
    ):
        scroll_set_scroll(self._instance, x, y, apply_axis_constraint)

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        return


class ScrollDict(typing.TypedDict):
    id: int
    overflow: pygame.Vector2
    style: ScrollStyle
    absolute_rect: pygame.Rect
    scroll: pygame.Vector2
    container_axis: Axis


def scroll_init(id_: int, style: ScrollStyle) -> ScrollDict:
    return {
        "id": id_,
        "overflow": pygame.Vector2(),
        "style": style,
        "absolute_rect": pygame.Rect(),
        "scroll": pygame.Vector2(),
        "container_axis": Axis.Y,
    }


def scroll_scroll(self: ScrollDict, x, y, apply_axis_constraint=True):
    offset = self["scroll"]
    offset.x += x
    offset.y += y
    scroll_clamp(self, apply_axis_constraint)


def scroll_set_scroll(self: ScrollDict, x, y, apply_axis_constraint=True):
    offset = self["scroll"]
    offset.x = x
    offset.y = y
    scroll_clamp(self, apply_axis_constraint)


def scroll_clamp(self: ScrollDict, apply_axis_constraint=True):
    offset = self["scroll"]
    offset.x = pygame.math.clamp(offset.x, 0, self["overflow"].x)
    offset.y = pygame.math.clamp(offset.y, 0, self["overflow"].y)
    if apply_axis_constraint:
        axis = self["style"].axis
        if axis == ScrollAxis.INHERIT:
            axis = ScrollAxis.Y if self["container_axis"] == Axis.Y else ScrollAxis.X
        if axis == ScrollAxis.X:
            offset.y = 0
        elif axis == ScrollAxis.Y:
            offset.x = 0


def scroll_event(event: pygame.Event, self: ScrollDict):
    if self["id"] != ScrollState._bounds_hovered_id:
        return
    if event.type == pygame.MOUSEWHEEL and self["absolute_rect"].collidepoint(
        event.pos
    ):
        axis = self["style"].axis
        if axis == ScrollAxis.INHERIT:
            axis = ScrollAxis.Y if self["container_axis"] == Axis.Y else ScrollAxis.X
        elif axis == ScrollAxis.BOTH_INHERIT_PRIMARY:
            axis = (
                ScrollAxis.BOTH_PRIMARY_Y
                if self["container_axis"] == Axis.Y
                else ScrollAxis.BOTH_PRIMARY_X
            )
        speed = self["style"].speed
        event_x = event_y = 0
        if axis == ScrollAxis.Y:
            event_y = event.y
            event_x = event.x
        elif axis == ScrollAxis.X:
            event_y = event.x
            event_x = event.y
        else:
            if axis == ScrollAxis.BOTH_PRIMARY_Y:
                event_y = event.y
                event_x = event.x
            else:
                event_x = event.y
                event_y = event.x
            if (
                self["style"].opposite_axis_modifier is not None
                and pygame.key.get_mods() & self["style"].opposite_axis_modifier
            ):
                event_y, event_x = event_x, event_y
        scroll_scroll(self, -event_x * speed, -event_y * speed)


def scroll(
    style: ScrollStyle | None = None,
    **style_overrides: typing.Unpack[ScrolLStyleOverrides],
):
    context = _get_context()
    container = context._element_stack[-1]
    interaction = container.interaction()

    if style is None:
        style = DEFAULT_SCROLL_STYLE
    if len(style_overrides) > 0:
        style = dataclasses.replace(style, **style_overrides)

    id_ = context._id_stack[-1]
    if id_ not in context._widget_memories["scroll"]:
        context._widget_memories["scroll"][id_] = scroll_init(id_, style)
    self: ScrollDict = context._widget_memories["scroll"][id_]

    previous_overflow = self["overflow"]
    self["style"] = style
    self["overflow"] = interaction.data.children_overflow
    self["absolute_rect"] = interaction.data.absolute_rect
    self["container_axis"] = container.style.axis

    if (
        self["style"].keep_scroll_percentage_on_resize
        and previous_overflow != self["overflow"]
    ):
        if previous_overflow[0] > 0:
            perc_x = self["scroll"].x / previous_overflow[0]
            self["scroll"].x = perc_x * self["overflow"][0]
        if previous_overflow[1] > 0:
            perc_y = self["scroll"].y / previous_overflow[1]
            self["scroll"].y = perc_y * self["overflow"][1]

    scroll_clamp(self)

    if interaction.bounds_hovered:
        ScrollState._bounds_hovered_id = id_

    state = ScrollState(self)
    if style.automatic_children_offset:
        container.style = dataclasses.replace(
            container.style, children_offset=state.children_offset
        )
    return state


Context._widget_event_handler["scroll"] = scroll_event
