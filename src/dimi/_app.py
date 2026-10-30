import dataclasses
import enum
import os
import tomllib
import typing

import pygame

from dimi._dimi import begin, element, image, push_id, rect, text, using, when
from dimi._error import IllegalOperation
from dimi._icon import PackedIcon, svg
from dimi._interaction import Interaction
from dimi._primitives import (
    Absolute,
    Align,
    Anchor,
    Axis,
    Directions,
    Fill,
    Font,
    FontAlign,
)
from dimi._style import ImageStyle, RectStyle, Style, TextStyle

if typing.TYPE_CHECKING:
    from dimi._context import Context


@dataclasses.dataclass(slots=True, frozen=True)
class AppStyle:
    __module__ = "dimi.app"

    clear_color: pygame.typing.ColorLike | None = "black"
    target_framerate: float = 144
    using_style: Style | None = None
    tick_busy_loop: bool = False
    dt_clamp: tuple[float, float] | None = None


class AppStyleOverrides(typing.TypedDict, total=False):
    __module__ = "dimi.typehinting"

    clear_color: pygame.typing.ColorLike | None
    target_framerate: float
    using_style: Style | None
    tick_busy_loop: bool
    dt_clamp: tuple[float, float] | None


@dataclasses.dataclass(slots=True, frozen=True)
class IconLayout:
    __module__ = "dimi.app"

    top_padding: int = 4
    bottom_padding: int = 4
    left_margin: int = 4
    right_margin: int = 4


@dataclasses.dataclass(slots=True, frozen=True)
class TitlebarButtonStyle:
    __module__ = "dimi.app"

    icon: PackedIcon
    icon_size: int = 20
    bg_style: RectStyle | None = None
    bg_hovered_style: RectStyle | None = None
    bg_held_style: RectStyle | None = None
    icon_style: ImageStyle | None = None
    icon_hovered_style: ImageStyle | None = None
    icon_held_style: ImageStyle | None = None


@dataclasses.dataclass(slots=True, frozen=True)
class TitlebarButtonStyles:
    __module__ = "dimi.app"

    minimize: TitlebarButtonStyle
    maximize: TitlebarButtonStyle
    restore: TitlebarButtonStyle
    close: TitlebarButtonStyle


MINIMIZE_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24">
    <path d="M0 0h24v24H0z" fill="none" />
    <path fill="#FFFFFF" d="M6.521 13.096q-.466 0-.78-.316T5.425 12t.316-.78T6.521 10.904h10.958q.466 0 .781.316T18.575 12t-.316.781T17.479 13.096z" />
</svg>
"""
MAXIMIZE_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24">
    <path d="M0 0h24v24H0z" fill="none" />
    <path fill="#FFFFFF" d="M6.886 18.575q-.603 0-1.032-.429T5.425 17.114V6.886q0-.603.43-1.032T6.886 5.425h10.228q.603 0 1.032.43T18.575 6.886v10.228q0 .603-.429 1.032T17.114 18.575zm0-1.461h10.228V6.886H6.886zm0 0V6.886z" />
</svg>
"""
RESTORE_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 16 16">
    <path d="M0 0h16v16H0z" fill="none" />
    <path fill="#FFFFFF" d="M5.085 4A1.5 1.5 0 0 1 6.5 3H10a3 3 0 0 1 3 3v3.5a1.5 1.5 0 0 1-1 1.415V6a2 2 0 0 0-2-2zM4.5 5h5A1.5 1.5 0 0 1 11 6.5v5A1.5 1.5 0 0 1 9.5 13h-5A1.5 1.5 0 0 1 3 11.5v-5A1.5 1.5 0 0 1 4.5 5m0 1a.5.5 0 0 0-.5.5v5a.5.5 0 0 0 .5.5h5a.5.5 0 0 0 .5-.5v-5a.5.5 0 0 0-.5-.5z" />
</svg>
"""
CLOSE_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" width="1em" height="1em" viewBox="0 0 24 24">
    <path d="M0 0h24v24H0z" fill="none" />
    <path fill="#FFFFFF" d="m12 13.4l-4.9 4.9q-.275.275-.7.275t-.7-.275t-.275-.7t.275-.7l4.9-4.9l-4.9-4.9q-.275-.275-.275-.7t.275-.7t.7-.275t.7.275l4.9 4.9l4.9-4.9q.275-.275.7-.275t.7.275t.275.7t-.275.7L13.4 12l4.9 4.9q.275.275.275.7t-.275.7t-.7.275t-.7-.275z" />
</svg>
"""


