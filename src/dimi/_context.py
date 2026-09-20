import dataclasses

import pygame
from pygame import _render

from dimi._canvas import Canvas, RendererCanvas, SurfaceCanvas
from dimi._style import Style
from dimi._primitives import Exact, RenderOrder
from dimi._node import Node
from dimi._interaction import Interaction, ButtonStatus, HoverStatus
from dimi._components import (
    Component,
    SHAPE_HIT_TEST_CALLBACKS,
    DEFAULT_COMPONENT_STYLE_CLASSES,
)


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
        self._widget_memories: dict[str, dict[int, dict]] = {"entry_line": {}}

        self._node: Node | None = None

        self._hovered_node: Node | None = None
        self._hovered_id: int | None = None
        self._active_button: int = -1
        self._active_id: int | None = None

        self._mouse_pos: tuple[int, int] | None = None

        self._dummy_node: Node = Node(self, Style(), 0)

    @property
    def viewport(self) -> pygame.Rect:
        canvas_viewport = self.canvas.viewport
        origin = self.origin.origin
        return pygame.Rect(
            (origin[0] + canvas_viewport.x, origin[1] + canvas_viewport.y),
            canvas_viewport.size,
        )

    def _start(self, style=None):
        viewport = self.viewport
        self._parent_stack = []
        self._element_stack = []
        self._node = None
        self._style_stacks = {None: [Style()]}
        self._id_stack = [hash("root")]
        self._begin(
            style, {"width": Exact(viewport.width), "height": Exact(viewport.height)}
        )

    def _start_style_stack(self, component):
        self._style_stacks[component] = [DEFAULT_COMPONENT_STYLE_CLASSES[component]()]

    def _compose_style(self, component: str | None, style, style_overrides):
        if component not in self._style_stacks:
            self._start_style_stack(component)
        composed_style = self._style_stacks[component][-1]
        if style is not None:
            composed_style = style
        if len(style_overrides) > 0:
            composed_style = dataclasses.replace(composed_style, **style_overrides)
        return composed_style

    def _create_node(self, style: Style | None, style_overrides):
        style = self._compose_style(None, style, style_overrides)
        id_ = self._id_stack[-1]
        self._id_stack[-1] += 1
        node = Node(self, style, id_)
        self._node = node
        if len(self._parent_stack) <= 0:
            return node
        parent = self._parent_stack[-1]
        if node.style.position is None:
            parent.relative_children.append(node)
        else:
            parent.absolute_children.append(node)
        return node

    def _element(self, style, style_overrides):
        node = self._create_node(style, style_overrides)
        return Interaction(self)

    def _begin(self, style, style_overrides):
        node = self._create_node(style, style_overrides)
        self._parent_stack.append(node)
        interaction = Interaction(self)
        interaction._is_parent = True
        self._element_stack.append(node)
        return interaction

    def _end(self):
        self._element_stack.pop(-1)
        return self._parent_stack.pop(-1)

    def _component(self, component: str, data, style, style_overrides):
        style = self._compose_style(component, style, style_overrides)
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
            or (len(node.relative_children) > 0 or len(node.absolute_children) > 0)
        ) and render_order != RenderOrder.BELOW_CHILDREN:
            node.components_above.append(comp)
        else:
            node.components_below.append(comp)
        if getattr(style, "shape", False) == True:
            node.shape = comp

    def _update_interaction_draw(self, node: Node, parent_viewport):
        viewport = parent_viewport
        if node.style.clip_graphics:
            viewport = node.absolute_rect.clamp(parent_viewport)
            self.canvas.viewport = viewport
        node.render_rect = self.canvas._get_render_rect(node.absolute_rect, viewport)

        fast_hitbox = node.absolute_rect.clamp(parent_viewport)
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

        for comp, data, style, *other in node.components_below:
            # todo support custom components and change how the canvas method is checked
            self.canvas._component_render_methods[comp](
                node.render_rect, data, style, *other
            )

        for child in sorted(
            node.relative_children + node.absolute_children,
            key=lambda child: child.style.z,
        ):
            self._update_interaction_draw(child, viewport)

        for comp, data, style, *other in node.components_above:
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

        self._node_memory.clear()
        root.measure(0, viewport.width, 0, viewport.height)
        root.arrange(0, 0, 0, 0)

        self._hovered_node = None
        mouse = pygame.mouse.get_pos(True)
        self._mouse_pos = (mouse[0] - viewport.x, mouse[1] - viewport.y)

        self.canvas._render_start()
        self._update_interaction_draw(root, self.canvas.viewport)
        self.canvas._render_end()

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
                    self._hovered_node.active_button = just_pressed
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
                node.active_button = just_released
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
                node.active_button = self._active_button
                node.active_status = ButtonStatus.HELD

        # TEST
        return

        def render_node(node: Node):
            self.canvas.renderer.draw_color = "green" if node.absolute_hover else "red"
            if node is self._hovered_node:
                self.canvas.renderer.draw_color = "pink"
            self.canvas.renderer.draw_rect(node.absolute_rect)
            for child in sorted(
                node.relative_children + node.absolute_children,
                key=lambda child: child.style.z,
            ):

                render_node(child)

        render_node(root)
