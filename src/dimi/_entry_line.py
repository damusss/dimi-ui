import dataclasses
import enum
import typing

import pygame

from dimi._components import Component
from dimi._context import Context
from dimi._dimi import _get_context
from dimi._primitives import (
    Anchor,
    Axis,
    B,
    Directions,
    Font,
    FontAlign,
    L,
    Measure,
    Percent,
    R,
    SizeIntent,
    T,
    get_directional_measure,
)
from dimi._style import RectStyle, TextStyle


class EntryLineInputAnchor(enum.IntEnum):
    LEFT = FontAlign.LEFT
    CENTER = FontAlign.CENTER
    RIGHT = FontAlign.RIGHT


@dataclasses.dataclass(slots=True, frozen=True)
class EntryLineStyle:
    __module__ = "dimi.widget"

    text_color: pygame.typing.ColorLike = "white"
    placeholder_color: pygame.typing.ColorLike = (100, 100, 100, 255)
    invalid_number_color: pygame.typing.ColorLike = (255, 0, 0, 255)
    cursor_style: RectStyle = RectStyle(color="white")
    selection_style: RectStyle = RectStyle(color=(20, 80, 225, 255))
    cursor_width: Measure = "5%"
    blink_interval_ms: int = 350
    input_anchor: EntryLineInputAnchor | FontAlign = EntryLineInputAnchor.LEFT


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
class EntryLineBindings:
    __module__ = "dimi.widget"

    left: tuple[int] = (pygame.K_LEFT,)
    right: tuple[int] = (pygame.K_RIGHT,)
    cursor_start: tuple[int] = (pygame.K_UP,)
    cursor_end: tuple[int] = (pygame.K_DOWN,)
    delete_left: tuple[int] = (pygame.K_BACKSPACE,)
    delete_right: tuple[int] = (pygame.K_DELETE,)
    submit: tuple[int] = (pygame.K_RETURN,)
    select_modifier: int | None = pygame.KMOD_SHIFT
    whole_words_modifier: int | None = pygame.KMOD_CTRL


@dataclasses.dataclass(slots=True, frozen=True)
class EntryLineConfig:
    __module__ = "dimi.widget"

    target: EntryLineTarget = EntryLineTarget.TEXT
    validator: EntryLineValidator | typing.Callable[[str], str | None] | None = None
    length_limit: int | None = None
    history: bool | int = True
    double_click_interval_ms: int = 300
    space_characters: str = " "
    hotkeys: EntryLineHotkeys = EntryLineHotkeys()
    bindings: EntryLineBindings = EntryLineBindings()