@dataclasses.dataclass(slots=True, frozen=True)
class EmulatedAppStyle:
    __module__ = "dimi.app"

    target_framerate: float = 144
    using_style: Style | None = Style(padding=1, spacing=1)
    maximized_using_style: Style | None = Style(padding=0, spacing=0)
    tick_busy_loop: bool = False
    dt_clamp: tuple[float, float] | None = None

    clear_color: pygame.typing.ColorLike | None = "#383838"
    unfocused_clear_color: pygame.typing.ColorLike | None = "#303030"

    client_area_style: Style | None = None
    client_area_clear_color: pygame.typing.ColorLike | None = "black"

    titlebar_color: pygame.typing.ColorLike | None = "#242424"
    unfocused_titlebar_color: pygame.typing.ColorLike | None = "#202020"

    icon: PackedIcon | None = None
    icon_style: ImageStyle | None = ImageStyle()
    icon_layout: IconLayout = IconLayout()
    maximized_icon_layout: IconLayout = IconLayout(3, 3, 3, 3)

    title_style: TextStyle = TextStyle(
        Font("Segoe UI", True),
        17,
        color="white",
        anchor=Anchor.MIDLEFT,
        align=FontAlign.LEFT,
        wrap=False,
    )
    unfocused_title_style: TextStyle = TextStyle(
        Font("Segoe UI", True),
        17,
        color="#7B7B7B",
        anchor=Anchor.MIDLEFT,
        align=FontAlign.LEFT,
        wrap=False,
    )

    button_styles: TitlebarButtonStyles = TitlebarButtonStyles(
        TitlebarButtonStyle(
            svg.pack(MINIMIZE_SVG, size=128),
            bg_hovered_style=RectStyle(color="#333333"),
            bg_held_style=RectStyle(color="#2B2B2B"),
        ),
        TitlebarButtonStyle(
            svg.pack(MAXIMIZE_SVG, size=128),
            bg_hovered_style=RectStyle(color="#333333"),
            bg_held_style=RectStyle(color="#2B2B2B"),
        ),
        TitlebarButtonStyle(
            svg.pack(RESTORE_SVG, size=128),
            bg_hovered_style=RectStyle(color="#333333"),
            bg_held_style=RectStyle(color="#2B2B2B"),
        ),
        TitlebarButtonStyle(
            svg.pack(CLOSE_SVG, size=128),
            bg_hovered_style=RectStyle(color="#C42B1C"),
            bg_held_style=RectStyle(color="#B42516"),
        ),
    )
    unfocused_button_styles: TitlebarButtonStyles = TitlebarButtonStyles(
        TitlebarButtonStyle(
            svg.pack(MINIMIZE_SVG, size=128),
            bg_hovered_style=RectStyle(color="#333333"),
            bg_held_style=RectStyle(color="#2B2B2B"),
            icon_style=ImageStyle(alpha_modifier=123),
        ),
        TitlebarButtonStyle(
            svg.pack(MAXIMIZE_SVG, size=128),
            bg_hovered_style=RectStyle(color="#333333"),
            bg_held_style=RectStyle(color="#2B2B2B"),
            icon_style=ImageStyle(alpha_modifier=123),
        ),
        TitlebarButtonStyle(
            svg.pack(RESTORE_SVG, size=128),
            bg_hovered_style=RectStyle(color="#333333"),
            bg_held_style=RectStyle(color="#2B2B2B"),
            icon_style=ImageStyle(alpha_modifier=123),
        ),
        TitlebarButtonStyle(
            svg.pack(CLOSE_SVG, size=128),
            bg_hovered_style=RectStyle(color="#C42B1C"),
            bg_held_style=RectStyle(color="#B42516"),
            icon_style=ImageStyle(alpha_modifier=123),
        ),
    )


class EmulatedAppStyleOverrides(typing.TypedDict, total=False):
    __module__ = "dimi.typehinting"

    target_framerate: float
    using_style: Style | None
    maximized_using_style: Style | None
    tick_busy_loop: bool
    dt_clamp: tuple[float, float] | None

    clear_color: pygame.typing.ColorLike | None
    unfocused_clear_color: pygame.typing.ColorLike | None

    client_area_style: Style | None
    client_area_clear_color: pygame.typing.ColorLike | None

    titlebar_color: pygame.typing.ColorLike | None
    unfocused_titlebar_color: pygame.typing.ColorLike | None

    icon: PackedIcon | None
    icon_style: ImageStyle | None
    icon_layout: IconLayout
    maximized_icon_layout: IconLayout

    title_style: TextStyle
    unfocused_title_style: TextStyle

    button_styles: TitlebarButtonStyles
    unfocused_button_styles: TitlebarButtonStyles


@dataclasses.dataclass(slots=True, frozen=True)
class TitlebarButtonLayout:
    __module__ = "dimi.app"

    top_padding: int = 0
    bottom_padding: int = 0
    size_ratio: float = 1.2
    left_margin: int = 0
    right_margin: int = 0


@dataclasses.dataclass(slots=True, frozen=True)
class TitlebarButtonLayouts:
    __module__ = "dimi.app"

    minimize: TitlebarButtonLayout = TitlebarButtonLayout()
    maximize: TitlebarButtonLayout = TitlebarButtonLayout()
    close: TitlebarButtonLayout = TitlebarButtonLayout()


class HitTestResult(enum.Enum):
    DEFAULT = enum.auto()
    NORMAL = enum.auto()
    DRAG = enum.auto()
    RESIZE_TOPLEFT = enum.auto()
    RESIZE_TOP = enum.auto()
    RESIZE_TOPRIGHT = enum.auto()
    RESIZE_RIGHT = enum.auto()
    RESIZE_BOTTOMRIGHT = enum.auto()
    RESIZE_BOTTOM = enum.auto()
    RESIZE_BOTTOMLEFT = enum.auto()
    RESIZE_LEFT = enum.auto()
    MINIMIZE_BUTTON = enum.auto()
    MAXIMIZE_BUTTON = enum.auto()
    CLOSE_BUTTON = enum.auto()


