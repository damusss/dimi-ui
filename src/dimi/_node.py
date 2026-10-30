import math
import typing
import weakref

import pygame

from dimi._components import Component
from dimi._error import IllegalOperation
from dimi._interaction import ButtonStatus, HoverStatus
from dimi._primitives import (
    Align,
    Axis,
    B,
    Exact,
    Fill,
    Hug,
    L,
    Percent,
    R,
    Ratio,
    SizeIntent,
    Span,
    T,
    get_directional_measure,
)
from dimi._style import Style

if typing.TYPE_CHECKING:
    from dimi._context import Context
    from dimi._interaction import Interaction

CX = 4
CY = 5

MNW = 0
MXW = 1
MNH = 2
MXH = 3


class Node:
    __module__ = "dimi.typehinting"

    def __init__(self, context, style: Style, id_: int):
        # hardcoded from declaration
        self.context: Context = context
        self.style = style
        self.id = id_

        # controlled during declaration
        self.relative_children: list[Node] = []
        self.absolute_children: list[Node] = []
        self.components_below: list[tuple | list] = []
        self.components_above: list[tuple | list] = []
        self.intrinsic_components: list[list] = []
        self.shape: tuple | list | None = None

        self.interaction: weakref.ref[Interaction] | None = None

        # calculated during measure/arrange
        self.measured_width = 0
        self.measured_height = 0
        self.measured_width_no_margins = 0
        self.measured_height_no_margins = 0
        self.pads_px: tuple[int, int, int, int] = (0, 0, 0, 0)
        self.margins_px: tuple[int, int, int, int] = (0, 0, 0, 0)
        self.spacing_px: int = 0
        self.absolute_anchors: list[int | None] = [None, None, None, None, None, None]
        self.constrained_size = (None, None, None, None)
        self.children_overflow: pygame.Vector2 = pygame.Vector2()

        # measure/arrange output
        self.absolute_rect: pygame.Rect | None = None
        self.relative_rect: pygame.Rect | None = None
        self.render_rect: pygame.Rect | None = None

        # interaction output
        self.hover_status = HoverStatus.NONE
        self.active_button = -1
        self.active_status = ButtonStatus.NONE

    def resolve_intrinsic_components(self):
        can_wrap_width = not isinstance(self.style.width, Hug)
        biggest_w = 0
        biggest_h = 0
        for component in self.intrinsic_components:
            comp, data, style = component
            resolved_w = 0
            resolved_h = 0
            if comp == Component.IMAGE:
                ratio = data.width / data.height
                if isinstance(self.style.width, Hug) and isinstance(
                    self.style.height, Hug
                ):
                    resolved_w = data.width
                    resolved_h = data.height
                    padding = get_directional_measure(
                        style.padding,
                        resolved_w,
                        resolved_h,
                        "padding",
                    )
                    resolved_w += padding[L] + padding[R]
                    resolved_h += padding[T] + padding[B]
                    component.append(padding)
                elif isinstance(self.style.width, Hug):
                    padding = get_directional_measure(
                        style.padding,
                        self.measured_width_no_margins,
                        self.measured_height_no_margins,
                        "padding",
                    )
                    resolved_h = (
                        self.measured_height_no_margins - padding[T] - padding[B]
                    )
                    resolved_w = resolved_h * ratio
                    padding = get_directional_measure(
                        style.padding,
                        resolved_w,
                        resolved_h,
                        "padding",
                    )
                    resolved_w += padding[L] + padding[R]
                    component.append(padding)
                elif isinstance(self.style.height, Hug):
                    padding = get_directional_measure(
                        style.padding,
                        self.measured_width_no_margins,
                        self.measured_height_no_margins,
                        "padding",
                    )
                    resolved_w = (
                        self.measured_width_no_margins - padding[L] - padding[R]
                    )
                    resolved_h = resolved_w / ratio
                    padding = get_directional_measure(
                        style.padding,
                        resolved_w,
                        resolved_h,
                        "padding",
                    )
                    resolved_h += padding[T] + padding[B]
                    component.append(padding)
                else:
                    padding = get_directional_measure(
                        style.padding,
                        self.measured_width_no_margins,
                        self.measured_height_no_margins,
                        "padding",
                    )
                    component.append(padding)
            elif comp == Component.TEXT:
                if can_wrap_width and style.wrap:
                    wrap_width = self.measured_width_no_margins
                else:
                    wrap_width = 0
                height = self.measured_height_no_margins
                if isinstance(style.size, Percent | Span) and isinstance(
                    self.style.height, Hug
                ):
                    raise IllegalOperation(
                        "Text size can't be a percentage of the height if the element's height is Hug()"
                    )
                cache_key = hash((hash(data), hash(style), wrap_width, height))
                resolved_w, resolved_h = self.context.canvas._resolve_text(
                    cache_key, data, style, wrap_width, height
                )
                component.append(cache_key)
            if resolved_w > biggest_w:
                biggest_w = resolved_w
            if resolved_h > biggest_h:
                biggest_h = resolved_h

        return biggest_w, biggest_h

    def intrinsic_components_dont_wrap(self):
        for comp, data, style, *other in self.intrinsic_components:
            if comp == Component.TEXT:
                if style.wrap:
                    return False
        return True

    def apply_measure_constrained(
        self,
        width_no_margins,
        height_no_margins,
    ):
        self.measured_width_no_margins = min(
            max(width_no_margins, self.constrained_size[MNW]),
            self.constrained_size[MXW],
        )
        self.measured_height_no_margins = min(
            max(height_no_margins, self.constrained_size[MNH]),
            self.constrained_size[MXH],
        )

        self.measured_width = (
            self.measured_width_no_margins + self.margins_px[L] + self.margins_px[R]
        )
        self.measured_height = (
            self.measured_height_no_margins + self.margins_px[T] + self.margins_px[B]
        )

    def measure(
        self,
        min_w: float,
        max_w: float,
        min_h: float,
        max_h: float,
        parent_axis: Axis | None = Axis.Y,
        parent_style: Style | None = None,
        parent_spacing: float = 0,
        arrange_measure: bool = False,
    ):
        if not arrange_measure:
            self.margins_px = get_directional_measure(
                self.style.margin, max_w, max_h, "margin"
            )

            self.pads_px = get_directional_measure(
                self.style.padding, max_w, max_h, "padding"
            )

            self.spacing_px = SizeIntent._sizefy(self.style.spacing)._measure(
                max_w, max_h, Axis.X
            )

        margined_max_w = max(0, max_w - self.margins_px[L] - self.margins_px[R])
        margined_max_h = max(0, max_h - self.margins_px[T] - self.margins_px[B])

        if not arrange_measure:
            constrained_min_w = max(0, min_w - self.margins_px[L] - self.margins_px[R])
            constrained_min_h = max(0, min_h - self.margins_px[T] - self.margins_px[B])
            constrained_max_w = math.inf
            constrained_max_h = math.inf
            if self.style.width_constraint is not None:
                if self.style.width_constraint.min is not None:
                    constrained_min_w = max(
                        constrained_min_w,
                        SizeIntent._sizefy(self.style.width_constraint.min)._measure(
                            max_w, max_h, Axis.X
                        ),
                    )
                if self.style.width_constraint.max is not None:
                    constrained_max_w = min(
                        constrained_max_w,
                        SizeIntent._sizefy(self.style.width_constraint.max)._measure(
                            max_w, max_h, Axis.X
                        ),
                    )
            if self.style.height_constraint is not None:
                if self.style.height_constraint.min is not None:
                    constrained_min_h = max(
                        constrained_min_h,
                        SizeIntent._sizefy(self.style.height_constraint.min)._measure(
                            max_w, max_h, Axis.Y
                        ),
                    )
                if self.style.height_constraint.max is not None:
                    constrained_max_h = min(
                        constrained_max_h,
                        SizeIntent._sizefy(self.style.height_constraint.max)._measure(
                            max_w, max_h, Axis.Y
                        ),
                    )
            self.constrained_size = (
                constrained_min_w,
                constrained_max_w,
                constrained_min_h,
                constrained_max_h,
            )

        max_w_for_inner = margined_max_w
        max_h_for_inner = margined_max_h

        if arrange_measure:
            tentative_w = self.measured_width_no_margins
            tentative_h = self.measured_height_no_margins
        else:
            tentative_w = 0
            tentative_h = 0
            set_w = False
            set_h = False
            w_is_ratio = False

            width = SizeIntent._sizefy(self.style.width)

            if isinstance(width, Exact):
                tentative_w = width.pixels
                set_w = True
            elif isinstance(width, Percent):
                tentative_w = width._measure(margined_max_w, margined_max_h, Axis.X)
                set_w = True
                if parent_style is not None and isinstance(parent_style.width, Hug):
                    raise IllegalOperation(
                        "Child with Percent width cannot be measured inside a parent with Hug width"
                    )
            elif isinstance(width, Span):
                tentative_w = (
                    margined_max_w - (parent_spacing * (width.count - 1))
                ) * width.weight
                set_w = True
                if parent_style is not None and isinstance(parent_style.width, Hug):
                    raise IllegalOperation(
                        "Child with Span width cannot be measured inside a parent with Hug width"
                    )
            elif isinstance(width, Ratio):
                w_is_ratio = True
            elif isinstance(width, Fill):
                if parent_axis in (Axis.Y, None):
                    tentative_w = width.weight * margined_max_w
                    set_w = True
                if parent_style is not None and isinstance(parent_style.width, Hug):
                    raise IllegalOperation(
                        "Child with Fill width cannot be measured inside a parent with Hug width"
                    )

            height = SizeIntent._sizefy(self.style.height)

            if isinstance(height, Exact):
                tentative_h = height.pixels
                set_h = True
            elif isinstance(height, Percent):
                tentative_h = height._measure(margined_max_w, margined_max_h, Axis.Y)
                set_h = True
                if parent_style is not None and isinstance(parent_style.height, Hug):
                    raise IllegalOperation(
                        "Child with Percent height cannot be measured inside a parent with Hug height"
                    )
            elif isinstance(height, Span):
                tentative_h = (
                    margined_max_h - (parent_spacing * (height.count - 1))
                ) * height.weight
                set_h = True
                if parent_style is not None and isinstance(parent_style.height, Hug):
                    raise IllegalOperation(
                        "Child with Span height cannot be measured inside a parent with Hug height"
                    )
            elif isinstance(height, Ratio):
                if not set_w:
                    raise IllegalOperation(
                        "Element with Ratio height needs a well defined width of either Exact, Percent, or Span"
                    )
                tentative_h = tentative_w / height.ratio
                set_h = True
            elif isinstance(height, Fill):
                if parent_axis in (Axis.X, None):
                    tentative_h = height.weight * margined_max_h
                    set_h = True
                if parent_style is not None and isinstance(parent_style.height, Hug):
                    raise IllegalOperation(
                        "Child with Fill height cannot be measured inside a parent with Hug height"
                    )

            if w_is_ratio:
                if not set_h:
                    raise IllegalOperation(
                        "Element with Ratio width needs a well defined height of either Exact, Percent, or Span"
                    )
                tentative_w = tentative_h * width.ratio
                set_w = True

            self.apply_measure_constrained(tentative_w, tentative_h)

            if set_w:
                max_w_for_inner = self.measured_width_no_margins
            if set_h:
                max_h_for_inner = self.measured_height_no_margins

        inner_max_w = max(0, max_w_for_inner - self.pads_px[L] - self.pads_px[R])
        inner_max_h = max(0, max_h_for_inner - self.pads_px[T] - self.pads_px[B])

        width_paradox_fill = parent_axis == Axis.X and isinstance(
            self.style.width, Fill
        )
        height_paradox_fill = parent_axis == Axis.Y and isinstance(
            self.style.height, Fill
        )
        paradox_defer_measure = not arrange_measure and (
            width_paradox_fill or height_paradox_fill
        )

        if not paradox_defer_measure:
            for child in self.relative_children:
                child.measure(
                    0,
                    inner_max_w,
                    0,
                    inner_max_h,
                    self.style.axis,
                    self.style,
                    self.spacing_px,
                )

        if arrange_measure:
            if width_paradox_fill:
                tentative_w = margined_max_w

            if height_paradox_fill:
                tentative_h = margined_max_h

            self.apply_measure_constrained(tentative_w, tentative_h)

        if not arrange_measure:
            biggest_intrinsic_w = 0
            biggest_intrinsic_h = 0
            if (
                not isinstance(width, Fill)
                or parent_axis in (Axis.Y, None)
                or self.intrinsic_components_dont_wrap()
            ):
                biggest_intrinsic_w, biggest_intrinsic_h = (
                    self.resolve_intrinsic_components()
                )

            if isinstance(width, Hug):
                if self.style.axis == Axis.X:
                    tentative_w = sum(c.measured_width for c in self.relative_children)
                    tentative_w += self.spacing_px * max(
                        0, len(self.relative_children) - 1
                    )
                else:
                    tentative_w = max(
                        (c.measured_width for c in self.relative_children), default=0
                    )
                tentative_w += self.pads_px[L] + self.pads_px[R]
                if tentative_w < biggest_intrinsic_w:
                    tentative_w = biggest_intrinsic_w

            if isinstance(height, Hug):
                if self.style.axis == Axis.Y:
                    tentative_h = sum(c.measured_height for c in self.relative_children)
                    tentative_h += self.spacing_px * max(
                        0, len(self.relative_children) - 1
                    )
                else:
                    tentative_h = max(
                        (c.measured_height for c in self.relative_children), default=0
                    )
                tentative_h += self.pads_px[T] + self.pads_px[B]
                if tentative_h < biggest_intrinsic_h:
                    tentative_h = biggest_intrinsic_h

            if isinstance(width, Hug) or isinstance(height, Hug):
                self.apply_measure_constrained(tentative_w, tentative_h)

        if paradox_defer_measure:
            return

        for child in self.absolute_children:
            anchored_max_w = margined_max_w
            anchored_max_h = margined_max_h
            if child.style.position.left is not None:
                child.absolute_anchors[L] = SizeIntent._sizefy(
                    child.style.position.left
                )._measure(margined_max_w, margined_max_h, Axis.X)
                if isinstance(child.style.width, Fill):
                    anchored_max_w -= child.absolute_anchors[L]
            if child.style.position.right is not None:
                child.absolute_anchors[R] = SizeIntent._sizefy(
                    child.style.position.right
                )._measure(margined_max_w, margined_max_h, Axis.X)
                if isinstance(child.style.width, Fill):
                    anchored_max_w -= child.absolute_anchors[R]
            if child.style.position.top is not None:
                child.absolute_anchors[T] = SizeIntent._sizefy(
                    child.style.position.top
                )._measure(margined_max_w, margined_max_h, Axis.Y)
                if isinstance(child.style.height, Fill):
                    anchored_max_h -= child.absolute_anchors[T]
            if child.style.position.bottom is not None:
                child.absolute_anchors[B] = SizeIntent._sizefy(
                    child.style.position.bottom
                )._measure(margined_max_w, margined_max_h, Axis.Y)
                if isinstance(child.style.height, Fill):
                    anchored_max_h -= child.absolute_anchors[B]
            if child.style.position.center_x is not None:
                child.absolute_anchors[CX] = SizeIntent._sizefy(
                    child.style.position.center_x
                )._measure(margined_max_w, margined_max_h, Axis.X)
            if child.style.position.center_y is not None:
                child.absolute_anchors[CY] = SizeIntent._sizefy(
                    child.style.position.center_y
                )._measure(margined_max_w, margined_max_h, Axis.Y)
            if (
                child.absolute_anchors[L] is not None
                and child.absolute_anchors[R] is not None
                and (
                    not isinstance(child.style.width, Fill)
                    or child.style.width.weight != 1
                )
            ):
                raise IllegalOperation(
                    "An absolutely positioned element can't fulfill both lateral anchor requests simultaneously if the element's width isn't Fill(1)."
                )
            if (
                child.absolute_anchors[L] is not None
                or child.absolute_anchors[R] is not None
            ) and child.absolute_anchors[CX] is not None:
                raise IllegalOperation(
                    "An absolutely positioned element can't fulfill both the central anchor request and either of the later anchors simultaneously."
                )
            if (
                child.absolute_anchors[T] is not None
                and child.absolute_anchors[B] is not None
                and (
                    not isinstance(child.style.height, Fill)
                    or child.style.height.weight != 1
                )
            ):
                raise IllegalOperation(
                    "An absolutely positioned element can't fulfill both lateral anchor requests simultaneously if the element's height isn't Fill(1)."
                )
            if (
                child.absolute_anchors[T] is not None
                or child.absolute_anchors[B] is not None
            ) and child.absolute_anchors[CY] is not None:
                raise IllegalOperation(
                    "An absolutely positioned element can't fulfill both the central anchor request and either of the later anchors simultaneously."
                )
            child.measure(
                0, anchored_max_w, 0, anchored_max_h, None, None, self.spacing_px
            )

        # todo implement wrap

    def confirm_measure(
        self,
        width: float | None,
        height: float | None,
        parent_axis,
        parent_style,
        parent_spacing,
    ):
        if width is not None:
            self.apply_measure_constrained(
                width - self.margins_px[L] - self.margins_px[R],
                self.measured_height_no_margins,
            )
            if not self.intrinsic_components_dont_wrap():
                biggest_intrinsic_w, biggest_intrinsic_h = (
                    self.resolve_intrinsic_components()
                )
                if self.measured_height_no_margins < biggest_intrinsic_h and isinstance(
                    self.style.height, Hug
                ):
                    self.apply_measure_constrained(
                        self.measured_width_no_margins, biggest_intrinsic_h
                    )
            self.measure(
                0,
                self.measured_width,
                0,
                self.measured_height,
                parent_axis,
                parent_style,
                parent_spacing,
                True,
            )
        if height is not None:
            self.apply_measure_constrained(
                self.measured_width_no_margins,
                height - self.margins_px[T] - self.margins_px[B],
            )
            self.measure(
                0,
                self.measured_width,
                0,
                self.measured_height,
                parent_axis,
                parent_style,
                parent_spacing,
                True,
            )

    def arrange(self, x: float, y: float, parent_x, parent_y, parent_offset):
        x += self.margins_px[L] + self.style.self_offset[0] + parent_offset[0]
        y += self.margins_px[T] + self.style.self_offset[1] + parent_offset[1]
        self.relative_rect = pygame.Rect(
            x,
            y,
            self.measured_width_no_margins,
            self.measured_height_no_margins,
        )
        self.absolute_rect = pygame.Rect(
            x + parent_x,
            y + parent_y,
            self.measured_width_no_margins,
            self.measured_height_no_margins,
        )

        remaining_w = 0
        remaining_h = 0
        total_fill_weight = 0
        used_w = 0
        used_h = 0
        children_needing_fill: list[Node] = []

        if self.style.axis == Axis.X:
            for c in self.relative_children:
                if isinstance(c.style.width, Fill):
                    total_fill_weight += c.style.width.weight
                    children_needing_fill.append(c)
                else:
                    used_w += c.measured_width
            used_w += self.spacing_px * max(0, len(self.relative_children) - 1)
            remaining_w = max(
                0,
                self.measured_width_no_margins
                - used_w
                - self.pads_px[L]
                - self.pads_px[R],
            )
        else:  # Axis.Y
            for c in self.relative_children:
                if isinstance(c.style.height, Fill):
                    total_fill_weight += c.style.height.weight
                    children_needing_fill.append(c)
                else:
                    used_h += c.measured_height
            used_h += self.spacing_px * max(0, len(self.relative_children) - 1)
            remaining_h = max(
                0,
                self.measured_height_no_margins
                - used_h
                - self.pads_px[T]
                - self.pads_px[B],
            )

        fill_mult = 1
        if self.style.axis == Axis.X:
            total_fill_size = total_fill_weight * remaining_w
            if total_fill_size > remaining_w:
                fill_mult = remaining_w / total_fill_size
        else:  # Axis.Y
            total_fill_size = total_fill_weight * remaining_h
            if total_fill_size > remaining_h:
                fill_mult = remaining_h / total_fill_size
        for child in children_needing_fill:
            if self.style.axis == Axis.X:
                prev_h = child.measured_height
                child.confirm_measure(
                    remaining_w * child.style.width.weight * fill_mult,
                    None,
                    self.style.axis,
                    self.style,
                    self.spacing_px,
                )
                used_w += child.measured_width
                used_h += child.measured_height - prev_h
                if (
                    isinstance(self.style.height, Hug)
                    and child.measured_height != prev_h
                ):
                    raise IllegalOperation(
                        "Due to layout complexity it is illegal to create a parent with height Hug() containing a child with width Fill() and height Hug() containing intrinsic text that resizes based on wrap width."
                    )
            else:  # Axis.Y
                child.confirm_measure(
                    None,
                    remaining_h * child.style.height.weight * fill_mult,
                    self.style.axis,
                    self.style,
                    self.spacing_px,
                )
                used_h += child.measured_height

        cursor_x = self.pads_px[L]  # Align.FIRST
        cursor_y = self.pads_px[T]  # Align.FIRST
        if self.style.axis == Axis.X:
            if self.style.align_children == Align.LAST:
                cursor_x = self.measured_width_no_margins - self.pads_px[R] - used_w
            elif self.style.align_children == Align.CENTER:
                cursor_x = self.measured_width_no_margins / 2 - used_w / 2
        else:  # Axis.Y
            if self.style.align_children == Align.LAST:
                cursor_y = self.measured_height_no_margins - self.pads_px[B] - used_h
            elif self.style.align_children == Align.CENTER:
                cursor_y = self.measured_height_no_margins / 2 - used_h / 2

        rightmost_opposite = 0
        for child in self.relative_children:
            x = cursor_x
            y = cursor_y
            if self.style.axis == Axis.X:
                cursor_x += child.measured_width + self.spacing_px
                if child.style.align_self == Align.LAST:
                    y = (
                        self.measured_height_no_margins
                        - child.measured_height
                        - self.pads_px[B]
                    )
                elif child.style.align_self == Align.CENTER:
                    y = self.measured_height_no_margins / 2 - child.measured_height / 2
            else:
                cursor_y += child.measured_height + self.spacing_px
                if child.style.align_self == Align.LAST:
                    x = (
                        self.measured_width_no_margins
                        - child.measured_width
                        - self.pads_px[R]
                    )
                elif child.style.align_self == Align.CENTER:
                    x = self.measured_width_no_margins / 2 - child.measured_width / 2
            child.arrange(
                x,
                y,
                self.absolute_rect.x,
                self.absolute_rect.y,
                self.style.children_offset,
            )
            if self.style.axis == Axis.X:
                rightmost_opposite = max(rightmost_opposite, child.relative_rect.bottom)
            else:
                rightmost_opposite = max(rightmost_opposite, child.relative_rect.right)

        cursor_x -= self.spacing_px
        cursor_y -= self.spacing_px
        if self.style.axis == Axis.X:
            cursor_y = rightmost_opposite
        else:
            cursor_x = rightmost_opposite
        self.children_overflow.x = max(0, cursor_x - self.relative_rect.w)
        self.children_overflow.y = max(0, cursor_y - self.relative_rect.h)

        for child in self.absolute_children:
            anchor_x = 0
            anchor_y = 0
            if child.absolute_anchors[L] is not None:
                anchor_x = child.absolute_anchors[L]
            elif child.absolute_anchors[R] is not None:
                anchor_x = (
                    self.measured_width_no_margins
                    - child.absolute_anchors[R]
                    - child.measured_width
                )
            elif child.absolute_anchors[CX] is not None:
                anchor_x = child.absolute_anchors[CX] - child.measured_width / 2
            if child.absolute_anchors[T] is not None:
                anchor_y = child.absolute_anchors[T]
            elif child.absolute_anchors[B] is not None:
                anchor_y = (
                    self.measured_height_no_margins
                    - child.absolute_anchors[B]
                    - child.measured_height
                )
            elif child.absolute_anchors[CY] is not None:
                anchor_y = child.absolute_anchors[CY] - child.measured_height / 2

            child.arrange(
                anchor_x,
                anchor_y,
                self.absolute_rect.x,
                self.absolute_rect.y,
                self.style.children_offset,
            )

        self.context._node_memory[self.id] = self

        # todo implement wrap
