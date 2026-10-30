import enum

import pygame

from dimi._primitives import (
    BL,
    BR,
    TL,
    TR,
    Axis,
    B,
    ChooseAxis,
    Corners,
    ImageFit,
    L,
    NinePatch,
    R,
    SizeIntent,
    T,
    anchor_rect,
    get_directional_measure,
)
from dimi._style import EllipseStyle, ImageStyle, RectStyle, TextStyle


class Component(enum.StrEnum):
    RECT = "rect"
    ELLIPSE = "ellipse"
    TEXT = "text"
    IMAGE = "image"


def image_parse_style(bounds: pygame.Rect, padding, width, height, style: ImageStyle):
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
    elif style.fit == ImageFit.STRETCH or isinstance(style.fit, NinePatch):
        scale_x = padded_rect.w / width
        scale_y = padded_rect.h / height
    fit_rect = pygame.Rect(0, 0, width * scale_x, height * scale_y)
    anchor_rect(fit_rect, padded_rect, style.anchor)
    if isinstance(style.border_radius, Corners):
        border_radius = style.border_radius
        border_radius = tuple(
            round(
                SizeIntent._sizefy(br)._measure(fit_rect.w, fit_rect.h, ChooseAxis.MIN)
            )
            for br in (
                border_radius.topleft,
                border_radius.topright,
                border_radius.bottomright,
                border_radius.bottomleft,
            )
        )
    else:
        border_radius = round(
            SizeIntent._sizefy(style.border_radius)._measure(
                fit_rect.w, fit_rect.h, ChooseAxis.MIN
            )
        )
        border_radius = (border_radius, border_radius, border_radius, border_radius)
    nine_patch_inset_size = None
    if isinstance(style.fit, NinePatch):
        nine_patch_inset_size = SizeIntent._sizefy(style.fit.inset_size)._measure(
            fit_rect.w, fit_rect.h, ChooseAxis.MIN
        )
    return fit_rect, border_radius, nine_patch_inset_size


def rect_parse_style(bounds: pygame.Rect, style: RectStyle):
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
    padded_rect.x += style.offset[0]
    padded_rect.y += style.offset[1]
    border_width = SizeIntent._sizefy(style.border_width)._measure(
        bounds.w, bounds.h, ChooseAxis.MIN
    )
    if isinstance(style.border_radius, Corners):
        border_radius = style.border_radius
        border_radius = tuple(
            round(
                SizeIntent._sizefy(br)._measure(
                    padded_rect.w, padded_rect.h, ChooseAxis.MIN
                )
            )
            for br in (
                border_radius.topleft,
                border_radius.topright,
                border_radius.bottomright,
                border_radius.bottomleft,
            )
        )
    else:
        border_radius = round(
            SizeIntent._sizefy(style.border_radius)._measure(
                padded_rect.w, padded_rect.h, ChooseAxis.MIN
            )
        )
        border_radius = (border_radius, border_radius, border_radius, border_radius)
    return padded_rect, int(border_width), border_radius


def ellipse_parse_style(bounds: pygame.Rect, style: EllipseStyle):
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
    padded_rect.x += style.offset[0]
    padded_rect.y += style.offset[1]
    border_width = SizeIntent._sizefy(style.border_width)._measure(
        bounds.w, bounds.h, ChooseAxis.MIN
    )
    return padded_rect, int(border_width)


def hit_test_rounded_rect(
    padded_rect: pygame.Rect, mouse_pos: tuple[int, int], radius: tuple
):
    if all(br == 0 for br in radius):
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
    padded_rect, border_width, radius = rect_parse_style(bounds, style)
    return hit_test_rounded_rect(padded_rect, mouse_pos, radius)


def image_hit_test(
    bounds: pygame.Rect, mouse_pos: tuple[int, int], image, style: ImageStyle, padding
):
    fit_rect, border_radius, ninepatch_inset = image_parse_style(
        bounds, padding, image.width, image.height, style
    )
    return hit_test_rounded_rect(fit_rect, mouse_pos, border_radius)


def ellipse_hit_test(
    bounds: pygame.Rect, mouse_pos: tuple[int, int], _, style: EllipseStyle
):
    padded_rect, border_width = ellipse_parse_style(bounds, style)
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
}