@dataclasses.dataclass(slots=True, frozen=True)
class Cursors:
    __module__ = "dimi.app"

    normal = pygame.SYSTEM_CURSOR_ARROW
    drag = pygame.SYSTEM_CURSOR_ARROW
    resize_topleft = pygame.SYSTEM_CURSOR_SIZENWSE
    resize_top = pygame.SYSTEM_CURSOR_SIZENS
    resize_topright = pygame.SYSTEM_CURSOR_SIZENESW
    resize_right = pygame.SYSTEM_CURSOR_SIZEWE
    resize_bottomright = pygame.SYSTEM_CURSOR_SIZENWSE
    resize_bottom = pygame.SYSTEM_CURSOR_SIZENS
    resize_bottomleft = pygame.SYSTEM_CURSOR_SIZENESW
    resize_left = pygame.SYSTEM_CURSOR_SIZEWE
    buttons = pygame.SYSTEM_CURSOR_HAND


# todo: snapping (including top)
@dataclasses.dataclass(slots=True, frozen=True)
class EmulatedWindowControlsStyle:
    __module__ = "dimi.app"

    display_usable_bounds: pygame.Rect | None = None  # obsolete in pygame-ce 3

    titlebar_height: int = 28
    maximized_titlebar_height: int = 24

    resize_borders_size: int = 6
    resize_corners_size: int = 10

    button_layouts: TitlebarButtonLayouts = TitlebarButtonLayouts()
    maximized_button_layouts: TitlebarButtonLayouts = TitlebarButtonLayouts(
        TitlebarButtonLayout(size_ratio=1.5),
        TitlebarButtonLayout(size_ratio=1.5),
        TitlebarButtonLayout(size_ratio=1.5),
    )
    cursors: Cursors = Cursors()

    close_callback: typing.Callable[[], None] | None = None
    custom_hit_testing: (
        typing.Callable[[EmulatedWindowControls, tuple[int, int]], HitTestResult] | None
    ) = None

    state_persistence_folder: str | None = None
    state_persistence_id: str | None = None

    fullscreen_key: int | None = pygame.K_F11
    fullscreen_modifier: int | None = None

    double_click_interval_ms: int = 300
    drag_tolerance: int = 10


class EmulatedWindowControlsStyleOverrides(typing.TypedDict, total=False):
    __module__ = "dimi.typehinting"

    display_usable_bounds: pygame.Rect | None  # obsolete in pygame-ce 3

    titlebar_height: int
    maximized_titlebar_height: int

    resize_borders_size: int
    resize_corners_size: int

    button_layouts: TitlebarButtonLayouts
    maximized_button_layouts: TitlebarButtonLayouts

    cursors: Cursors

    close_callback: typing.Callable[[], None] | None
    custom_hit_testing: (
        typing.Callable[[EmulatedWindowControls, tuple[int, int]], HitTestResult] | None
    )

    state_persistence_folder: str | None
    state_persistence_id: str | None

    fullscreen_key: int | None
    fullscreen_modifier: int | None

    double_click_interval_ms: int
    drag_tolerance: int


@dataclasses.dataclass(slots=True, frozen=True)
class CachedHitboxes:
    __module__ = "dimi.typehinting"

    titlebar_hitbox: pygame.Rect | None
    resize_hitboxes: dict[HitTestResult, pygame.Rect] | None
    button_hitboxes: tuple[pygame.Rect, pygame.Rect, pygame.Rect] | None