class EntryLineState:
    __module__ = "dimi.typehinting"

    def __init__(self, _instance: EntryLineDict):
        self._instance = _instance
        self._submitted: bool = _instance["submitted"]
        self._edited: bool = _instance["edited"]
        self._focus_changed: bool = _instance["focus_changed"]
        _instance["submitted"] = False
        _instance["edited"] = False
        _instance["focus_changed"] = False

    @property
    def submitted(self) -> bool:
        return self._submitted

    @property
    def edited(self) -> bool:
        return self._edited

    @property
    def focused(self) -> bool:
        return self._instance["focused"]

    @focused.setter
    def focused(self, value: bool):
        if value:
            self._instance["request_unfocus"] = -1
            entry_line_blink(self._instance)
        self._instance["focused"] = value

    @property
    def just_focused(self):
        return self._instance["focused"] and self._focus_changed

    @property
    def just_unfocused(self):
        return (not self._instance["focused"]) and self._focus_changed

    @property
    def text(self) -> str:
        return self._instance["text"]

    @property
    def text_strip(self) -> str:
        return self._instance["text"].strip()

    @property
    def text_as_int(self) -> int | None:
        try:
            return int(self._instance["text"].strip())
        except ValueError:
            return None

    @property
    def text_as_number(self) -> int | float | None:
        text = self._instance["text"].strip()
        try:
            return int(text)
        except ValueError:
            try:
                return float(text)
            except ValueError:
                return None

    @property
    def cursor(self) -> int:
        return self._instance["cursor"]

    @property
    def selection_cursors(self) -> tuple[int, int] | None:
        return entry_line_get_selection_cursors(self._instance)

    @property
    def selection(self) -> str:
        selection = entry_line_get_selection(
            self._instance, entry_line_get_selection_cursors(self._instance)
        )
        if selection is None:
            return ""
        return selection

    def set_cursor(self, cursor: int):
        self._instance["cursor"] = cursor
        entry_line_clamp_cursor(self._instance)

    def move_cursor(self, amount: int):
        self._instance["cursor"] += amount
        entry_line_clamp_cursor(self._instance)

    def set_text(self, text: str, sanitize: bool = True):
        if sanitize:
            text = entry_line_sanitize_text(self._instance, text)
        self._instance["text"] = text
        self._instance["cursor"] = len(text)

    def sanitize_text(self, text: str) -> str:
        return entry_line_sanitize_text(
            self._instance,
            text,
        )

    def append_text(
        self, text: str, sanitize: bool = True, apply_length_limit: bool = True
    ):
        self._instance["cursor"] = len(self._instance["text"])
        entry_line_insert(self._instance, text, sanitize, apply_length_limit)

    def insert_text(
        self,
        text: str,
        position: int,
        sanitize: bool = True,
        apply_length_limit: bool = True,
    ):
        self._instance["cursor"] = position
        entry_line_clamp_cursor(self._instance)
        entry_line_insert(self._instance, text, sanitize, apply_length_limit)

    def delete_text(self, amount: int):
        entry_line_delete(self._instance, amount)

    def select(self, start: int, end: int):
        self._instance["cursor"] = end
        self._instance["selection_start"] = start
        entry_line_clamp_cursor(self._instance)

    def select_all(self):
        self._instance["cursor"] = 0
        self._instance["selection_start"] = len(self._instance["text"])
        entry_line_clamp_cursor(self._instance)

    def cancel_selection(self):
        self._instance["selection_start"] = None

    def delete_selection(self):
        entry_line_erase_selection(self._instance)

    def undo(self):
        entry_line_undo(self._instance)

    def redo(self):
        entry_line_redo(self._instance)

    def save_to_history(self):
        entry_line_save_to_history(self._instance)

    def copy(self):
        entry_line_copy(self._instance)

    def cut(self):
        entry_line_cut(self._instance, False)

    def paste(self):
        entry_line_paste(self._instance, False)

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        return


ENTRY_LINE_DEFAULT_STYLE = EntryLineStyle()
ENTRY_LINE_DEFAULT_CONFIG = EntryLineConfig()


class EntryLineDict(typing.TypedDict):
    id: int
    text: str
    placeholder: str
    style: EntryLineStyle
    config: EntryLineConfig
    cursor: int
    focused: bool
    request_unfocus: int
    focus_changed: bool
    submitted: bool
    edited: bool
    display_cursor: bool
    blink_time: int
    offset: int
    selection_start: int | None
    history: list[tuple[str, int, int | None]]
    history_index: int
    last_mouse_pos: tuple | None
    first_mouse_cursor: int | None
    click_time: int
    click_count: int


def entry_line_init(
    id_: int,
    initial_text: str,
    placeholder: str,
    style: EntryLineStyle,
    config: EntryLineConfig,
) -> EntryLineDict:
    return {
        "id": id_,
        "text": initial_text,
        "placeholder": placeholder,
        "style": style,
        "config": config,
        "cursor": len(initial_text),
        "focused": False,
        "request_unfocus": -1,
        "focus_changed": False,
        "submitted": False,
        "edited": False,
        "display_cursor": True,
        "blink_time": 0,
        "offset": 0,
        "selection_start": None,
        "history": [],
        "history_index": -1,
        "last_mouse_pos": None,
        "first_mouse_cursor": None,
        "click_time": 0,
        "click_count": 1,
    }


