import typing

import pygame

from dimi._context import Context
from dimi._dimi import get_current_context, register_widget
from dimi._interaction import Interaction
from dimi._primitives import CursorLike
from dimi.error import MissingActiveContexError, MissingElementForWidget


class CursorStyle(typing.NamedTuple):
    __module__ = "dimi.widget"

    hovered: CursorLike | None = pygame.SYSTEM_CURSOR_HAND
    bounds_hovered: CursorLike | None = None
    held: CursorLike | None = None
    rules: dict[typing.Callable[[Interaction], bool], CursorLike] | None = None


class CursorStyleOverrides(typing.TypedDict, total=False):
    hovered: CursorLike | None
    bounds_hovered: CursorLike | None
    held: CursorLike | None
    rules: dict[typing.Callable[[Interaction], bool], CursorLike] | None


CURSOR_DEFAULT_STYLE = CursorStyle()


class CursorState:
    _cursor: typing.ClassVar[CursorLike | None] = None

    __module__ = "dimi.typehinting"

    def __enter__(self) -> typing.Self:
        return self

    def __exit__(self, *args, **kwargs): ...


CURSOR_STATE = CursorState()


def cursor_on_start(_context: Context):
    CursorState._cursor = None


def cursor(
    style: CursorStyle | None = None,
    **style_overrides: typing.Unpack[CursorStyleOverrides],
):
    if style is None:
        style = CURSOR_DEFAULT_STYLE
    if style_overrides:
        style = style._replace(**style_overrides)

    context = get_current_context()
    if context is None:
        raise MissingActiveContexError()
    interaction = context.get_last_interaction()
    if interaction is None:
        raise MissingElementForWidget("cursor")

    assigned = None
    if style.rules is not None:
        for rule_callback, rule_cursor in style.rules.items():
            if rule_callback(interaction):
                assigned = rule_cursor
                break
    if assigned is None:
        if interaction.held and style.held is not None:
            assigned = style.held
        elif interaction.hovered and style.hovered is not None:
            assigned = style.hovered
        elif interaction.bounds_hovered and style.bounds_hovered is not None:
            assigned = style.bounds_hovered

    if assigned is not None:
        CursorState._cursor = assigned

    return CURSOR_STATE


def get_cursor() -> CursorLike | None:
    return CursorState._cursor


register_widget("cursor", on_start=cursor_on_start)