class EmulatedWindowControls:
    __module__ = "dimi.app"

    def __init__(
        self,
        window: pygame.Window,
        style: EmulatedWindowControlsStyle | None = None,
        **style_overrides: typing.Unpack[EmulatedWindowControlsStyleOverrides],
    ):
        self.window = window
        if style is None:
            style = EmulatedWindowControlsStyle()
        style = dataclasses.replace(style, **style_overrides)
        self.style: EmulatedWindowControlsStyle = style
        usable = self.style.display_usable_bounds  # obsolete in pygame-ce 3
        if usable is None:
            usable = pygame.Rect((0, 0), pygame.display.get_desktop_sizes()[0])

        self._usable_bounds = usable  # make dynamic in pygame-ce 3
        self._display_size = pygame.display.get_desktop_sizes()[
            0
        ]  # make dynamic in pygame-ce 3
        self._minimized: bool = False
        self._maximized: bool = False
        self._fullscreen: bool = False
        self._before_maximize_state: tuple[tuple[int, int], tuple[int, int]] | None = (
            None
        )
        self._before_fullscreen_state: (
            tuple[tuple[int, int], tuple[int, int], bool] | None
        ) = None
        self._hidden: bool = False
        self._titlebar_hitbox: dict[tuple[int, int], pygame.Rect] = {}
        self._buttons_hitbox: dict[
            tuple[int, int, TitlebarButtonLayouts],
            tuple[pygame.Rect, pygame.Rect, pygame.Rect],
        ] = {}
        self._resize_hitbox: dict[
            tuple[int, int], dict[HitTestResult, pygame.Rect]
        ] = {}
        self._mouse_pressed: tuple[bool, bool, bool] = (False,) * 3
        self._active_action: HitTestResult = HitTestResult.NORMAL
        self._action_start_mouse: tuple[int, int] = (0, 0)
        self._action_start_size: tuple[int, int] = (0, 0)
        self._action_start_pos: tuple[int, int] = (0, 0)
        self._action_unlocked: bool = False
        self._click_time: int | None = None
        self._hover_action_just_pressed: HitTestResult = HitTestResult.NORMAL

        if self.style.state_persistence_folder is not None:
            file_path = os.path.join(
                self.style.state_persistence_folder,
                f"{self.style.state_persistence_id}.toml",
            )
            if os.path.exists(file_path):
                with open(file_path, "r") as state_file:
                    state = tomllib.loads(state_file.read())
                    size = state.get("size", None)
                    position = state.get("position", None)
                    if size is not None:
                        self.window.size = size
                    if position is not None:
                        self.window.position = position
                    if state.get("maximized", False):
                        self._maximize()

    def save_persistent_state(self):
        if self.style.state_persistence_folder is None:
            return
        file_path = os.path.join(
            self.style.state_persistence_folder,
            f"{self.style.state_persistence_id}.toml",
        )
        with open(file_path, "w") as file:
            if self._maximized:
                size, position = self._before_maximize_state
            else:
                size = self.window.size
                position = self.window.position
            file.write(
                f"size = [{size[0]}, {size[1]}]\nposition = [{position[0]}, {position[1]}]\nmaximized = {str(self._maximized).lower()}"
            )

    def process_event(self, event: pygame.Event):
        if event.type == pygame.WINDOWMINIMIZED and event.window == self.window:
            self._minimized = True
        elif event.type == pygame.WINDOWMAXIMIZED and event.window == self.window:
            raise IllegalOperation(
                "When using EmulatedWindowControls, maximization is emulated. It is therefore forbidden to use Window.maximize directly to avoid undefined behavior"
            )
        elif event.type == pygame.WINDOWRESTORED and event.window == self.window:
            self._minimized = False
        elif event.type == pygame.WINDOWSHOWN and event.window == self.window:
            self._hidden = False
        elif event.type == pygame.WINDOWHIDDEN and event.window == self.window:
            self._hidden = True
        elif (
            event.type == pygame.KEYDOWN
            and event.window == self.window
            and event.key == self.style.fullscreen_key
            and (
                self.style.fullscreen_modifier is None
                or event.mod & self.style.fullscreen_modifier
            )
        ):
            self.set_fullscreen(not self._fullscreen)

    def update(self):
        if self._minimized:
            return HitTestResult.NORMAL

        mouse = pygame.mouse.get_pos(True)
        position = self.window.position
        rel_mouse = (mouse[0] - position[0], mouse[1] - position[1])
        just_pressed = just_released = False
        mouse_pressed = pygame.mouse.get_pressed(desktop=True)
        if mouse_pressed[0] != self._mouse_pressed[0]:
            if mouse_pressed[0]:
                just_pressed = True
            else:
                just_released = True
        self._mouse_pressed = mouse_pressed

        if just_pressed:
            self._update_just_pressed(mouse, rel_mouse)
        if just_released:
            self._update_just_released(rel_mouse)
        if self._active_action != HitTestResult.NORMAL:
            self._update_action(mouse)
            return self._active_action
        else:
            if not self.window.focused:
                return HitTestResult.NORMAL
            return self._hit_test(rel_mouse)

    def apply_cursor(self, action: HitTestResult, cursor=None):
        to_apply = None
        cursors = self.style.cursors
        if action == HitTestResult.NORMAL:
            if cursor is not None:
                to_apply = cursor
            else:
                to_apply = cursors.normal
        elif action == HitTestResult.DEFAULT:
            to_apply = cursor
        else:
            to_apply = {
                HitTestResult.DRAG: cursors.drag,
                HitTestResult.RESIZE_TOPLEFT: cursors.resize_topleft,
                HitTestResult.RESIZE_TOP: cursors.resize_top,
                HitTestResult.RESIZE_TOPRIGHT: cursors.resize_topright,
                HitTestResult.RESIZE_RIGHT: cursors.resize_right,
                HitTestResult.RESIZE_BOTTOMRIGHT: cursors.resize_bottomright,
                HitTestResult.RESIZE_BOTTOM: cursors.resize_bottom,
                HitTestResult.RESIZE_BOTTOMLEFT: cursors.resize_bottomleft,
                HitTestResult.RESIZE_LEFT: cursors.resize_left,
                HitTestResult.MINIMIZE_BUTTON: cursors.buttons,
                HitTestResult.MAXIMIZE_BUTTON: cursors.buttons,
                HitTestResult.CLOSE_BUTTON: cursors.buttons,
            }[action]
        if to_apply is not None:
            pygame.mouse.set_cursor(to_apply)

    def _update_just_pressed(self, mouse, rel_mouse):
        if not self.window.focused:
            return

        if self._click_time is not None and self.window.resizable:
            if (
                pygame.time.get_ticks() - self._click_time
                < self.style.double_click_interval_ms
            ):
                if self._fullscreen:
                    self._remove_fullscreen()
                elif self._maximized:
                    self._restore()
                else:
                    self._maximize()
            self._click_time = None

        hit_test = self._hit_test(rel_mouse)
        self._hover_action_just_pressed = hit_test
        if hit_test not in (
            HitTestResult.NORMAL,
            HitTestResult.MINIMIZE_BUTTON,
            HitTestResult.MAXIMIZE_BUTTON,
            HitTestResult.CLOSE_BUTTON,
        ) and (self.window.resizable or hit_test == HitTestResult.DRAG):
            self._active_action = hit_test
            self._action_start_size = self.window.size
            self._action_start_pos = self.window.position
            self._action_start_mouse = mouse
            self._action_unlocked = False

    def _update_just_released(self, rel_mouse):
        if (
            self._active_action == HitTestResult.DRAG
            and not self._action_unlocked
            and self._click_time is None
        ):
            self._click_time = pygame.time.get_ticks()

        if self._active_action == HitTestResult.NORMAL and self.window.focused:
            hovered = self._hit_test(rel_mouse)
            if (
                hovered == HitTestResult.MINIMIZE_BUTTON
                and self._hover_action_just_pressed == HitTestResult.MINIMIZE_BUTTON
            ):
                self.window.minimize()
            elif (
                hovered == HitTestResult.MAXIMIZE_BUTTON
                and self._hover_action_just_pressed == HitTestResult.MAXIMIZE_BUTTON
                and self.window.resizable
            ):
                if self.maximized:
                    self._restore()
                else:
                    self._maximize()
            elif (
                hovered == HitTestResult.CLOSE_BUTTON
                and self._hover_action_just_pressed == HitTestResult.CLOSE_BUTTON
            ):
                post_event = True
                if (
                    self.style.close_callback is not None
                    and self.style.close_callback() is False
                ):
                    post_event = False
                if post_event:
                    pygame.event.post(
                        pygame.Event(pygame.WINDOWCLOSE, {"window": self.window})
                    )

        self._active_action = HitTestResult.NORMAL
        self._action_unlocked = False

    def _update_action(self, mouse):
        if not self.window.focused:
            return

        if self._active_action != HitTestResult.DRAG and self.maximized:
            return

        dx, dy = (
            mouse[0] - self._action_start_mouse[0],
            mouse[1] - self._action_start_mouse[1],
        )

        if self._active_action == HitTestResult.DRAG:
            if not self._action_unlocked:
                if (
                    abs(dx) >= self.style.drag_tolerance
                    or abs(dy) >= self.style.drag_tolerance
                ):
                    self._action_unlocked = True
                    if self._fullscreen:
                        self._remove_fullscreen()
                        if not self._maximized:
                            size = self.window.size
                            self.window.position = (
                                mouse[0] - size[0] / 2,
                                mouse[1] - self.style.titlebar_height / 2,
                            )
                            self._action_start_pos = self.window.position
                            self._action_start_size = size
                    if self._maximized:
                        self._restore()
                        size = self.window.size
                        self.window.position = (
                            mouse[0] - size[0] / 2,
                            mouse[1] - self.style.titlebar_height / 2,
                        )
                        self._action_start_pos = self.window.position
                        self._action_start_size = size
                else:
                    return

            self.window.position = (
                self._action_start_pos[0] + dx,
                self._action_start_pos[1] + dy,
            )
        else:
            w_min = 1
            h_min = 1

            # todo make the magic addition +2 more explicit in the style
            h_min = max(h_min, self.style.titlebar_height + 2)
            buttons_w = 0
            for button, mult in zip(
                (
                    self.style.button_layouts.minimize,
                    self.style.button_layouts.maximize,
                    self.style.button_layouts.close,
                ),
                (1, 1, 2),
            ):
                button_w = (
                    self.style.titlebar_height
                    - button.top_padding
                    - button.bottom_padding
                ) * button.size_ratio
                contribute = button.left_margin + button.right_margin + button_w
                buttons_w += contribute * mult
            w_min = max(w_min, buttons_w)

            if self._active_action == HitTestResult.RESIZE_RIGHT:
                if dx != 0:
                    width = self._action_start_size[0] + dx
                    self.window.size = (max(w_min, width), self._action_start_size[1])
            elif self._active_action == HitTestResult.RESIZE_BOTTOM:
                if dy != 0:
                    height = self._action_start_size[1] + dy
                    self.window.size = (self._action_start_size[0], max(h_min, height))
            elif self._active_action == HitTestResult.RESIZE_BOTTOMRIGHT:
                if dx != 0 or dy != 0:
                    self.window.size = (
                        max(w_min, self._action_start_size[0] + dx),
                        max(h_min, self._action_start_size[1] + dy),
                    )
            elif self._active_action == HitTestResult.RESIZE_LEFT:
                if dx != 0:
                    prev = self.window.size[0]
                    width = self._action_start_size[0] - dx
                    self.window.size = (max(w_min, width), self._action_start_size[1])
                    size = self.window.size
                    if size[0] != prev:
                        x = min(
                            self._action_start_pos[0] + dx,
                            (
                                self._action_start_pos[0]
                                + self._action_start_size[0]
                                - w_min
                            ),
                        )
                        self.window.position = (x, self._action_start_pos[1])

            elif self._active_action == HitTestResult.RESIZE_TOP:
                if dy != 0:
                    prev = self.window.size[1]
                    height = self._action_start_size[1] - dy
                    self.window.size = (self._action_start_size[0], max(h_min, height))
                    if self.window.size[1] != prev:
                        y = min(
                            self._action_start_pos[1] + dy,
                            (
                                self._action_start_pos[1]
                                + self._action_start_size[1]
                                - h_min
                            ),
                        )
                        self.window.position = (self._action_start_pos[0], y)
            elif self._active_action == HitTestResult.RESIZE_TOPRIGHT:
                if dx != 0 or dy != 0:
                    prev = self.window.size[1]
                    self.window.size = (
                        max(w_min, self._action_start_size[0] + dx),
                        max(h_min, self._action_start_size[1] - dy),
                    )
                    if self.window.size[1] != prev:
                        y = min(
                            self._action_start_pos[1] + dy,
                            (
                                self._action_start_pos[1]
                                + self._action_start_size[1]
                                - h_min
                            ),
                        )
                        self.window.position = (self._action_start_pos[0], y)
            elif self._active_action == HitTestResult.RESIZE_BOTTOMLEFT:
                if dx != 0 or dy != 0:
                    prev = self.window.size[0]
                    self.window.size = (
                        max(w_min, self._action_start_size[0] - dx),
                        max(h_min, self._action_start_size[1] + dy),
                    )
                    if self.window.size[0] != prev:
                        x = min(
                            self._action_start_pos[0] + dx,
                            (
                                self._action_start_pos[0]
                                + self._action_start_size[0]
                                - w_min
                            ),
                        )
                        self.window.position = (x, self._action_start_pos[1])
            elif self._active_action == HitTestResult.RESIZE_TOPLEFT:  # noqa: SIM102
                if dx != 0 or dy != 0:
                    prev = self.window.size
                    self.window.size = (
                        max(w_min, self._action_start_size[0] - dx),
                        max(h_min, self._action_start_size[1] - dy),
                    )
                    new = self.window.size
                    if new[0] != prev[0] or new[1] != prev[1]:
                        self.window.position = (
                            min(
                                self._action_start_pos[0] + dx,
                                (
                                    self._action_start_pos[0]
                                    + self._action_start_size[0]
                                    - w_min
                                ),
                            ),
                            min(
                                self._action_start_pos[1] + dy,
                                (
                                    self._action_start_pos[1]
                                    + self._action_start_size[1]
                                    - h_min
                                ),
                            ),
                        )

    def _hit_test(self, point: tuple[int, int]):
        if self.style.custom_hit_testing is not None:
            hit_test = self.style.custom_hit_testing(self, point)
            if hit_test != HitTestResult.DEFAULT:
                return hit_test
        return self._default_hit_test(point)

    def _default_hit_test(self, point: tuple[int, int]):
        if self._fullscreen:
            return HitTestResult.NORMAL

        size = self.window.size
        hit_result = HitTestResult.NORMAL
        titlebar = self.style.titlebar_height
        layouts = self.style.button_layouts
        if self._maximized:
            titlebar = self.style.maximized_titlebar_height
            layouts = self.style.maximized_button_layouts

        if titlebar > 0:
            titlebar_key = (size[0], titlebar)
            if titlebar_key not in self._titlebar_hitbox:
                self._titlebar_hitbox.clear()
                self._titlebar_hitbox[titlebar_key] = pygame.Rect(
                    0, 0, size[0], titlebar
                )
            if self._titlebar_hitbox[titlebar_key].collidepoint(point):
                hit_result = HitTestResult.DRAG
            buttons_key = (size[0], titlebar, layouts)
            if buttons_key not in self._buttons_hitbox:
                self._buttons_hitbox.clear()
                hitboxes = []
                right = size[0]
                for layout in (layouts.close, layouts.maximize, layouts.minimize):
                    height = titlebar - layout.top_padding - layout.bottom_padding
                    width = height * layout.size_ratio
                    right -= width + layout.right_margin
                    hitboxes.append(
                        pygame.Rect(right, layout.top_padding, width, height)
                    )
                    right -= layout.left_margin
                self._buttons_hitbox[buttons_key] = tuple(hitboxes)
            close_hitbox, maximize_hitbox, minimize_hitbox = self._buttons_hitbox[
                buttons_key
            ]
            if minimize_hitbox.collidepoint(point):
                hit_result = HitTestResult.MINIMIZE_BUTTON
            if maximize_hitbox.collidepoint(point):
                hit_result = HitTestResult.MAXIMIZE_BUTTON
            if close_hitbox.collidepoint(point):
                hit_result = HitTestResult.CLOSE_BUTTON
        if not self.window.resizable or self._maximized:
            return hit_result
        if size not in self._resize_hitbox:
            self._resize_hitbox.clear()
            b, c = self.style.resize_borders_size, self.style.resize_corners_size
            self._resize_hitbox[size] = {
                HitTestResult.RESIZE_TOPLEFT: pygame.Rect(0, 0, c, c),
                HitTestResult.RESIZE_TOPRIGHT: pygame.Rect(size[0] - c, 0, c, c),
                HitTestResult.RESIZE_BOTTOMRIGHT: pygame.Rect(
                    size[0] - c, size[1] - c, c, c
                ),
                HitTestResult.RESIZE_BOTTOMLEFT: pygame.Rect(0, size[1] - c, c, c),
                HitTestResult.RESIZE_LEFT: pygame.Rect(0, c, b, size[1] - c * 2),
                HitTestResult.RESIZE_TOP: pygame.Rect(c, 0, size[0] - c * 2, b),
                HitTestResult.RESIZE_RIGHT: pygame.Rect(
                    size[0] - b, c, b, size[1] - c * 2
                ),
                HitTestResult.RESIZE_BOTTOM: pygame.Rect(
                    c, size[1] - b, size[0] - c * 2, b
                ),
            }
        for resize, hitbox in self._resize_hitbox[size].items():
            if hitbox.collidepoint(point):
                hit_result = resize
                break
        return hit_result

    def _maximize(self):
        if self._maximized:
            return
        if self._minimized:
            self.window.restore()
        self._before_maximize_state = self.window.size, self.window.position
        # make dynamic with pygame-ce 3 Display
        self.window.position = self._usable_bounds.topleft
        self.window.size = self._usable_bounds.size
        self._maximized = True

    def _restore(self):
        if not self._maximized:
            return
        self._maximized = False
        if self._before_maximize_state is None:
            return
        self.window.size, self.window.position = self._before_maximize_state
        self._before_maximize_state = None

    def _set_fullscreen(self):
        if self._fullscreen:
            return
        if self._minimized:
            self.window.restore()
        self._before_fullscreen_state = (
            self.window.size,
            self.window.position,
            self._maximized,
        )
        # make dynamic with pygame-ce 3 Display
        self.window.position = (0, 0)
        self.window.size = self._display_size
        self._fullscreen = True
        self._maximized = False

    def _remove_fullscreen(self):
        if not self._fullscreen:
            return
        self._fullscreen = False
        if self._before_fullscreen_state is None:
            return
        self.window.size, self.window.position, self._maximized = (
            self._before_fullscreen_state
        )
        self._before_fullscreen_state = None

    def maximize(self):
        self._maximize()

    def restore(self):
        if self._minimized:
            self.window.restore()
        elif self._fullscreen:
            self._remove_fullscreen()
        elif self._maximized:
            self._restore()

    def set_fullscreen(self, active: bool):
        if active:
            self._set_fullscreen()
        else:
            self._remove_fullscreen()

    @property
    def minimized(self) -> bool:
        return self._minimized

    @property
    def maximized(self) -> bool:
        return self._maximized

    @property
    def fullscreen(self) -> bool:
        return self._fullscreen

    @property
    def hidden(self) -> bool:
        return self._hidden

    @property
    def titlebar_height(self) -> int:
        if self._fullscreen:
            return 0
        if self._maximized:
            return self.style.maximized_titlebar_height
        return self.style.titlebar_height

    @property
    def cached_hitboxes(self) -> CachedHitboxes:
        if len(self._titlebar_hitbox) > 0:
            titlebar_hitbox = next(iter(self._titlebar_hitbox.values()))
        else:
            titlebar_hitbox = None
        if len(self._resize_hitbox) > 0:
            resize_hitboxes = next(iter(self._resize_hitbox.values()))
        else:
            resize_hitboxes = None
        if len(self._buttons_hitbox) > 0:
            button_hitboxes = tuple(reversed(next(iter(self._buttons_hitbox.values()))))
        else:
            button_hitboxes = None
        return CachedHitboxes(titlebar_hitbox, resize_hitboxes, button_hitboxes)