def entry_line_save_to_history(self: EntryLineDict):
    config_history = self["config"].history
    if config_history is False:
        return

    state = (self["text"], self["cursor"], self["selection_start"])
    if len(self["history"]) <= 0:
        self["history"].append(state)
        self["history_index"] = 0
    else:
        if self["history_index"] < len(self["history"]) - 1:
            self["history"] = self["history"][: self["history_index"]]
        self["history"].append(state)
        self["history_index"] += 1

    if config_history is not False and config_history is not True:
        limit = abs(config_history)
        if len(self["history"]) > limit:
            self["history"] = self["history"][len(self["history"]) - limit :]
            self["history_index"] = len(self["history"]) - 1


def entry_line_history_apply(self: EntryLineDict):
    state = self["history"][self["history_index"]]
    self["text"] = state[0]
    self["cursor"] = state[1]
    self["selection_start"] = state[2]


def entry_line_undo(self: EntryLineDict):
    if self["config"].history is False:
        return
    if self["history_index"] <= 0:
        return
    if self["history_index"] == len(self["history"]) - 1:
        entry_line_save_to_history(self)
    self["history_index"] -= 1
    entry_line_history_apply(self)


def entry_line_redo(self: EntryLineDict):
    if self["config"].history is False:
        return
    if self["history_index"] >= len(self["history"]) - 1:
        return
    self["history_index"] += 1
    entry_line_history_apply(self)


def entry_line_blink(self: EntryLineDict):
    self["display_cursor"] = True
    self["blink_time"] = pygame.time.get_ticks()


def entry_line_clamp_cursor(self: EntryLineDict, cursor: int | None = None):
    if cursor is None:
        self["cursor"] = max(0, min(len(self["text"]), self["cursor"]))
        if self["selection_start"] is not None:
            self["selection_start"] = max(
                0, min(len(self["text"]), self["selection_start"])
            )
        return 0
    else:
        return max(0, min(len(self["text"]), cursor))


def entry_line_sanitize_text(self: EntryLineDict, text: str):
    validator = self["config"].validator
    if validator is not None:
        if validator == EntryLineValidator.LOWERCASE:
            text = text.lower()
        elif validator == EntryLineValidator.UPPERCASE:
            text = text.upper()
        elif validator == EntryLineValidator.WINDOWS_PATH:
            for forbidden in "":
                text = text.replace(forbidden, "")
        else:
            text = validator(text)
    return text


def entry_line_apply_length_limit(self: EntryLineDict, text: str):
    if self["config"].length_limit is not None:
        available_length = self["config"].length_limit
        available_length -= len(self["text"])
        if len(text) > available_length:
            text = text[:available_length]
    return text


def entry_line_full_sanitize(self: EntryLineDict, text: str):
    return entry_line_apply_length_limit(self, entry_line_sanitize_text(self, text))


def entry_line_insert(
    self: EntryLineDict, text: str, sanitize: bool = True, apply_length_limit=True
):
    if sanitize:
        text = entry_line_sanitize_text(self, text)
    if apply_length_limit:
        text = entry_line_apply_length_limit(self, text)
    self["text"] = (
        self["text"][: self["cursor"]] + text + self["text"][self["cursor"] :]
    )
    self["cursor"] += len(text)


