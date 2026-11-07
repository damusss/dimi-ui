import math
import typing
import weakref

import pygame

from dimi._components import Component
from dimi._error import IllegalOperation
from dimi._interaction import ButtonStatus, HoverStatus
from dimi._primitives import (
    ZERO_DIRECTIONS,
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
    measure_value,
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

    def __init__(self, context, style: Style, id_: int, style_args):
        # hardcoded from declaration
        self.context: Context = context
        self.style = style
        self.style_args = style_args
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
        self.pads_px: tuple[float, float, float, float] = (0, 0, 0, 0)
        self.margins_px: tuple[float, float, float, float] = (0, 0, 0, 0)
        self.spacing_px: float = 0
        self.absolute_anchors: list[float | None] = [None, None, None, None, None, None]
        self.constrained_size = (None, None, None, None)
        self.children_overflow: tuple[float, float] = (0, 0)

        # measure/arrange output
        self.absolute_rect: pygame.Rect | None = None
        self.relative_rect: pygame.Rect | None = None
        self.render_rect: pygame.Rect | None = None

        # interaction output
        self.hover_status = HoverStatus.NONE
        self.active_button = -1
        self.active_status = ButtonStatus.NONE

    def resolve_intrinsic_components(self):
        width_is_hug = type(self.style.width) is Hug
        height_is_hug = type(self.style.height) is Hug
        biggest_w = 0
        biggest_h = 0
        for component in self.intrinsic_components:
            comp, data, style = component
            resolved_w = 0
            resolved_h = 0
            if comp == Component.IMAGE:
                ratio = data.width / data.height
                if width_is_hug and height_is_hug:
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
                elif width_is_hug:
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
                elif height_is_hug:
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
                if not width_is_hug and style.wrap:
                    wrap_width = self.measured_width_no_margins
                else:
                    wrap_width = 0
                height = self.measured_height_no_margins
                if isinstance(style.size, Percent | Span) and height_is_hug:
                    raise IllegalOperation(
                        "Text size can't be a percentage or a span of the height if the element's height is Hug()"
                    )
                cache_key = hash((hash(data), hash(style), wrap_width, height))
                resolved_w, resolved_h = self.context.canvas._resolve_text(
                    cache_key, data, style, wrap_width, height
                )
                component.append(cache_key)
                self.context.canvas._pinged_text_cache_keys.discard(cache_key)
            biggest_w = max(biggest_w, resolved_w)
            biggest_h = max(biggest_h, resolved_h)

        return biggest_w, biggest_h

    def intrinsic_components_dont_wrap(self):
        for comp, data, style, *other in self.intrinsic_components:
            if comp == Component.TEXT and style.wrap:
                return False
        return True

    def apply_measure_constrained(
        self,
        width_no_margins,
        height_no_margins,
    ):
        min_w, max_w, min_h, max_h = self.constrained_size

        width = width_no_margins if width_no_margins > min_w else min_w
        if max_w is not math.inf and width > max_w:
            width = max_w

        height = height_no_margins if height_no_margins > min_h else min_h
        if max_h is not math.inf and height > max_h:
            height = max_h

        self.measured_width_no_margins = width
        self.measured_height_no_margins = height

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
            margin = self.style.margin
            if margin == 0:
                self.margins_px = ZERO_DIRECTIONS
            elif type(margin) in (int, float):
                self.margins_px = (margin, margin, margin, margin)
            else:
                self.margins_px = get_directional_measure(
                    self.style.margin, max_w, max_h, "margin"
                )

            padding = self.style.padding
            if padding == 0:
                self.pads_px = ZERO_DIRECTIONS
            elif type(padding) in (int, float):
                self.pads_px = (padding, padding, padding, padding)
            else:
                self.pads_px = get_directional_measure(
                    self.style.padding, max_w, max_h, "padding"
                )

            self.spacing_px = measure_value(self.style.spacing, max_w, max_h, Axis.X)

        margined_max_w = max_w - self.margins_px[L] - self.margins_px[R]
        margined_max_h = max_h - self.margins_px[T] - self.margins_px[B]
        if margined_max_w < 0:
            margined_max_w = 0
        if margined_max_h < 0:
            margined_max_h = 0

        if not arrange_measure:
            constrained_min_w = min_w - self.margins_px[L] - self.margins_px[R]
            constrained_min_h = min_h - self.margins_px[T] - self.margins_px[B]
            if constrained_min_w < 0:
                constrained_min_w = 0
            if constrained_min_h < 0:
                constrained_min_h = 0
            constrained_max_w = math.inf
            constrained_max_h = math.inf
            if self.style.width_constraint is not None:
                if self.style.width_constraint.min is not None:
                    constrained_min_w = max(
                        constrained_min_w,
                        measure_value(
                            self.style.width_constraint.min, max_w, max_h, Axis.X
                        ),
                    )
                if self.style.width_constraint.max is not None:
                    constrained_max_w = min(
                        constrained_max_w,
                        measure_value(
                            self.style.width_constraint.max, max_w, max_h, Axis.X
                        ),
                    )
            if self.style.height_constraint is not None:
                if self.style.height_constraint.min is not None:
                    constrained_min_h = max(
                        constrained_min_h,
                        measure_value(
                            self.style.height_constraint.min, max_w, max_h, Axis.Y
                        ),
                    )
                if self.style.height_constraint.max is not None:
                    constrained_max_h = min(
                        constrained_max_h,
                        measure_value(
                            self.style.height_constraint.max, max_w, max_h, Axis.Y
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

            width_type = type(self.style.width)
            if type(self.style.width) in (int, float):
                tentative_w = self.style.width
                set_w = True
            else:
                width = SizeIntent._sizefy(self.style.width)
                width_type = type(width)

                if width_type is Exact:
                    tentative_w = width.pixels
                    set_w = True
                elif width_type is Percent:
                    tentative_w = width._measure(margined_max_w, margined_max_h, Axis.X)
                    set_w = True
                    if parent_style is not None and type(parent_style.width) is Hug:
                        raise IllegalOperation(
                            "Child with Percent width cannot be measured inside a parent with Hug width"
                        )
                elif width_type is Span:
                    tentative_w = (
                        margined_max_w - (parent_spacing * (width.count - 1))
                    ) * width.weight
                    set_w = True
                    if parent_style is not None and type(parent_style.width) is Hug:
                        raise IllegalOperation(
                            "Child with Span width cannot be measured inside a parent with Hug width"
                        )
                elif width_type is Ratio:
                    w_is_ratio = True
                elif width_type is Fill:
                    if parent_axis in (Axis.Y, None):
                        tentative_w = width.weight * margined_max_w
                        set_w = True
                    if parent_style is not None and type(parent_style.width) is Hug:
                        raise IllegalOperation(
                            "Child with Fill width cannot be measured inside a parent with Hug width"
                        )

            height_type = type(self.style.height)
            if height_type in (int, float):
                tentative_h = self.style.height
                set_h = True
            else:
                height = SizeIntent._sizefy(self.style.height)
                height_type = type(height)

                if height_type is Exact:
                    tentative_h = height.pixels
                    set_h = True
                elif height_type is Percent:
                    tentative_h = height._measure(
                        margined_max_w, margined_max_h, Axis.Y
                    )
                    set_h = True
                    if parent_style is not None and type(parent_style.height) is Hug:
                        raise IllegalOperation(
                            "Child with Percent height cannot be measured inside a parent with Hug height"
                        )
                elif height_type is Span:
                    tentative_h = (
                        margined_max_h - (parent_spacing * (height.count - 1))
                    ) * height.weight
                    set_h = True
                    if parent_style is not None and type(parent_style.height) is Hug:
                        raise IllegalOperation(
                            "Child with Span height cannot be measured inside a parent with Hug height"
                        )
                elif height_type is Ratio:
                    if not set_w:
                        raise IllegalOperation(
                            "Element with Ratio height needs a well defined width of either Exact, Percent, or Span"
                        )
                    tentative_h = tentative_w / height.ratio
                    set_h = True
                elif height_type is Fill:
                    if parent_axis in (Axis.X, None):
                        tentative_h = height.weight * margined_max_h
                        set_h = True
                    if parent_style is not None and type(parent_style.height) is Hug:
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

        inner_max_w = max_w_for_inner - self.pads_px[L] - self.pads_px[R]
        inner_max_h = max_h_for_inner - self.pads_px[T] - self.pads_px[B]
        if inner_max_w < 0:
            inner_max_w = 0
        if inner_max_h < 0:
            inner_max_h = 0

        width_paradox_fill = parent_axis == Axis.X and type(self.style.width) is Fill

        height_paradox_fill = parent_axis == Axis.Y and type(self.style.height) is Fill

        paradox_defer_measure = not arrange_measure and (
            width_paradox_fill or height_paradox_fill
        )

        if not paradox_defer_measure:
            sum_measured_width = 0
            sum_measured_height = 0
            max_measured_width = 0
            max_measured_height = 0
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
                cw, ch = child.measured_width, child.measured_height
                sum_measured_width += cw
                sum_measured_height += ch
                if cw > max_measured_width:
                    max_measured_width = cw
                if ch > max_measured_height:
                    max_measured_height = ch

        if arrange_measure:
            if width_paradox_fill:
                tentative_w = margined_max_w

            if height_paradox_fill:
                tentative_h = margined_max_h

            self.apply_measure_constrained(tentative_w, tentative_h)

        if not arrange_measure:
            biggest_intrinsic_w = 0
            biggest_intrinsic_h = 0
            if self.intrinsic_components and (
                width_type is not Fill
                or parent_axis in (Axis.Y, None)
                or self.intrinsic_components_dont_wrap()
            ):
                biggest_intrinsic_w, biggest_intrinsic_h = (
                    self.resolve_intrinsic_components()
                )

            if width_type is Hug:
                if self.style.axis == Axis.X:
                    tentative_w = sum_measured_width + self.spacing_px * max(
                        0, len(self.relative_children) - 1
                    )
                else:
                    tentative_w = max_measured_width
                tentative_w += self.pads_px[L] + self.pads_px[R]
                if biggest_intrinsic_w > tentative_w:
                    tentative_w = biggest_intrinsic_w

            if height_type is Hug:
                if self.style.axis == Axis.Y:
                    tentative_h = sum_measured_height + self.spacing_px * max(
                        0, len(self.relative_children) - 1
                    )
                else:
                    tentative_h = max_measured_height
                tentative_h += self.pads_px[T] + self.pads_px[B]
                if biggest_intrinsic_h > tentative_h:
                    tentative_h = biggest_intrinsic_h

            if width_type is Hug or height_type is Hug:
                self.apply_measure_constrained(tentative_w, tentative_h)

        if paradox_defer_measure:
            return

        for child in self.absolute_children:
            anchored_max_w = margined_max_w
            anchored_max_h = margined_max_h
            cw_is_fill = type(child.style.width) is Fill
            ch_is_fill = type(child.style.height) is Fill
            if child.style.position.left is not None:
                child.absolute_anchors[L] = measure_value(
                    child.style.position.left, margined_max_w, margined_max_h, Axis.X
                )
                if cw_is_fill:
                    anchored_max_w -= child.absolute_anchors[L]
            if child.style.position.right is not None:
                child.absolute_anchors[R] = measure_value(
                    child.style.position.right, margined_max_w, margined_max_h, Axis.X
                )
                if cw_is_fill:
                    anchored_max_w -= child.absolute_anchors[R]
            if child.style.position.top is not None:
                child.absolute_anchors[T] = measure_value(
                    child.style.position.top, margined_max_w, margined_max_h, Axis.Y
                )
                if ch_is_fill:
                    anchored_max_h -= child.absolute_anchors[T]
            if child.style.position.bottom is not None:
                child.absolute_anchors[B] = measure_value(
                    child.style.position.bottom, margined_max_w, margined_max_h, Axis.Y
                )
                if ch_is_fill:
                    anchored_max_h -= child.absolute_anchors[B]
            if child.style.position.center_x is not None:
                child.absolute_anchors[CX] = measure_value(
                    child.style.position.center_x,
                    margined_max_w,
                    margined_max_h,
                    Axis.X,
                )
            if child.style.position.center_y is not None:
                child.absolute_anchors[CY] = measure_value(
                    child.style.position.center_y,
                    margined_max_w,
                    margined_max_h,
                    Axis.Y,
                )
            if (
                child.absolute_anchors[L] is not None
                and child.absolute_anchors[R] is not None
                and (not cw_is_fill or child.style.width.weight != 1)
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
                and (not ch_is_fill or child.style.height.weight != 1)
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
            if self.intrinsic_components and not self.intrinsic_components_dont_wrap():
                _biggest_intrinsic_w, biggest_intrinsic_h = (
                    self.resolve_intrinsic_components()
                )
                if (
                    self.measured_height_no_margins < biggest_intrinsic_h
                    and type(self.style.height) is Hug
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

        if not self.relative_children and not self.absolute_children:
            self.children_overflow = (0, 0)
            self.context._node_memory[self.id] = self
            return

        remaining_w = 0
        remaining_h = 0
        total_fill_weight = 0
        used_w = 0
        used_h = 0
        children_needing_fill: list[Node] = []

        if self.style.axis == Axis.X:
            for c in self.relative_children:
                if type(c.style.width) is Fill:
                    total_fill_weight += c.style.width.weight
                    children_needing_fill.append(c)
                else:
                    used_w += c.measured_width
            used_w += self.spacing_px * max(0, len(self.relative_children) - 1)
            remaining_w = (
                self.measured_width_no_margins
                - used_w
                - self.pads_px[L]
                - self.pads_px[R]
            )
            if remaining_w < 0:
                remaining_w = 0
        else:  # Axis.Y
            for c in self.relative_children:
                if type(c.style.height) is Fill:
                    total_fill_weight += c.style.height.weight
                    children_needing_fill.append(c)
                else:
                    used_h += c.measured_height
            used_h += self.spacing_px * max(0, len(self.relative_children) - 1)
            remaining_h = (
                self.measured_height_no_margins
                - used_h
                - self.pads_px[T]
                - self.pads_px[B]
            )
            if remaining_h < 0:
                remaining_h = 0

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
                if type(self.style.height) is Hug and child.measured_height != prev_h:
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

        lastmost_opposite = 0
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
                bottom = child.relative_rect.bottom
                if bottom > lastmost_opposite:
                    lastmost_opposite = bottom
            else:
                right = child.relative_rect.right
                if right > lastmost_opposite:
                    lastmost_opposite = right

        cursor_x -= self.spacing_px
        cursor_y -= self.spacing_px
        if self.style.axis == Axis.X:
            cursor_y = lastmost_opposite
        else:
            cursor_x = lastmost_opposite
        overflow_x = cursor_x - self.relative_rect.w
        overflow_y = cursor_y - self.relative_rect.h
        self.children_overflow = (
            overflow_x if overflow_x > 0 else 0,
            overflow_y if overflow_y > 0 else 0,
        )

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
