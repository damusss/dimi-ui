import enum
import math

import pygame

from dimi._primitives import (
    BL,
    BR,
    TL,
    TR,
    ZERO_CORNERS,
    Axis,
    B,
    ChooseAxis,
    Corners,
    ImageFit,
    L,
    NinePatch,
    PointsOrigin,
    R,
    T,
    Transform,
    anchor_rect,
    get_directional_measure,
    measure_value,
)
from dimi._style import EllipseStyle, ImageStyle, LineStyle, RectStyle, TextStyle


class Component(enum.StrEnum):
    RECT = "rect"
    ELLIPSE = "ellipse"
    LINE = "line"
    TEXT = "text"
    IMAGE = "image"


def image_parse_style(bounds: pygame.Rect, padding, width, height, style: ImageStyle):
    if padding == 0:
        padded_rect = bounds
    else:
        padded_rect = pygame.Rect(
            bounds.x + padding[L],
            bounds.y + padding[T],
            bounds.w - padding[L] - padding[R],
            bounds.h - padding[T] - padding[B],
        )

    scale_x = 1
    scale_y = 1
    if style.fit == ImageFit.NONE:
        scale_x = scale_y = 1
    elif style.fit == ImageFit.FIT:
        scale_x = scale_y = min(padded_rect.w / width, padded_rect.h / height)
    elif style.fit == ImageFit.FIT_SCALE_DOWN:
        scale_x = scale_y = min(1, padded_rect.w / width, padded_rect.h / height)
    elif style.fit == ImageFit.FIT_WIDTH:
        scale_x = scale_y = padded_rect.w / width
    elif style.fit == ImageFit.FIT_HEIGHT:
        scale_x = scale_y = padded_rect.h / height
    elif style.fit == ImageFit.COVER:
        scale_x = scale_y = max(padded_rect.w / width, padded_rect.h / height)
    elif style.fit == ImageFit.STRETCH or type(style.fit) is NinePatch:
        scale_x = padded_rect.w / width
        scale_y = padded_rect.h / height

    fit_rect = pygame.Rect(0, 0, width * scale_x, height * scale_y)
    anchor_rect(fit_rect, padded_rect, style.anchor)

    if style.border_radius == 0:
        border_radius = ZERO_CORNERS
    elif isinstance(style.border_radius, Corners):
        border_radius = style.border_radius
        border_radius = tuple(
            round(measure_value(br, fit_rect.w, fit_rect.h, ChooseAxis.MIN))
            for br in (
                border_radius.topleft,
                border_radius.topright,
                border_radius.bottomright,
                border_radius.bottomleft,
            )
        )
    else:
        border_radius = round(
            measure_value(style.border_radius, fit_rect.w, fit_rect.h, ChooseAxis.MIN)
        )
        border_radius = (border_radius, border_radius, border_radius, border_radius)

    nine_patch_inset_size = None
    if isinstance(style.fit, NinePatch):
        nine_patch_inset_size = measure_value(
            style.fit.inset_size, fit_rect.w, fit_rect.h, ChooseAxis.MIN
        )

    return fit_rect, border_radius, nine_patch_inset_size


def image_parse_transform(
    image_w: int, image_h: int, transform: Transform | None, fit_rect: pygame.Rect
) -> tuple[pygame.Rect, float, tuple[float, float], bool, bool]:
    transformed_rect = fit_rect

    if transform is not None:
        angle = transform.angle_deg
        flip_x = transform.flip_x
        flip_y = transform.flip_y
        angle_origin = transform.angle_origin
        if transform.scale_origin is None:
            scale_origin = (image_w / 2, image_h / 2)
        else:
            scale_origin = transform.scale_origin
        transformed_rect = pygame.Rect(
            fit_rect.x
            + scale_origin[0] * (fit_rect.w / image_w) * (1 - transform.scale[0])
            + transform.offset[0],
            fit_rect.y
            + scale_origin[1] * (fit_rect.h / image_h) * (1 - transform.scale[1])
            + transform.offset[1],
            fit_rect.w * transform.scale[0],
            fit_rect.h * transform.scale[1],
        )
        if angle_origin is None:
            angle_origin = (transformed_rect.w / 2, transformed_rect.h / 2)
        else:
            angle_origin = (
                angle_origin[0] * (transformed_rect.w / image_w),
                angle_origin[1] * (transformed_rect.h / image_h),
            )

    else:
        angle = 0
        flip_x = flip_y = False
        angle_origin = (transformed_rect.w / 2, transformed_rect.h / 2)

    return transformed_rect, angle, angle_origin, flip_x, flip_y