def entry_line_get_action_distance(
    self: EntryLineDict,
    direction: int,
    whole_words: bool,
    force_target_spaces: bool | None = None,
):
    start_cursor = self["cursor"]
    if not whole_words:
        end_cursor = start_cursor + direction
        end_cursor = entry_line_clamp_cursor(self, end_cursor)
        return end_cursor - start_cursor
    if direction == -1 and self["cursor"] <= 0:
        return 0
    if direction == 1 and self["cursor"] >= len(self["text"]):
        return 0
    next_index = self["cursor"] + (0 if direction == 1 else -1)
    first_next = self["text"][next_index]
    spaces = self["config"].space_characters
    if force_target_spaces is None:
        target_spaces = first_next in spaces
    else:
        target_spaces = force_target_spaces
    index = next_index
    distance = 0
    while True:
        if target_spaces:
            if self["text"][index] not in spaces:
                break
        else:
            if self["text"][index] in spaces:
                break
        distance += 1
        index += direction
        if index <= 0 or index >= len(self["text"]):
            if direction == -1:
                distance += 1
            break
    distance = distance * direction
    if self["cursor"] + distance < 0:
        distance += 1
    if self["cursor"] + distance > len(self["text"]):
        distance -= 1
    return distance


def entry_line_delete(self: EntryLineDict, amount: int):
    if amount == 0:
        return
    start = self["cursor"]
    end = self["cursor"] + amount
    end = entry_line_clamp_cursor(self, end)
    self["text"] = self["text"][: min(start, end)] + self["text"][max(start, end) :]
    if amount < 0:
        self["cursor"] += amount


def entry_line_erase_selection(self: EntryLineDict):
    if self["selection_start"] is None:
        return
    start, end = entry_line_get_selection_cursors(self)
    if start == end:
        self["selection_start"] = None
        return
    self["text"] = self["text"][:start] + self["text"][end:]
    self["cursor"] = start
    self["selection_start"] = None


def entry_line_get_selection_cursors(self: EntryLineDict):
    if self["selection_start"] is None:
        return None
    return min(self["selection_start"], self["cursor"]), max(
        self["selection_start"], self["cursor"]
    )


def entry_line_get_selection(self: EntryLineDict, cursors):
    if cursors is None:
        return None
    return self["text"][cursors[0] : cursors[1]]


def entry_line_redundant_selection(self: EntryLineDict):
    if self["selection_start"] == self["cursor"]:
        self["selection_start"] = None


def entry_line_select_all(self: EntryLineDict):
    self["selection_start"] = 0
    self["cursor"] = len(self["text"])
    entry_line_redundant_selection(self)


def entry_line_paste(self: EntryLineDict, save_to_history=True):
    if save_to_history:
        entry_line_save_to_history(self)
    if self["selection_start"] is not None:
        entry_line_erase_selection(self)
    entry_line_insert(self, pygame.scrap.get_text())


def entry_line_copy(self: EntryLineDict):
    if self["selection_start"] is not None:
        pygame.scrap.put_text(
            entry_line_get_selection(self, entry_line_get_selection_cursors(self))
        )


def entry_line_cut(self: EntryLineDict, save_to_history=True):
    if self["selection_start"] is not None:
        if save_to_history:
            entry_line_save_to_history(self)
        pygame.scrap.put_text(
            entry_line_get_selection(self, entry_line_get_selection_cursors(self))
        )
        entry_line_erase_selection(self)


