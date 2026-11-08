import typing
import weakref

import pygame
from pygame import _render

from dimi._canvas import Canvas, RendererCanvas, SurfaceCanvas
from dimi._components import (
    DEFAULT_COMPONENT_STYLE_CLASSES,
    SHAPE_HIT_TEST_CALLBACKS,
    Component,
)
from dimi._interaction import Button, ButtonStatus, HoverStatus, Interaction
from dimi._node import Node
from dimi._primitives import Exact, RenderOrder
from dimi._style import Style
from dimi.error import WidgetRegistrationError


class ContextOrigin:
    __module__ = "dimi"

    def __init__(
        self,
        window_origin: pygame.Window | pygame.typing.Point,
        canvas_origin: pygame.typing.Point = (0, 0),
    ):
        self.window_origin: pygame.Window | pygame.typing.Point = window_origin
        self.canvas_origin = canvas_origin

    @property
    def origin(self) -> tuple[int, int]:
        if isinstance(self.window_origin, pygame.Window):
            window_position = self.window_origin.position
            return (
                int(window_position[0] + self.canvas_origin[0]),
                int(window_position[1] + self.canvas_origin[1]),
            )
        return (
            int(self.window_origin[0] + self.canvas_origin[0]),
            int(self.window_origin[1] + self.canvas_origin[1]),
        )


