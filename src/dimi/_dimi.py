import typing

import pygame

from dimi._canvas import Canvas, RendererCanvas, SurfaceCanvas
from dimi._components import Component
from dimi._context import Context
from dimi._interaction import Button, ButtonStatus, Interaction
from dimi._primitives import Measure
from dimi._style import (
    EllipseStyle,
    EllipseStyleOverrides,
    ImageStyle,
    ImageStyleOverrides,
    LineStyle,
    LineStyleOverrides,
    RectStyle,
    RectStyleOverrides,
    Style,
    StyleOverrides,
    TextStyle,
    TextStyleOverrides,
)
from dimi.error import (
    CacheRegistrationError,
    MissingActiveContexError,
    WidgetRegistrationError,
)


class using:
    __module__ = "dimi"

    _context_stack: typing.ClassVar[list[Context | None]] = [None]

    def __init__(self, context: Context, style: Style | None = None):
        self.context: Context = context
        using._context_stack.append(context)
        context._start(style)

    def __enter__(self) -> typing.Self:
        return self

    def __exit__(self, *args, **kwargs):
        using._context_stack.pop()
        self.context._finish()


class push_style:
    __module__ = "dimi"

    def __init__(
        self, component: Component | None = None, **style: typing.Unpack[StyleOverrides]
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
        context = using._context_stack[-1]
        if context is None:
            raise MissingActiveContexError()
        if self._component not in context._style_stacks:
            context._start_style_stack(self._component)
        cur_style = context._style_stacks[self._component][-1]
        composed_style = cur_style._fast_replace(self._style)
        context._style_stacks[self._component].append(composed_style)
        return self

    def __exit__(self, *args, **kwargs):
        context = using._context_stack[-1]
        if context is None:
            raise MissingActiveContexError()
        context._style_stacks[self._component].pop(-1)


class push_id:
    __module__ = "dimi"

    def __init__(self, id_: typing.Hashable):
        self._id = id_

    def __enter__(self) -> typing.Self:
        context = using._context_stack[-1]
        if context is None:
            raise MissingActiveContexError()
        context._id_stack.append(hash((context._id_stack[-1], self._id)))
        return self

    def __exit__(self, *args, **kwargs):
        context = using._context_stack[-1]
        if context is None:
            raise MissingActiveContexError()
        context._id_stack.pop(-1)


def get_current_context() -> Context | None:
    return using._context_stack[-1]


def register_widget(
    widget: str,
    on_event: typing.Callable[[pygame.Event, Context], None] | None = None,
    on_start: typing.Callable[[Context], None] | None = None,
    # todo: add more callback options
):
    if widget in Context._registered_widgets:
        raise WidgetRegistrationError(f"Widget '{widget}' was already registered")
    Context._registered_widgets.add(widget)
    if on_event is not None:
        Context._registered_widget_on_event[widget] = on_event
    if on_start is not None:
        Context._registered_widget_on_start[widget] = on_start


def register_canvas_cache(
    cache: str,
    canvas_targets: tuple[type[Canvas], ...] = (RendererCanvas, SurfaceCanvas),
):
    for canvas_target in canvas_targets:
        if cache in canvas_target._registered_caches:
            raise CacheRegistrationError(cache, canvas_target, True)
        canvas_target._registered_caches.add(cache)


def element(
    style: Style | None = None, **style_overrides: typing.Unpack[StyleOverrides]
) -> Interaction:
    context = using._context_stack[-1]
    if context is None:
        raise MissingActiveContexError()
    return context._element(style, style_overrides)


def begin(
    style: Style | None = None, **style_overrides: typing.Unpack[StyleOverrides]
) -> Interaction:
    context = using._context_stack[-1]
    if context is None:
        raise MissingActiveContexError()
    return context._begin(style, style_overrides)


def end():
    context = using._context_stack[-1]
    if context is None:
        raise MissingActiveContexError()
    context._end()


def rect(
    style: RectStyle | None = None,
    **style_ovverrides: typing.Unpack[RectStyleOverrides],
):
    context = using._context_stack[-1]
    if context is None:
        raise MissingActiveContexError()
    context._component(Component.RECT, None, style, style_ovverrides)


def ellipse(
    style: EllipseStyle | None = None,
    **style_overrides: typing.Unpack[EllipseStyleOverrides],
):
    context = using._context_stack[-1]
    if context is None:
        raise MissingActiveContexError()
    context._component(Component.ELLIPSE, None, style, style_overrides)


def line(
    start_end: tuple[tuple[Measure, Measure], tuple[Measure, Measure]],
    style: LineStyle | None = None,
    **style_overrides: typing.Unpack[LineStyleOverrides],
):
    context = using._context_stack[-1]
    if context is None:
        raise MissingActiveContexError()
    context._component(Component.LINE, start_end, style, style_overrides)


def text(
    text: str,
    style: TextStyle | None = None,
    **style_overrides: typing.Unpack[TextStyleOverrides],
):
    context = using._context_stack[-1]
    if context is None:
        raise MissingActiveContexError()
    context._component(
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
    context = using._context_stack[-1]
    if context is None:
        raise MissingActiveContexError()
    context._component(Component.IMAGE, image, style, style_overrides)


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
    if held is not None and (
        force_held
        or (
            interaction.button_status == ButtonStatus.HELD
            and (button is None or interaction.button == button)
        )
    ):
        return held

    if hovered is not None and (force_hovered or interaction.hovered):
        return hovered

    return default


type NestedAttributesFormat = dict[str, NestedAttributesFormat | typing.Any]


def unflatten_nested_attributes_format(
    attributes_format: NestedAttributesFormat,
) -> NestedAttributesFormat:
    unflattened = {}
    for key, value in attributes_format.items():
        if "." in key:
            main, parts = key.split(".", 1)
            if main not in unflattened:
                unflattened[main] = {}
            if isinstance(unflattened[main], dict):
                unflattened[main][parts] = value
            else:
                unflattened[main] = {parts: value}
        else:
            if isinstance(value, dict):
                value = unflatten_nested_attributes_format(value)
            if (
                key in unflattened
                and isinstance(unflattened[key], dict)
                and isinstance(value, dict)
            ):
                unflattened[key].update(value)
            else:
                unflattened[key] = value

    for key, value in unflattened.items():
        if isinstance(value, dict):
            unflattened[key] = unflatten_nested_attributes_format(value)

    return unflattened


def replace_nested_style[StyleNamedTupleType](
    style: StyleNamedTupleType, attributes_format: NestedAttributesFormat
) -> StyleNamedTupleType:
    unflattened_format = unflatten_nested_attributes_format(attributes_format)
    changes = {}
    for key, value in unflattened_format.items():
        if isinstance(value, dict):
            changes[key] = replace_nested_style(getattr(style, key), value)
        else:
            changes[key] = value
    style = style._replace(**changes)
    return style