def entry_line_event(event: pygame.Event, self: EntryLineDict):
    if event.type == pygame.MOUSEBUTTONDOWN and event.button == pygame.BUTTON_LEFT:
        self["request_unfocus"] = 1
    if self["focused"]:
        if event.type == pygame.KEYDOWN:
            hotkeys = self["config"].hotkeys
            bindings = self["config"].bindings
            whole_words = (
                bindings.whole_words_modifier is not None
                and event.mod & bindings.whole_words_modifier
            )
            select = (
                bindings.select_modifier is not None
                and event.mod & bindings.select_modifier
            )
            hotkey_modifier = event.mod & hotkeys.modifier
            if event.key in bindings.submit:
                self["submitted"] = True
            elif event.key in bindings.left:
                entry_line_blink(self)
                if not select and self["selection_start"] is not None:
                    self["cursor"] = min(self["cursor"], self["selection_start"])
                    self["selection_start"] = None
                else:
                    if select and self["selection_start"] is None:
                        self["selection_start"] = self["cursor"]
                    distance = entry_line_get_action_distance(self, -1, whole_words)
                    self["cursor"] += distance
                    entry_line_redundant_selection(self)
            elif event.key in bindings.right:
                entry_line_blink(self)
                if not select and self["selection_start"] is not None:
                    self["cursor"] = max(self["cursor"], self["selection_start"])
                    self["selection_start"] = None
                else:
                    if select and self["selection_start"] is None:
                        self["selection_start"] = self["cursor"]
                    distance = entry_line_get_action_distance(self, 1, whole_words)
                    self["cursor"] += distance
                    entry_line_redundant_selection(self)
            elif event.key in bindings.cursor_start:
                entry_line_blink(self)
                self["cursor"] = 0
                self["selection_start"] = None
            elif event.key in bindings.cursor_end:
                entry_line_blink(self)
                self["cursor"] = len(self["text"])
                self["selection_start"] = None
            elif event.key in bindings.delete_left:
                prev = self["text"]
                entry_line_save_to_history(self)
                entry_line_blink(self)
                if self["selection_start"] is not None:
                    entry_line_erase_selection(self)
                else:
                    distance = entry_line_get_action_distance(self, -1, whole_words)
                    entry_line_delete(self, distance)
                if prev != self["text"]:
                    self["edited"] = True
            elif event.key in bindings.delete_right:
                prev = self["text"]
                entry_line_save_to_history(self)
                entry_line_blink(self)
                if self["selection_start"] is not None:
                    entry_line_erase_selection(self)
                else:
                    distance = entry_line_get_action_distance(self, 1, whole_words)
                    entry_line_delete(self, distance)
                if prev != self["text"]:
                    self["edited"] = True
            elif hotkey_modifier and event.key == hotkeys.copy:
                entry_line_copy(self)
            elif hotkey_modifier and event.key == hotkeys.cut:
                prev = self["text"]
                entry_line_cut(self)
                if prev != self["text"]:
                    self["edited"] = True
            elif hotkey_modifier and event.key == hotkeys.paste:
                prev = self["text"]
                entry_line_paste(self)
                if prev != self["text"]:
                    self["edited"] = True
            elif hotkey_modifier and event.key == hotkeys.select_all:
                entry_line_select_all(self)
            elif hotkey_modifier and event.key == hotkeys.undo:
                prev = self["text"]
                entry_line_undo(self)
                entry_line_blink(self)
                if prev != self["text"]:
                    self["edited"] = True
            elif hotkey_modifier and event.key == hotkeys.redo:
                prev = self["text"]
                entry_line_redo(self)
                entry_line_blink(self)
                if prev != self["text"]:
                    self["edited"] = True

        elif event.type == pygame.TEXTINPUT:
            prev = self["text"]
            entry_line_save_to_history(self)
            entry_line_blink(self)
            if self["selection_start"] is not None:
                entry_line_erase_selection(self)
            entry_line_insert(self, event.text)
            if prev != self["text"]:
                self["edited"] = True


def entry_line_number_valid(self: EntryLineDict):
    if self["config"].target == EntryLineTarget.TEXT:
        return True
    elif self["config"].target == EntryLineTarget.INTEGER:
        converter = int
    elif self["config"].target == EntryLineTarget.NUMBER:
        converter = float
    else:
        raise NotImplementedError
    try:
        converter(self["text"].strip())
        return True
    except ValueError:
        return False


