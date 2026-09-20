import typing
import dataclasses

from dimi._interaction import Interaction, Button, ButtonStatus
from dimi._context import Context
from dimi._components import Component
from dimi._error import IllegalOperation
from dimi._style import (
    Style,
    StyleOverrides,
    RectStyle,
    RectStyleOverrides,
    EllipseStyle,
    EllipseStyleOverrides,
    TextStyle,
    TextStyleOverrides,
    ImageStyle,
    ImageStyleOverrides,
)


class using:
    __module__ = "dimi"

    _current_context: Context | None = None

    def __init__(self, context: Context, style: Style | None = None):
        if using._current_context is not None:
            raise IllegalOperation("Another context is already in use")
        self.context: Context = context
        using._current_context = context
        context._start(style)

    def __enter__(self) -> typing.Self:
        return self

    def __exit__(self, *args, **kwargs):
        using._current_context = None
        self.context._finish()


class push_style:
    __module__ = "dimi"

    def __init__(
        self, component: Component | None, **style: typing.Unpack[StyleOverrides]
    ):
        self._component: Component | None = component
        self._style = style

    @classmethod
    def rect(cls, **style: typing.Unpack[RectStyleOverrides]):
        return cls(Component.RECT, **style)

    @classmethod
    def ellipse(cls, **style: typing.Unpack[EllipseStyleOverrides]):
        return cls(Component.ELLIPSE, **style)

    @classmethod
    def text(cls, **style: typing.Unpack[TextStyleOverrides]):
        return cls(Component.TEXT, **style)

    @classmethod
    def image(cls, **style: typing.Unpack[ImageStyleOverrides]):
        return cls(Component.IMAGE, **style)

    def __enter__(self) -> typing.Self:
        context = _get_context()
        if self._component not in context._style_stacks:
            context._start_style_stack(self._component)
        cur_style = context._style_stacks[self._component][-1]
        composed_style = dataclasses.replace(cur_style, **self._style)
        context._style_stacks[self._component].append(composed_style)
        return self

    def __exit__(self, *args, **kwargs):
        context = _get_context()
        context._style_stacks[self._component].pop(-1)


class push_id:
    __module__ = "dimi"

    def __init__(self, id_: typing.Any):
        self._id = id_

    def __enter__(self) -> typing.Self:
        context = _get_context()
        context._id_stack.append(hash((context._id_stack[-1], self._id)))
        return self

    def __exit__(self, *args, **kwargs):
        context = _get_context()
        context._id_stack.pop(-1)


def _get_context() -> Context:
    if using._current_context is None:
        raise IllegalOperation("UI operation requires an active context (dimi.use())")
    return using._current_context


def get_current_context() -> Context | None:
    return using._current_context


def element(
    style: Style | None = None, **style_overrides: typing.Unpack[StyleOverrides]
) -> Interaction:
    return _get_context()._element(style, style_overrides)


def begin(
    style: Style | None = None, **style_overrides: typing.Unpack[StyleOverrides]
) -> Interaction:
    return _get_context()._begin(style, style_overrides)


def end():
    _get_context()._end()


def get_interaction(element_id: int) -> Interaction | None:
    context = _get_context()
    if element_id in context._node_memory:
        context._node = context._node_memory[element_id]
        interaction = Interaction(context)
        interaction._is_element = False
        return interaction
    return None


def rect(
    style: RectStyle | None = None,
    **style_ovverrides: typing.Unpack[RectStyleOverrides],
):
    _get_context()._component(Component.RECT, None, style, style_ovverrides)


def ellipse(
    style: EllipseStyle | None = None,
    **style_overrides: typing.Unpack[EllipseStyleOverrides],
):
    _get_context()._component(Component.ELLIPSE, None, style, style_overrides)


def text(
    text: str,
    style: TextStyle | None = None,
    **style_overrides: typing.Unpack[TextStyleOverrides],
):
    _get_context()._component(
        Component.TEXT,
        text if isinstance(text, str) else str(text),
        style,
        style_overrides,
    )


def image(
    image,
    style: ImageStyle | None = None,
    **style_overrides: typing.Unpack[ImageStyleOverrides],
):
    _get_context()._component(Component.IMAGE, image, style, style_overrides)


def when(
    interaction: Interaction,
    default: typing.Any,
    hovered: typing.Any | None = None,
    held: typing.Any | None = None,
    *,
    force_held: bool = False,
    force_hovered: bool = False,
    button: Button | None = Button.LEFT,
) -> typing.Any:
    variant = default
    if held is not None and force_held:
        variant = held
    if hovered is not None and (force_hovered or interaction.hovered):
        variant = hovered
    if held is not None and interaction.button_status == ButtonStatus.HELD and (button is None or interaction.button == button):
        variant = held
    return variant