def image_repeat_translate_angle(
    original: pygame.Rect, translated: pygame.Rect, angle: float
) -> pygame.Rect:
    if angle == 0:
        return translated
    ox, oy = translated.center
    gx, gy = original.center
    angle_rad = math.radians(angle)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    rotated_x = cos_a * (ox - gx) - sin_a * (oy - gy) + gx
    rotated_y = sin_a * (ox - gx) + cos_a * (oy - gy) + gy
    return translated.move_to(center=(rotated_x, rotated_y))


def rect_parse_style(bounds: pygame.Rect, style: RectStyle):
    if style.padding == 0:
        padded_rect = bounds
    else:
        padding = get_directional_measure(style.padding, bounds.w, bounds.h, "padding")
        padded_rect = pygame.Rect(
            bounds.x + padding[L],
            bounds.y + padding[T],
            bounds.w - padding[L] - padding[R],
            bounds.h - padding[T] - padding[B],
        )

    if style.aspect_ratio != 0:
        control = Axis.X
        aspect = style.aspect_ratio
        dofit = True
        if isinstance(style.aspect_ratio, tuple):
            aspect, control, dofit = style.aspect_ratio
        aspect_rect = padded_rect.copy()
        if control == Axis.X:
            aspect_rect.h = aspect_rect.w / aspect
        else:
            aspect_rect.w = aspect_rect.h * aspect
        if dofit:
            aspect_rect = aspect_rect.fit(padded_rect)
        anchor_rect(aspect_rect, padded_rect, style.anchor)
        padded_rect = aspect_rect

    if style.offset != (0, 0):
        padded_rect = padded_rect.move(style.offset)

    if style.border_width != 0:
        border_width = measure_value(
            style.border_width, bounds.w, bounds.h, ChooseAxis.MIN
        )
    else:
        border_width = 0

    if style.border_radius == 0:
        border_radius = ZERO_CORNERS
    elif isinstance(style.border_radius, Corners):
        border_radius = style.border_radius
        border_radius = tuple(
            round(measure_value(br, padded_rect.w, padded_rect.h, ChooseAxis.MIN))
            for br in (
                border_radius.topleft,
                border_radius.topright,
                border_radius.bottomright,
                border_radius.bottomleft,
            )
        )
    else:
        border_radius = round(
            measure_value(
                style.border_radius, padded_rect.w, padded_rect.h, ChooseAxis.MIN
            )
        )
        border_radius = (border_radius, border_radius, border_radius, border_radius)

    return padded_rect, int(border_width), border_radius


def line_parse_style(
    bounds: pygame.Rect, start_end: tuple[tuple, tuple], style: LineStyle
) -> tuple[tuple[float, float], tuple[float, float], float]:
    line_size = measure_value(style.size, bounds.w, bounds.h, ChooseAxis.MIN)

    if style.padding == 0:
        padded_rect = bounds
    else:
        padding = get_directional_measure(style.padding, bounds.w, bounds.h, "padding")
        padded_rect = pygame.Rect(
            bounds.x + padding[L],
            bounds.y + padding[T],
            bounds.w - padding[L] - padding[R],
            bounds.h - padding[T] - padding[B],
        )

    if style.offset != (0, 0):
        padded_rect = padded_rect.move(style.offset)

    if style.points_origin == PointsOrigin.CENTER:
        x_100, y_100 = padded_rect.w / 2, padded_rect.h / 2
        origin_x, origin_y = x_100, y_100
    elif style.points_origin == PointsOrigin.TOPLEFT:
        x_100, y_100 = padded_rect.size
        origin_x = origin_y = 0
    else:
        raise ValueError(f"Unrecognized points_origin value '{style.points_origin}'")

    points = []
    for point in start_end:
        px = measure_value(point[0], x_100, y_100, Axis.X)
        py = measure_value(point[1], x_100, y_100, Axis.Y)
        points.append((padded_rect.x + origin_x + px, padded_rect.y + origin_y + py))

    return (
        points[0],
        points[1],
        line_size,
    )