def entry_line_cursor_intersection(font: pygame.Font, text: str, mouse: int):
    low = 0
    high = len(text)
    closest = 0

    while low <= high:
        mid = int((low + high) // 2)
        size = font.size(text[:mid])[0]

        if size == mouse:
            return mid
        elif size < mouse:
            closest = mid
            low = mid + 1
        else:
            high = mid - 1

    left = font.size(text[:closest])[0]
    right = font.size(text[: closest + 1])[0]
    if abs(mouse - left) < abs(right - mouse):
        return closest
    return closest + 1


def entry_line(
    initial_text: str = "",
    placeholder: str = "",
    style: EntryLineStyle | None = None,
    config: EntryLineConfig | None = None,
) -> EntryLineState:
    context = _get_context()
    container = context._element_stack[-1]
    interaction = container.interaction()

    if style is None:
        style = ENTRY_LINE_DEFAULT_STYLE
    if config is None:
        config = ENTRY_LINE_DEFAULT_CONFIG

    id_ = context._id_stack[-1]
    if id_ not in context._widget_memories["entry_line"]:
        context._widget_memories["entry_line"][id_] = entry_line_init(
            id_, initial_text, placeholder, style, config
        )
    self: EntryLineDict = context._widget_memories["entry_line"][id_]
    self["placeholder"] = placeholder
    self["style"] = style
    self["config"] = config

    last_focus = self["focused"]

    if self["request_unfocus"] == 1:
        self["request_unfocus"] = 0
    elif self["request_unfocus"] == 0:
        self["focused"] = False
        self["selection_start"] = None
    if interaction.just_pressed:
        self["focused"] = True
        self["request_unfocus"] = -1
        entry_line_blink(self)

    if self["focused"] != last_focus:
        self["focus_changed"] = True

    entry_line_redundant_selection(self)

    display_text = self["text"]
    display_color = self["style"].text_color
    if display_text == "":
        display_text = self["placeholder"]
        display_color = self["style"].placeholder_color
    elif not entry_line_number_valid(self):
        display_color = self["style"].invalid_number_color

    text_style: TextStyle = context._style_stacks[Component.TEXT][-1]
    container_rect = interaction.data.absolute_rect
    padding = get_directional_measure(
        text_style.padding, container_rect.w, container_rect.h, "padding"
    )
    available_h = container_rect.h - padding[T] - padding[B]
    if text_style.font is None or isinstance(text_style.font, Font):
        font = context.canvas._get_font(text_style.font)
        height = max(1, int(Percent(100)._measure(0, available_h, Axis.Y)))
        font.point_size = height
    else:
        font = text_style.font
        height = font.point_size

    align_offset = 0
    cursor_align_offset = 0
    text_size = None
    if self["style"].input_anchor != EntryLineInputAnchor.LEFT:
        text_size = font.size(self["text"])[0]
        available_w = container_rect.w - padding[L] - padding[R]
        placeholder_size = 0
        if self["text"] == "":
            placeholder_size = font.size(display_text)[0]
        if self["style"].input_anchor == EntryLineInputAnchor.CENTER:
            if text_size < available_w:
                self["offset"] = 0
            align_offset = cursor_align_offset = available_w / 2 - text_size / 2
            if self["text"] == "":
                align_offset -= placeholder_size / 2
                cursor_align_offset += placeholder_size / 2
        elif self["style"].input_anchor == EntryLineInputAnchor.RIGHT:
            align_offset = cursor_align_offset = available_w - text_size
            if self["text"] == "":
                align_offset -= placeholder_size

    text_before_cursor = self["text"][: self["cursor"]]
    size_before_cursor = font.size(text_before_cursor)[0]
    cursor_width = max(
        1, SizeIntent._sizefy(self["style"].cursor_width)._measure(0, height, Axis.Y)
    )
    cursor_left = padding[L] + size_before_cursor + cursor_align_offset

    right_diff = (
        cursor_left + cursor_width + self["offset"] - (container_rect.w - padding[R])
    )
    if right_diff > 0 and container_rect.w != 0:
        self["offset"] -= right_diff
    left_diff = padding[L] - (cursor_left + self["offset"])
    if left_diff > 0 and container_rect.w != 0:
        self["offset"] += left_diff

    if self["text"] != "" and (interaction.held or interaction.just_pressed):
        if interaction.just_pressed:
            if (
                pygame.time.get_ticks() - self["click_time"]
                <= self["config"].double_click_interval_ms
            ):
                self["click_count"] += 1
                if self["click_count"] > 3:
                    self["click_count"] = 1
            else:
                self["click_count"] = 1
            self["click_time"] = pygame.time.get_ticks()
        viewport = context.viewport
        mouse = pygame.mouse.get_pos(True)
        mouse_pos = (mouse[0] - viewport.x, mouse[1] - viewport.y)
        container_mouse = (
            mouse_pos[0] - container_rect.x,
            mouse_pos[1] - container_rect.y,
        )
        text_mouse = container_mouse[0] - (padding[L] + self["offset"] + align_offset)
        if text_mouse != self["last_mouse_pos"]:
            if text_size is None:
                text_size = font.size(self["text"])[0]
            if text_mouse > text_size:
                cursor = len(self["text"])
            else:
                cursor = entry_line_cursor_intersection(font, self["text"], text_mouse)
            self["cursor"] = cursor
            entry_line_clamp_cursor(self)
            entry_line_blink(self)
            self["last_mouse_pos"] = text_mouse
            if self["first_mouse_cursor"] is None:
                self["first_mouse_cursor"] = cursor
                self["selection_start"] = None
            else:
                if (
                    self["first_mouse_cursor"] != cursor
                    and self["selection_start"] is None
                ):
                    self["selection_start"] = self["first_mouse_cursor"]
        if (
            self["first_mouse_cursor"] is not None
            and self["click_count"] > 1
            and self["cursor"] == self["first_mouse_cursor"]
        ):
            if self["click_count"] == 3:
                entry_line_select_all(self)
            else:
                character = (
                    self["text"][self["cursor"]]
                    if self["cursor"] < len(self["text"])
                    else self["text"][-1]
                )
                target_spaces = False
                if character in self["config"].space_characters:
                    target_spaces = True
                distance_left = entry_line_get_action_distance(
                    self, -1, True, target_spaces
                )
                distance_right = entry_line_get_action_distance(
                    self, 1, True, target_spaces
                )
                self["selection_start"] = self["cursor"] + distance_left
                self["cursor"] = self["cursor"] + distance_right
                entry_line_redundant_selection(self)
    else:
        self["last_mouse_pos"] = None
        self["first_mouse_cursor"] = None

    if self["selection_start"] is not None:
        start, end = entry_line_get_selection_cursors(self)
        text_before_start = self["text"][:start]
        text_selected = self["text"][start:end]
        size_before_start = font.size(text_before_start)[0]
        size_selected = font.size(text_selected)[0]
        start_left = padding[L] + size_before_start + align_offset

        context._component(
            Component.RECT,
            None,
            self["style"].selection_style,
            {
                "padding": Directions(0, padding[T], 0, padding[B]),
                "aspect_ratio": ((size_selected / height), Axis.Y, False),
                "anchor": Anchor.MIDLEFT,
                "offset": (start_left + self["offset"], 0),
            },
        )

    context._component(
        Component.TEXT,
        display_text,
        None,
        {
            "color": display_color,
            "size": "100%",
            "align": FontAlign.LEFT,
            "anchor": Anchor.MIDLEFT,
            "wrap": False,
            "offset": (self["offset"] + align_offset, 0),
        },
    )

    if self["focused"] and self["display_cursor"] and self["selection_start"] is None:
        context._component(
            Component.RECT,
            None,
            self["style"].cursor_style,
            {
                "padding": Directions(0, padding[T], 0, padding[B]),
                "aspect_ratio": ((cursor_width / height), Axis.Y, False),
                "anchor": Anchor.MIDLEFT,
                "offset": (cursor_left + self["offset"], 0),
            },
        )

    if pygame.time.get_ticks() - self["blink_time"] >= self["style"].blink_interval_ms:
        self["display_cursor"] = not self["display_cursor"]
        self["blink_time"] = pygame.time.get_ticks()

    result = EntryLineState(self)
    return result


Context._widget_event_handler["entry_line"] = entry_line_event