class EmulatedApp:
    __module__ = "dimi.app"

    def __init__(
        self,
        window: pygame.Window,
        context: Context,
        controls: EmulatedWindowControls,
        style: EmulatedAppStyle | None = None,
        **style_overrides: typing.Unpack[EmulatedAppStyleOverrides],
    ):
        self.window: pygame.Window = window
        self.context: Context = context
        self.controls: EmulatedWindowControls = controls

        if style is None:
            style = EmulatedAppStyle()
        style = dataclasses.replace(style, **style_overrides)
        self.style: EmulatedAppStyle = style
        self.clock: pygame.Clock = pygame.Clock()
        self.dt_s: float = 0

        if not self.window.borderless:
            self.window.borderless = True

    def on_event(self, event: pygame.Event): ...

    def on_ui(self, main: Interaction): ...

    def on_close(self) -> bool | None:
        return True

    def close(self):
        self.controls.save_persistent_state()
        raise SystemExit

    def ui_titlebar(self, titlebar: Interaction):
        unfocused = not self.window.focused
        maximized = self.controls.maximized
        titlebar_height = self.controls.titlebar_height

        titlebar_color = self.style.titlebar_color
        if unfocused:
            titlebar_color = self.style.unfocused_titlebar_color
        if titlebar_color is not None:
            rect(color=titlebar_color)

        if self.style.icon is not None:
            layout = self.style.icon_layout
            if maximized:
                layout = self.style.maximized_icon_layout
            size = titlebar_height - layout.top_padding - layout.bottom_padding
            with element(
                width=size,
                height=size,
                margin=Directions(
                    layout.left_margin,
                    layout.top_padding,
                    layout.right_margin,
                    layout.bottom_padding,
                ),
            ):
                image(self.style.icon.get(), self.style.icon_style)

        title = self.window.title
        if title != "":
            title_style = self.style.title_style
            if unfocused:
                title_style = self.style.unfocused_title_style
            with element(width=Fill(), height=Fill()):
                text(title, title_style)

        if len(self.controls._buttons_hitbox) <= 0:
            return
        styles = self.style.button_styles
        if unfocused:
            styles = self.style.unfocused_button_styles
        maximize_style = styles.maximize
        layouts = self.controls.style.button_layouts
        if maximized:
            maximize_style = styles.restore
            layouts = self.controls.style.maximized_button_layouts
        for layout, style in zip(
            (layouts.minimize, layouts.maximize, layouts.close),
            (styles.minimize, maximize_style, styles.close),
        ):
            height = titlebar_height - layout.top_padding - layout.bottom_padding
            with begin(
                height=height,
                width=height * layout.size_ratio,
                align_children=Align.CENTER,
                margin=Directions(
                    layout.left_margin,
                    layout.top_padding,
                    layout.right_margin,
                    layout.bottom_padding,
                ),
            ) as button_el:
                bg_style = when(
                    button_el,
                    style.bg_style,
                    style.bg_hovered_style,
                    style.bg_held_style,
                )
                icon_style = when(
                    button_el,
                    style.icon_style,
                    style.icon_hovered_style,
                    style.icon_held_style,
                )
                if bg_style is not None:
                    rect(bg_style)
                with element(
                    width=style.icon_size,
                    height=style.icon_size,
                    align_self=Align.CENTER,
                    blocking=False,
                ):
                    image(style.icon.get(), icon_style)

    def ui_using(self, clear_color: pygame.typing.ColorLike | None):
        if clear_color is not None:
            rect(color=clear_color)
        if self.controls.maximized or self.controls.fullscreen:
            return
        if len(self.controls._resize_hitbox) <= 0:
            return
        resize_hitbox = next(iter(self.controls._resize_hitbox.values()))
        for hitbox in resize_hitbox.values():
            element(
                width=hitbox.w, height=hitbox.h, position=Absolute(hitbox.y, hitbox.x)
            )

    def run(self):
        while True:
            for event in pygame.event.get():
                if (
                    event.type == pygame.QUIT
                    or (
                        event.type == pygame.WINDOWCLOSE and event.window == self.window
                    )
                ) and self.on_close() is not False:
                    self.close()
                self.context.process_event(event)
                self.controls.process_event(event)
                self.on_event(event)

            renderer = getattr(self.context.canvas, "renderer", None)
            unfocused = not self.window.focused

            clear_color = self.style.clear_color
            if unfocused:
                clear_color = self.style.unfocused_clear_color
            if clear_color is not None:
                if renderer is None:
                    self.window.get_surface().fill(clear_color)
                else:
                    renderer.draw_color = clear_color
                    renderer.clear()

            action: HitTestResult = self.controls.update()
            user_cursor = None

            using_style = self.style.using_style
            if self.controls.maximized or self.controls.fullscreen:
                using_style = self.style.maximized_using_style
            with using(self.context, using_style):
                self.ui_using(clear_color)
                titlebar_height = self.controls.titlebar_height
                if titlebar_height > 0:
                    with begin(
                        width=Fill(),
                        height=titlebar_height,
                        axis=Axis.X,
                        padding=0,
                        spacing=0,
                    ) as titlebar:
                        self.ui_titlebar(titlebar)
                with (
                    push_id(self),
                    begin(
                        self.style.client_area_style, width=Fill(), height=Fill()
                    ) as main,
                ):
                    if self.style.client_area_clear_color is not None:
                        rect(
                            color=self.style.client_area_clear_color,
                            padding=0,
                            border_width=0,
                            border_radius=0,
                            aspect_ratio=0,
                            z=float("-inf"),
                        )
                    user_cursor = self.on_ui(main)

            self.controls.apply_cursor(
                action, user_cursor
            )  # todo replace None with truth from UI after enstablished cursor system

            if renderer is None:
                self.window.flip()
            else:
                renderer.present()

            if self.style.tick_busy_loop:
                self.dt_s = (
                    self.clock.tick_busy_loop(self.style.target_framerate) / 1000.0
                )
            else:
                self.dt_s = self.clock.tick(self.style.target_framerate) / 1000.0
            if self.style.dt_clamp is not None:
                self.dt_s = pygame.math.clamp(self.dt_s, *self.style.dt_clamp)