def ellipse_parse_style(bounds: pygame.Rect, style: EllipseStyle):
    if style.padding == 0:
        padded_rect = bounds
    else:
        padding = get_directional_measure(style.padding, bounds.w, bounds.h, "padding")
        padded_rect = pygame.Rect(
            bounds.x + padding[L],
            bounds.y + padding[T],
            bounds.w - padding[L] - padding[R],
            bounds.h - padding[T] - padding[B],
        )

    if style.aspect_ratio != 0:
        control = Axis.X
        aspect = style.aspect_ratio
        dofit = True
        if isinstance(style.aspect_ratio, tuple):
            aspect, control, dofit = style.aspect_ratio
        aspect_rect = padded_rect.copy()
        if control == Axis.X:
            aspect_rect.h = aspect_rect.w / aspect
        else:
            aspect_rect.w = aspect_rect.h * aspect
        if dofit:
            aspect_rect = aspect_rect.fit(padded_rect)
        anchor_rect(aspect_rect, padded_rect, style.anchor)
        padded_rect = aspect_rect

    if style.offset != (0, 0):
        padded_rect = padded_rect.move(style.offset)

    if style.border_width != 0:
        border_width = measure_value(
            style.border_width, bounds.w, bounds.h, ChooseAxis.MIN
        )
    else:
        border_width = 0

    return padded_rect, int(border_width)


def hit_test_rounded_rect(
    padded_rect: pygame.Rect, mouse_pos: tuple[int, int], radius: tuple
):
    if radius == ZERO_CORNERS:
        return padded_rect.collidepoint(mouse_pos)
    for body_rect in (
        (
            pygame.Rect(
                padded_rect.x + radius[TL],
                padded_rect.y,
                padded_rect.w - radius[TL] - radius[TR],
                padded_rect.h / 2,
            )
            if padded_rect.w - radius[TL] - radius[TR] > 0
            else None
        ),
        (
            pygame.Rect(
                padded_rect.x + radius[BL],
                padded_rect.bottom - padded_rect.h / 2,
                padded_rect.w - radius[BL] - radius[BR],
                padded_rect.h / 2,
            )
            if padded_rect.w - radius[BL] - radius[BR] > 0
            else None
        ),
        (
            pygame.Rect(
                padded_rect.x,
                padded_rect.y + radius[TL],
                padded_rect.w / 2,
                padded_rect.h - radius[TL] - radius[BL],
            )
            if padded_rect.h - radius[TL] - radius[BL] > 0
            else None
        ),
        (
            pygame.Rect(
                padded_rect.right - padded_rect.w / 2,
                padded_rect.y + radius[TR],
                padded_rect.w / 2,
                padded_rect.h - radius[TR] - radius[BR],
            )
            if padded_rect.h - radius[TR] - radius[BR] > 0
            else None
        ),
    ):
        if body_rect is not None and body_rect.collidepoint(mouse_pos):
            return True
    for center, rad in (
        ((padded_rect.x + radius[TL], padded_rect.y + radius[TL]), radius[TL]),
        ((padded_rect.right - radius[TR], padded_rect.y + radius[TR]), radius[TR]),
        ((padded_rect.x + radius[BL], padded_rect.bottom - radius[BL]), radius[BL]),
        ((padded_rect.right - radius[BR], padded_rect.bottom - radius[BR]), radius[BR]),
    ):
        if (
            (mouse_pos[0] - center[0]) ** 2 + (mouse_pos[1] - center[1]) ** 2
        ) <= rad**2:
            return True
    return False


def rect_hit_test(bounds: pygame.Rect, mouse_pos: tuple[int, int], _, style: RectStyle):
    padded_rect, _border_width, radius = rect_parse_style(bounds, style)
    return hit_test_rounded_rect(padded_rect, mouse_pos, radius)


def image_hit_test(
    bounds: pygame.Rect, mouse_pos: tuple[int, int], image, style: ImageStyle, padding
):
    fit_rect, border_radius, _ninepatch_inset = image_parse_style(
        bounds, padding, image.width, image.height, style
    )
    return hit_test_rounded_rect(fit_rect, mouse_pos, border_radius)


def ellipse_hit_test(
    bounds: pygame.Rect, mouse_pos: tuple[int, int], _, style: EllipseStyle
):
    padded_rect, _border_width = ellipse_parse_style(bounds, style)
    return (
        (((mouse_pos[0] - padded_rect.centerx) ** 2) / ((padded_rect.w / 2) ** 2))
        + (((mouse_pos[1] - padded_rect.centery) ** 2) / ((padded_rect.h / 2) ** 2))
    ) <= 1


SHAPE_HIT_TEST_CALLBACKS = {
    Component.RECT: rect_hit_test,
    Component.ELLIPSE: ellipse_hit_test,
    Component.IMAGE: image_hit_test,
}

DEFAULT_COMPONENT_STYLE_CLASSES = {
    Component.RECT: RectStyle,
    Component.ELLIPSE: EllipseStyle,
    Component.TEXT: TextStyle,
    Component.IMAGE: ImageStyle,
    Component.LINE: LineStyle,
}