class Context:
    __module__ = "dimi"
    _registered_widgets: typing.ClassVar[set[str]] = set()
    _registered_widget_on_event: typing.ClassVar[
        dict[str, typing.Callable[[pygame.Event, Context], None]]
    ] = {}
    _registered_widget_on_start: typing.ClassVar[
        dict[str, typing.Callable[[Context], None]]
    ] = {}

    def __init__(
        self,
        origin: ContextOrigin | pygame.Window,
        canvas: Canvas | pygame.Surface | _render.Renderer,
    ):
        if isinstance(canvas, pygame.Surface):
            canvas = SurfaceCanvas(canvas)
        elif isinstance(canvas, _render.Renderer):
            canvas = RendererCanvas(canvas)
        if isinstance(origin, pygame.Window):
            origin = ContextOrigin(origin)
        self.origin: ContextOrigin = origin
        self.canvas: Canvas = canvas

        self._id_stack: list[int] = []
        self._style_stacks: dict[str | None, list[Style]] = {}
        self._parent_stack: list[Node] = []
        self._element_stack: list[Node] = []

        self._node_memory: dict[int, Node] = {}
        self._widget_memories: dict[str, dict[typing.Hashable, dict | typing.Any]] = {}

        self._node: Node | None = None
        self._dummy_node: Node = Node(self, Style(), 0, (None, {}))

        self._hovered_node: Node | None = None
        self._hovered_id: int | None = None
        self._active_button: int = -1
        self._active_id: int | None = None

        self._mouse_pos: tuple[int, int] | None = None

    @property
    def viewport(self) -> pygame.Rect:
        canvas_viewport = self.canvas.viewport
        origin = self.origin.origin
        return pygame.Rect(
            (origin[0] + canvas_viewport.x, origin[1] + canvas_viewport.y),
            canvas_viewport.size,
        )

    def process_event(self, event: pygame.Event):
        for event_handler in Context._registered_widget_on_event.values():
            event_handler(event, self)

    def get_interaction(self, element_id: int) -> Interaction | None:
        if element_id in self._node_memory:
            self._node = self._node_memory[element_id]
            interaction = Interaction(self, self._node)
            interaction._is_element = False
            return interaction
        return None

    def get_last_id(self) -> int:
        return self._id_stack[-1]

    def get_last_interaction(self) -> Interaction | None:
        if not self._element_stack:
            return None
        interaction_ref = self._element_stack[-1].interaction
        if interaction_ref is None:
            return None
        return interaction_ref()

    def get_last_parent_interaction(self) -> Interaction | None:
        if not self._parent_stack:
            return None
        interaction_ref = self._parent_stack[-1].interaction
        if interaction_ref is None:
            return None
        return interaction_ref()

    def get_widget_state[**FactoryParamSpec](
        self,
        widget: str,
        init_factory: typing.Callable[
            typing.Concatenate[typing.Hashable, FactoryParamSpec], typing.Any
        ],
        id_: typing.Hashable | None = None,
        *,
        init_args: FactoryParamSpec.args = (),
        init_kwargs: FactoryParamSpec.kwargs | None = None,
    ) -> typing.Any:
        if widget not in self._widget_memories:
            if widget not in self._registered_widgets:
                raise WidgetRegistrationError(
                    f"Cannot get/init the state of an unregistered widget. Use dimi.register_widget('{widget}') to register it"
                )
            self._widget_memories[widget] = {}
        memory = self._widget_memories[widget]
        if id_ is None:
            id_ = self._id_stack[-1]
        if id_ not in memory:
            if init_kwargs is None:
                state = init_factory(id_, *init_args)
            else:
                state = init_factory(id_, *init_args, **init_kwargs)
            memory[id_] = state
        return memory[id_]

    def discard_widget_state(self, widget: str, id_: typing.Hashable) -> bool:
        if widget not in self._widget_memories:
            if widget not in self._registered_widgets:
                raise WidgetRegistrationError(
                    f"Cannot discard the state of an unregistered widget. Use dimi.register_widget('{widget}') to register it"
                )
            return False
        memory = self._widget_memories[widget]
        if id_ in memory:
            memory.pop(id_)
            return True
        return False

    def iter_widget_states(self, widget: str) -> typing.Generator[dict | typing.Any]:
        if widget not in self._widget_memories:
            if widget not in self._registered_widgets:
                raise WidgetRegistrationError(
                    f"Cannot iterate the states of an unregistered widget. Use dimi.register_widget('{widget}') to register it"
                )
            self._widget_memories[widget] = {}
        yield from self._widget_memories[widget].values()

    def _start(self, style=None):
        viewport = self.viewport
        self._parent_stack = []
        self._element_stack = []
        self._node = None
        self._style_stacks = {None: [Style()]}
        self._id_stack = [hash("root")]
        self.canvas._using_start()
        for start_callback in Context._registered_widget_on_start.values():
            start_callback(self)
        self._begin(
            style, {"width": Exact(viewport.width), "height": Exact(viewport.height)}
        )

    def _start_style_stack(self, component):
        self._style_stacks[component] = [DEFAULT_COMPONENT_STYLE_CLASSES[component]()]

    def _compose_style_component(self, component: str | None, style, style_overrides):
        if component not in self._style_stacks:
            self._start_style_stack(component)
        if style is not None:
            composed_style = style
        else:
            composed_style = self._style_stacks[component][-1]
        if style_overrides:
            composed_style = composed_style._fast_replace(style_overrides)
        return composed_style

    def _compose_style_element(self, style, style_overrides, memory):
        if style is not None:
            composed_style = style
        else:
            composed_style = self._style_stacks[None][-1]
        style_args = (composed_style, style_overrides)
        if memory is not None:
            mem_style, mem_overrides = memory.style_args
            if (
                composed_style is mem_style or composed_style == mem_style
            ) and style_overrides == mem_overrides:
                return memory.style, style_args
        if style_overrides:
            composed_style = composed_style._fast_replace(style_overrides)
        return composed_style, style_args

    def _create_node(self, style: Style | None, style_overrides):
        id_ = self._id_stack[-1]
        self._id_stack[-1] += 1

        memory = self._node_memory.get(id_, None)
        style, style_args = self._compose_style_element(style, style_overrides, memory)
        node = Node(self, style, id_, style_args)

        self._node = node
        if not self._parent_stack:
            return node, memory

        parent = self._parent_stack[-1]
        if node.style.position is None:
            parent.relative_children.append(node)
        else:
            parent.absolute_children.append(node)
        return node, memory

    def _element(self, style, style_overrides):
        node, memory = self._create_node(style, style_overrides)
        interaction = Interaction(self, memory)
        node.interaction = weakref.ref(interaction)
        return interaction

    def _begin(self, style, style_overrides):
        node, memory = self._create_node(style, style_overrides)
        self._parent_stack.append(node)
        interaction = Interaction(self, memory)
        interaction._is_parent = True
        node.interaction = weakref.ref(interaction)
        self._element_stack.append(node)
        return interaction

    def _end(self):
        self._element_stack.pop(-1)
        return self._parent_stack.pop(-1)

    def _component(self, component: str, data, style, style_overrides):
        style = self._compose_style_component(component, style, style_overrides)
        node = self._element_stack[-1]
        if component in (
            Component.TEXT,
            Component.IMAGE,
        ):
            comp = [component, data, style]
            node.intrinsic_components.append(comp)
        else:
            comp = (component, data, style)
        render_order = getattr(style, "render_order", RenderOrder.DEFAULT)
        if (
            (render_order == RenderOrder.ABOVE_CHILDREN)
            or (node.relative_children or node.absolute_children)
        ) and render_order != RenderOrder.BELOW_CHILDREN:
            node.components_above.append(comp)
        else:
            node.components_below.append(comp)
        if getattr(style, "shape", False) == True:
            node.shape = comp

    def _update_interaction_draw(self, node: Node, parent_viewport):
        viewport = parent_viewport
        fast_hitbox = node.absolute_rect.clip(parent_viewport)

        if node.style.clip_graphics:
            viewport = fast_hitbox

            if fast_hitbox.w <= 0 or fast_hitbox.h <= 0:
                return

            self.canvas.viewport = viewport
        node.render_rect = self.canvas._get_render_rect(node.absolute_rect, viewport)

        if fast_hitbox.collidepoint(self._mouse_pos):
            colliding = True
            if node.shape is not None:
                hit_test_callback = SHAPE_HIT_TEST_CALLBACKS[node.shape[0]]
                colliding = hit_test_callback(
                    fast_hitbox, self._mouse_pos, *node.shape[1:]
                )
            if colliding:
                node.hover_status = HoverStatus.BOUNDS
                if node.style.blocking:
                    self._hovered_node = node

        if node.components_below:
            comps = node.components_below
            if len(comps) > 1 and any(c[2].z != 0 for c in comps):
                comps = sorted(comps, key=lambda c: c[2].z)
            for comp, data, style, *other in comps:
                self.canvas._component_render_methods[comp](
                    node.render_rect, data, style, *other
                )

        if node.relative_children or node.absolute_children:
            if not node.absolute_children:
                children = node.relative_children
            elif not node.relative_children:
                children = node.absolute_children
            else:
                children = node.relative_children + node.absolute_children

            if len(children) > 1 and any(c.style.z != 0 for c in children):
                children = sorted(children, key=lambda child: child.style.z)

            for child in children:
                self._update_interaction_draw(child, viewport)

        if node.components_above:
            comps = node.components_above
            if len(comps) > 1 and any(c[2].z != 0 for c in comps):
                comps = sorted(comps, key=lambda c: c[2].z)
            for comp, data, style, *other in comps:
                self.canvas._component_render_methods[comp](
                    node.render_rect, data, style, *other
                )

        if node.style.clip_graphics:
            self.canvas.viewport = parent_viewport

    def _get_active_mouse_index(self, button_states) -> int:
        for i, state in enumerate(button_states):
            if state:
                return i
        return -1

    def _finish(self):
        root = self._end()
        viewport = self.viewport

        self.canvas._render_start()

        self._node_memory.clear()
        root.measure(0, viewport.width, 0, viewport.height)
        root.arrange(0, 0, 0, 0, (0, 0))

        self._hovered_node = None
        mouse = pygame.mouse.get_pos(True)
        self._mouse_pos = (mouse[0] - viewport.x, mouse[1] - viewport.y)

        self._update_interaction_draw(root, self.canvas.viewport)
        self.canvas._render_end()
        self.canvas._using_end()

        just_pressed = self._get_active_mouse_index(pygame.mouse.get_just_pressed())
        just_released = self._get_active_mouse_index(pygame.mouse.get_just_released())

        if self._hovered_node is not None:
            if self._active_id is None or self._active_id == self._hovered_node.id:
                self._hovered_node.hover_status = HoverStatus.HOVERED
                if self._hovered_node.id != self._hovered_id:
                    self._hovered_node.hover_status = HoverStatus.JUST_HOVERED
                    node = self._node_memory.get(self._hovered_id, None)
                    if node is not None:
                        node.hover_status = HoverStatus.JUST_UNHOVERED
                self._hovered_id = self._hovered_node.id
                if self._active_id is None and just_pressed != -1:
                    self._active_button = just_pressed
                    self._active_id = self._hovered_node.id
                    self._hovered_node.active_button = Button(just_pressed)
                    self._hovered_node.active_status = ButtonStatus.JUST_PRESSED
        else:
            if self._hovered_id is not None:
                node = self._node_memory.get(self._hovered_id, None)
                if node is not None:
                    node.hover_status = HoverStatus.JUST_UNHOVERED
            self._hovered_id = None

        if self._active_id is not None and just_released == self._active_button:
            node = self._node_memory.get(self._active_id, None)
            if node is not None:
                node.active_button = Button(just_released)
                if node.hover_status == HoverStatus.HOVERED:
                    node.active_status = ButtonStatus.CLICKED
                else:
                    node.active_status = ButtonStatus.JUST_RELEASED
            self._active_button = -1
            self._active_id = None

        if (
            self._active_id is not None
            and self._active_button != -1
            and just_pressed == -1
        ):
            node = self._node_memory.get(self._active_id, None)
            if node is not None:
                node.active_button = Button(self._active_button)
                node.active_status = ButtonStatus.HELD