class App:
    __module__ = "dimi.app"

    def __init__(
        self,
        window: pygame.Window,
        context: Context,
        style: AppStyle | None = None,
        **style_overrides: typing.Unpack[AppStyleOverrides],
    ):
        self.window: pygame.Window = window
        self.context: Context = context

        if style is None:
            style = AppStyle()
        style = dataclasses.replace(style, **style_overrides)
        self.style: AppStyle = style
        self.clock: pygame.Clock = pygame.Clock()
        self.dt_s: float = 0

    def on_event(self, event: pygame.Event): ...

    def on_ui(self): ...

    def on_close(self) -> bool | None:
        return True

    def close(self):
        raise SystemExit

    def run(self):
        while True:
            for event in pygame.event.get():
                if (
                    event.type == pygame.QUIT
                    or (
                        event.type == pygame.WINDOWCLOSE and event.window == self.window
                    )
                ) and self.on_close() is not False:
                    self.close()
                self.context.process_event(event)
                self.on_event(event)

            renderer = getattr(self.context.canvas, "renderer", None)
            if self.style.clear_color is not None:
                if renderer is None:
                    self.window.get_surface().fill(self.style.clear_color)
                else:
                    renderer.draw_color = self.style.clear_color
                    renderer.clear()

            with using(self.context, self.style.using_style):
                self.on_ui()

            if renderer is None:
                self.window.flip()
            else:
                renderer.present()

            if self.style.tick_busy_loop:
                self.dt_s = (
                    self.clock.tick_busy_loop(self.style.target_framerate) / 1000.0
                )
            else:
                self.dt_s = self.clock.tick(self.style.target_framerate) / 1000.0
            if self.style.dt_clamp is not None:
                self.dt_s = pygame.math.clamp(self.dt_s, *self.style.dt_clamp)
