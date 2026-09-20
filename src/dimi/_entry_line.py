import dataclasses
import typing
import enum

import pygame

from dimi._primitives import Measure, Anchor
from dimi._style import RectStyle
from dimi._dimi import _get_context
from dimi._error import IllegalOperation


@dataclasses.dataclass(slots=True, frozen=True)
class EntryLineStyle:
    __module__ = "dimi.widget"

    text_color: pygame.typing.ColorLike = "white"
    placeholder_color: pygame.typing.ColorLike = (100, 100, 100, 255)
    cursor_style: RectStyle = RectStyle(color="white")
    selection_style: RectStyle = RectStyle(color=(20, 80, 225, 255))
    cursor_width: Measure = "10%"
    blink_interval_ms: int = 350
    text_anchor: Anchor = Anchor.MIDLEFT


class EntryLineTarget(enum.IntEnum):
    TEXT = enum.auto()
    NUMBER = enum.auto()
    INTEGER = enum.auto()


class EntryLineValidator(enum.IntEnum):
    LOWERCASE = enum.auto()
    UPPERCASE = enum.auto()
    WINDOWS_PATH = enum.auto()


@dataclasses.dataclass(slots=True, frozen=True)
class EntryLineHotkeys:
    __module__ = "dimi.widget"

    modifier: int = pygame.KMOD_CTRL
    copy: int | None = pygame.K_c
    paste: int | None = pygame.K_v
    cut: int | None = pygame.K_x
    select_all: int | None = pygame.K_a
    undo: int | None = pygame.K_z
    redo: int | None = pygame.K_y


@dataclasses.dataclass(slots=True, frozen=True)
class EntryLineConfig:
    __module__ = "dimi.widget"

    target: EntryLineTarget = EntryLineTarget.TEXT
    character_validator: (
        EntryLineValidator | typing.Callable[[str], str | None] | None
    ) = None
    length_limit: int | None = None
    history: bool | int = True
    double_click_interval_ms: int = 200
    space_characters: str = " "
    hotkeys: EntryLineHotkeys = EntryLineHotkeys()


class EntryLineState:
    __module__ = "dimi.typehinting"

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        return


ENTRY_LINE_DEFAULT_STYLE = EntryLineStyle()
ENTRY_LINE_DEFAULT_CONFIG = EntryLineConfig()


def entry_line_init(initial_text: str, placeholder: str, style: EntryLineStyle, config: EntryLineConfig) -> dict:
    return {
        "text": initial_text,
        "placeholder": placeholder,
        "style": style,
        "config": config,
    }


def entry_line(
    initial_text: str = "",
    placeholder: str = "",
    style: EntryLineStyle | None = None,
    config: EntryLineConfig | None = None,
) -> EntryLineState:
    context = _get_context()
    if context._parent_stack[-1].id != context._element_stack[-1].id:
        raise IllegalOperation(
            "entry_line() can only be used inside the context manager of a parent element (with dimi.begin...), not inside a childless element (with dimi.element...)"
        )
    if style is None:
        style = ENTRY_LINE_DEFAULT_STYLE
    if config is None:
        config = ENTRY_LINE_DEFAULT_CONFIG
    id_ = context._id_stack[-1]
    if id_ not in context._widget_memories["entry_line"]:
        context._widget_memories["entry_line"][id_] = entry_line_init(initial_text, placeholder, style, config)
    self = context._widget_memories["entry_line"][id_]
    result = EntryLineState()
    return result
