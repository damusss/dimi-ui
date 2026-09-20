import math
import typing
import warnings
from abc import ABC, abstractmethod

import pygame
from pygame import _render

from dimi._primitives import (
    SizeIntent,
    Axis,
    Font,
    ScaleQuality,
    ImageRepeat,
    L,
    T,
    B,
    R,
    TL,
    BL,
    BR,
    TR,
    get_directional_measure,
    anchor_rect,
)
from dimi._style import RectStyle, EllipseStyle, TextStyle, ImageStyle
from dimi._components import (
    Component,
    rect_parse_style,
    ellipse_parse_style,
    image_parse_style,
)
from dimi._error import IllegalOperation


class Canvas(ABC):
    __module__ = "dimi.typehinting"

    def __init__(self):
        self._component_render_methods: dict[str, typing.Callable] = {}
        self._fonts: dict[tuple[str, bool, bool, bool] | None, pygame.Font] = {}

    def _get_font(self, font: Font | None):
        if font is None:
            if None in self._fonts:
                return self._fonts[None]
            font = pygame.Font()
            self._fonts[None] = font
            return font
        font_key = (font.name, font.is_sysfont, font.sysfont_bold, font.sysfont_italic)
        if font_key in self._fonts:
            return self._fonts[font_key]
        if font.is_sysfont:
            font = pygame.font.SysFont(
                font.name, 16, font.sysfont_bold, font.sysfont_italic
            )
        else:
            font = pygame.Font(font.name, 16)
        self._fonts[font_key] = font
        return font

    def _create_text_render(
        self, text: str, style: TextStyle, wrap_width: int, height: int
    ):
        padding = get_directional_measure(style.padding, wrap_width, height, "padding")
        available_h = height - padding[T] - padding[B]
        if style.font is None or isinstance(style.font, Font):
            font: pygame.Font = self._get_font(style.font)
            if style.size is None:
                raise IllegalOperation(
                    "When a manual pygame.Font isn't specified the size style must not be None"
                )
        else:
            font: pygame.Font = style.font
        if style.size is not None:
            size = max(
                1,
                int(
                    SizeIntent._sizefy(style.size)._measure(
                        wrap_width, available_h, Axis.Y
                    )
                ),
            )
            font.point_size = size
        else:
            size = font.point_size
        outline_width = int(
            SizeIntent._sizefy(style.outline_width)._measure(wrap_width, size, Axis.Y)
        )
        if outline_width != 0:
            padding = (
                padding[0] - outline_width,
                padding[1] - outline_width,
                padding[2] - outline_width,
                padding[3] - outline_width,
            )

        if int(style.align) != font.align:
            font.align = int(style.align)
        font.set_direction(int(style.direction))
        if style.line_skip is not None:
            font.set_linesize(
                SizeIntent._sizefy(style.line_skip)._measure(wrap_width, size, Axis.Y)
            )
        if style.italic != font.italic:
            font.italic = style.italic
        if style.bold != font.bold:
            font.bold = style.bold
        if style.underline != font.underline:
            font.underline = style.underline
        if style.strikethrough != font.strikethrough:
            font.strikethrough = style.strikethrough

        if wrap_width != 0:
            wrap_width -= padding[L] + padding[R]

        render_wrap_width = wrap_width
        longest_line = None
        if wrap_width != 0:
            longest_line = max(font.size(line)[0] for line in text.split("\n"))

        outline_surface = None
        surface = None
        if outline_width != 0:
            font.outline = outline_width
            outline_surface = font.render(
                text,
                style.antialias,
                style.outline_color,
                None,
                int(render_wrap_width),
            )
            if style.background_color is not None:
                temp = pygame.Surface(outline_surface.size, pygame.SRCALPHA)
                temp.fill(style.background_color)
                temp.blit(outline_surface)
                outline_surface = temp
            if (
                longest_line is not None
                and longest_line + outline_width * 2 < outline_surface.width
            ):
                temp = pygame.Surface(
                    (longest_line + outline_width * 2, outline_surface.height),
                    pygame.SRCALPHA,
                )
                blit_dest = 0
                if font.align == pygame.FONT_CENTER:
                    blit_dest = -(
                        outline_surface.width / 2
                        - (longest_line + outline_width * 2) / 2
                    )
                if font.align == pygame.FONT_RIGHT:
                    blit_dest = -(
                        outline_surface.width - (longest_line + outline_width * 2)
                    )
                temp.blit(outline_surface, (blit_dest, 0))
                outline_surface = temp
            font.outline = 0

        if style.color is not None:
            surface = font.render(
                text,
                style.antialias,
                style.color,
                None if outline_width != 0 else style.background_color,
                int(render_wrap_width),
            )
            if longest_line is not None and longest_line < surface.width:
                temp = pygame.Surface((longest_line, surface.height), pygame.SRCALPHA)
                blit_dest = 0
                if font.align == pygame.FONT_CENTER:
                    blit_dest = -(surface.width / 2 - longest_line / 2)
                if font.align == pygame.FONT_RIGHT:
                    blit_dest = -(surface.width - longest_line)
                temp.blit(surface, (blit_dest, 0))
                surface = temp
            if outline_surface is not None:
                outline_surface.blit(surface, (outline_width, outline_width))
                surface = outline_surface
        else:
            if outline_surface is not None:
                surface = outline_surface
            else:
                raise IllegalOperation(
                    "The text color can only be None if the outline width is not zero."
                )

        return surface, surface.get_rect(), padding

    @property
    @abstractmethod
    def viewport(self) -> pygame.Rect:
        pass

    @viewport.setter
    @abstractmethod
    def viewport(self, value):
        pass

    @abstractmethod
    def _get_render_rect(
        self, absolute_rect: pygame.Rect, viewport: pygame.Rect
    ) -> pygame.Rect:
        pass

    @abstractmethod
    def _render_start(self): ...

    @abstractmethod
    def _render_end(self): ...

    @abstractmethod
    def _resolve_text(
        self, cache_key: int, text: str, style: TextStyle, wrap_width: int, height: int
    ) -> tuple[int, int]: ...


class RendererCanvas(Canvas):
    __module__ = "dimi"

    def __init__(self, renderer: _render.Renderer):
        super().__init__()
        self.renderer = renderer
        self._component_render_methods = {
            Component.RECT: self._render_rect,
            Component.ELLIPSE: self._render_ellipse,
            Component.TEXT: self._render_text,
            Component.IMAGE: self._render_image,
        }
        self._corners_mask_blend_mode = self.renderer.compose_custom_blend_mode(
            (
                pygame.BLENDFACTOR_ZERO,
                pygame.BLENDFACTOR_SRC_ALPHA,
                pygame.BLENDOPERATION_ADD,
            ),
            (
                pygame.BLENDFACTOR_ZERO,
                pygame.BLENDFACTOR_SRC_ALPHA,
                pygame.BLENDOPERATION_ADD,
            ),
        )
        self._cached_circle_corners: dict[tuple[int, int, bool], _render.Texture] = {}
        self._cached_ellipse_corners: dict[
            tuple[int, int, int, bool], _render.Texture
        ] = {}
        self._pinged_circle_corners: set[tuple[int, int, bool]] = set()
        self._pinged_ellipse_corners: set[tuple[int, int, int, bool]] = set()
        self._cached_text: dict[int, tuple[_render.Texture, pygame.Rect, tuple]] = {}
        self._pinged_text_cache_keys: set[int] = set()
        self._cached_radius_image_layers: dict[
            tuple[int, int, tuple], tuple[_render.Texture, list[_render.Texture]]
        ] = {}
        self._pinged_radius_image_layers: set[tuple[int, int, tuple]] = set()

    @property
    def viewport(self) -> pygame.Rect:
        return self.renderer.get_viewport()

    @viewport.setter
    def viewport(self, value: pygame.typing.RectLike):
        self.renderer.set_viewport(value)

    def _get_render_rect(
        self, absolute_rect: pygame.Rect, viewport: pygame.Rect
    ) -> pygame.Rect:
        return absolute_rect.move(-viewport.x, -viewport.y)

    def _render_start(self):
        self._pinged_circle_corners: set[tuple[int, int, bool]] = set(
            self._cached_circle_corners.keys()
        )
        self._pinged_ellipse_corners = set(self._cached_ellipse_corners.keys())
        self._pinged_text_cache_keys = set(self._cached_text.keys())
        self._pinged_radius_image_layers = set(self._cached_radius_image_layers.keys())

    def _render_end(self):
        for key in self._pinged_circle_corners:
            self._cached_circle_corners.pop(key)
        for key in self._pinged_ellipse_corners:
            self._cached_ellipse_corners.pop(key)
        for key in self._pinged_text_cache_keys:
            self._cached_text.pop(key)
        for key in self._pinged_radius_image_layers:
            self._cached_radius_image_layers.pop(key)

    def _render_image(
        self, bounds: pygame.Rect, image: _render.Texture, style: ImageStyle, padding
    ):
        if not isinstance(image, _render.Texture):
            if isinstance(image, pygame.Surface):
                raise TypeError(
                    "A Renderer canvas can only draw Texture objects. Convert any Surface to a Texture before using it."
                )
            else:
                raise TypeError("A Renderer canvas can only draw Texture objects.")

        fit_rect, border_radius, ninepatch_inset = image_parse_style(
            bounds, padding, image.width, image.height, style
        )

        transformed_rect = fit_rect

        if style.transform is not None:
            angle = style.transform.angle_deg
            flip_x = style.transform.flip_x
            flip_y = style.transform.flip_y
            angle_origin = style.transform.angle_origin
            if style.transform.scale_origin is None:
                scale_origin = (image.width / 2, image.height / 2)
            else:
                scale_origin = style.transform.scale_origin
            transformed_rect = pygame.Rect(
                fit_rect.x
                + scale_origin[0]
                * (fit_rect.w / image.width)
                * (1 - style.transform.scale[0])
                + style.transform.offset[0],
                fit_rect.y
                + scale_origin[1]
                * (fit_rect.h / image.height)
                * (1 - style.transform.scale[1])
                + style.transform.offset[1],
                fit_rect.w * style.transform.scale[0],
                fit_rect.h * style.transform.scale[1],
            )
            if angle_origin is not None:
                angle_origin = (
                    angle_origin[0] * (transformed_rect.w / image.width),
                    angle_origin[1] * (transformed_rect.h / image.height),
                )
            else:
                angle_origin = (transformed_rect.w / 2, transformed_rect.h / 2)
        else:
            angle = 0
            flip_x = flip_y = False
            angle_origin = (transformed_rect.w / 2, transformed_rect.h / 2)

        if style.scale_quality is not None:
            warnings.warn(
                "Before pygame 3+ it is not possible to dynamically change a Texture's scale quality. Modify it through the Texture constructor or wait for pygame to be upgraded.",
                RuntimeWarning,
            )

        drawing_image = image

        if any(br != 0 for br in border_radius):
            radius_key = (fit_rect.w, fit_rect.h, border_radius)
            if radius_key not in self._cached_radius_image_layers:
                layer_tex = _render.Texture(
                    self.renderer,
                    fit_rect.size,
                    32,
                    target=True,
                    scale_quality=0
                    if style.scale_quality == ScaleQuality.NEAREST
                    else 1,
                )  # todo PG3 remove scale quality parameter, use the later setting
                layer_tex.blend_mode = pygame.BLENDMODE_BLEND
                corners = []
                for rad in border_radius:
                    surf = pygame.Surface((rad, rad), pygame.SRCALPHA)
                    surf.fill((255, 255, 255, 0))
                    draw_function = (
                        pygame.draw.circle
                        if style.scale_quality == ScaleQuality.NEAREST
                        else pygame.draw.aacircle
                    )
                    draw_function(surf, "white", (rad, rad), rad, draw_top_left=True)
                    corner_tex = _render.Texture(
                        self.renderer,
                        surf.size,
                        32,
                        scale_quality=0
                        if (style.scale_quality == ScaleQuality.NEAREST)
                        else 1,
                    )
                    corner_tex.update(surf)
                    corner_tex.blend_mode = self._corners_mask_blend_mode
                    corners.append(corner_tex)
                self._cached_radius_image_layers[radius_key] = layer_tex, corners
            self._pinged_radius_image_layers.discard(radius_key)
            layer_texture, corner_textures = self._cached_radius_image_layers[
                radius_key
            ]
            # todo change the corners scale quality to the image's
            restore_target = self.renderer.target
            self.renderer.target = layer_texture
            self.renderer.draw_color = (255, 255, 255, 0)
            self.renderer.clear()
            self._render_texture(
                image,
                pygame.Rect(0, 0, fit_rect.w, fit_rect.h),
                ninepatch_inset,
                0,
                None,
                flip_x,
                flip_y,
            )
            flip_x = flip_y = False
            ninepatch_inset = None
            corner_textures[TL].draw(None, (0, 0, border_radius[TL], border_radius[TL]))
            corner_textures[TR].draw(
                None,
                (
                    fit_rect.w - border_radius[TR],
                    0,
                    border_radius[TR],
                    border_radius[TR],
                ),
                flip_x=True,
            )
            corner_textures[BL].draw(
                None,
                (
                    0,
                    fit_rect.h - border_radius[BL],
                    border_radius[BL],
                    border_radius[BL],
                ),
                flip_y=True,
            )
            corner_textures[BR].draw(
                None,
                (
                    fit_rect.w - border_radius[BR],
                    fit_rect.h - border_radius[BR],
                    border_radius[BR],
                    border_radius[BR],
                ),
                flip_x=True,
                flip_y=True,
            )
            self.renderer.target = restore_target
            drawing_image = layer_texture

        restore_blend_mode = None
        restore_color = None
        restore_alpha = None

        if style.blend_mode is not None:
            restore_blend_mode = drawing_image.blend_mode
            drawing_image.blend_mode = style.blend_mode
        if style.color_modifier is not None:
            restore_color = drawing_image.color
            drawing_image.color = style.color_modifier
        if style.alpha_modifier is not None:
            restore_alpha = drawing_image.alpha
            drawing_image.alpha = style.alpha_modifier

        self._render_texture(
            drawing_image,
            transformed_rect,
            ninepatch_inset,
            angle,
            angle_origin,
            flip_x,
            flip_y,
        )
        if style.repeat in (ImageRepeat.X, ImageRepeat.BOTH):
            self._repeat_image_x(
                drawing_image,
                bounds,
                transformed_rect,
                angle,
                angle_origin,
                flip_x,
                flip_y,
                ninepatch_inset,
                style.repeat,
            )
        if style.repeat in (ImageRepeat.Y, ImageRepeat.BOTH):
            self._repeat_image_y(
                drawing_image,
                bounds,
                transformed_rect,
                0,
                angle,
                angle_origin,
                flip_x,
                flip_y,
                ninepatch_inset,
            )

        if restore_blend_mode:
            drawing_image.blend_mode = restore_blend_mode
        if restore_color:
            drawing_image.color = restore_color
        if restore_alpha:
            drawing_image.alpha = restore_alpha

    def _repeat_angle(self, original: pygame.Rect, translated: pygame.Rect, angle):
        if angle == 0:
            return translated
        ox, oy = translated.center
        gx, gy = original.center
        angle_rad = math.radians(angle)
        rotated_x = (
            math.cos(angle_rad) * (ox - gx) - math.sin(angle_rad) * (oy - gy) + gx
        )
        rotated_y = (
            math.sin(angle_rad) * (ox - gx) + math.cos(angle_rad) * (oy - gy) + gy
        )
        return translated.move_to(center=(rotated_x, rotated_y))

    def _repeat_image_x(
        self,
        image,
        bounds,
        transformed_rect,
        angle,
        angle_origin,
        flip_x,
        flip_y,
        patch_size,
        repeat,
    ):
        if angle != 0:
            diagonal = math.sqrt(bounds.w**2 + bounds.h**2)
            space_left_rect = pygame.Rect(0, 0, diagonal, diagonal).move_to(
                center=bounds.center
            )
        else:
            space_left_rect = bounds
        left_space = transformed_rect.x - space_left_rect.x
        if left_space > 0:
            left_amount = int(left_space / transformed_rect.w) + 1
            cursor = -transformed_rect.w * left_amount
            for i in range(left_amount):
                self._render_texture(
                    image,
                    self._repeat_angle(
                        transformed_rect, transformed_rect.move(cursor, 0), angle
                    ),
                    patch_size,
                    angle,
                    angle_origin,
                    flip_x,
                    flip_y,
                )
                if repeat == ImageRepeat.BOTH:
                    self._repeat_image_y(
                        image,
                        bounds,
                        transformed_rect,
                        cursor,
                        angle,
                        angle_origin,
                        flip_x,
                        flip_y,
                        patch_size,
                    )
                cursor += transformed_rect.w
                if transformed_rect.x + cursor > space_left_rect.right:
                    break
        right_space = space_left_rect.right - transformed_rect.right
        if right_space > 0:
            right_amount = int(right_space / transformed_rect.w) + 1
            cursor = transformed_rect.w * right_amount
            for i in range(right_amount):
                self._render_texture(
                    image,
                    self._repeat_angle(
                        transformed_rect, transformed_rect.move(cursor, 0), angle
                    ),
                    patch_size,
                    angle,
                    angle_origin,
                    flip_x,
                    flip_y,
                )
                if repeat == ImageRepeat.BOTH:
                    self._repeat_image_y(
                        image,
                        bounds,
                        transformed_rect,
                        cursor,
                        angle,
                        angle_origin,
                        flip_x,
                        flip_y,
                        patch_size,
                    )
                cursor -= transformed_rect.w
                if transformed_rect.x + cursor + transformed_rect.w < space_left_rect.x:
                    break

    def _repeat_image_y(
        self,
        image,
        bounds,
        transformed_rect,
        cursor_x,
        angle,
        angle_origin,
        flip_x,
        flip_y,
        patch_size,
    ):
        if angle != 0:
            diagonal = math.sqrt(bounds.w**2 + bounds.h**2)
            space_left_rect = pygame.Rect(0, 0, diagonal, diagonal).move_to(
                center=bounds.center
            )
        else:
            space_left_rect = bounds
        top_space = transformed_rect.y - space_left_rect.y
        if top_space > 0:
            top_amount = int(top_space / transformed_rect.h) + 1
            cursor = -transformed_rect.h * top_amount
            for i in range(top_amount):
                self._render_texture(
                    image,
                    self._repeat_angle(
                        transformed_rect, transformed_rect.move(cursor_x, cursor), angle
                    ),
                    patch_size,
                    angle,
                    angle_origin,
                    flip_x,
                    flip_y,
                )
                cursor += transformed_rect.h
                if transformed_rect.y + cursor > space_left_rect.bottom:
                    break
        bottom_space = space_left_rect.bottom - transformed_rect.bottom
        if bottom_space > 0:
            bottom_amount = int(bottom_space / transformed_rect.h) + 1
            cursor = transformed_rect.h * bottom_amount
            for i in range(bottom_amount):
                self._render_texture(
                    image,
                    self._repeat_angle(
                        transformed_rect, transformed_rect.move(cursor_x, cursor), angle
                    ),
                    patch_size,
                    angle,
                    angle_origin,
                    flip_x,
                    flip_y,
                )
                cursor -= transformed_rect.h
                if transformed_rect.y + cursor + transformed_rect.h < space_left_rect.y:
                    break

    def _render_texture(
        self,
        image: _render.Texture,
        rect: pygame.Rect,
        patch_size: int | None,
        angle,
        angle_origin: pygame.typing.Point | None,
        flip_x,
        flip_y,
    ):
        if patch_size is None:
            image.draw(None, rect, angle, angle_origin, flip_x, flip_y)
            return
        w, h = image.width, image.height
        tl_r = pygame.Rect(rect.x, rect.y, patch_size, patch_size)
        tl_s = pygame.Rect(0, 0, patch_size, patch_size)
        tr_r = pygame.Rect(rect.right - patch_size, rect.y, patch_size, patch_size)
        tr_s = pygame.Rect(w - patch_size, 0, patch_size, patch_size)
        bl_r = pygame.Rect(rect.x, rect.bottom - patch_size, patch_size, patch_size)
        bl_s = pygame.Rect(0, h - patch_size, patch_size, patch_size)
        br_r = pygame.Rect(
            rect.right - patch_size, rect.bottom - patch_size, patch_size, patch_size
        )
        br_s = pygame.Rect(w - patch_size, h - patch_size, patch_size, patch_size)
        l_r = pygame.Rect(
            rect.x, rect.y + patch_size, patch_size, rect.h - patch_size * 2
        )
        l_s = pygame.Rect(0, patch_size, patch_size, h - patch_size * 2)
        r_r = pygame.Rect(
            rect.right - patch_size,
            rect.y + patch_size,
            patch_size,
            rect.h - patch_size * 2,
        )
        r_s = pygame.Rect(w - patch_size, patch_size, patch_size, h - patch_size * 2)
        t_r = pygame.Rect(
            rect.x + patch_size, rect.y, rect.w - patch_size * 2, patch_size
        )
        t_s = pygame.Rect(patch_size, 0, w - patch_size * 2, patch_size)
        b_r = pygame.Rect(
            rect.x + patch_size,
            rect.bottom - patch_size,
            rect.w - patch_size * 2,
            patch_size,
        )
        b_s = pygame.Rect(patch_size, h - patch_size, w - patch_size * 2, patch_size)
        c_r = pygame.Rect(
            rect.x + patch_size,
            rect.y + patch_size,
            rect.w - patch_size * 2,
            rect.h - patch_size * 2,
        )
        c_s = pygame.Rect(
            patch_size, patch_size, w - patch_size * 2, h - patch_size * 2
        )
        if flip_x:
            tl_r.right = rect.right
            tr_r.x = rect.x
            bl_r.right = rect.right
            br_r.x = rect.x
            l_r.right = rect.right
            r_r.x = rect.x
        if flip_y:
            tl_r.bottom = rect.bottom
            tr_r.bottom = rect.bottom
            bl_r.y = rect.y
            br_r.y = rect.y
            t_r.bottom = rect.bottom
            b_r.y = rect.y
        for sr, dr in zip(
            (tl_s, tr_s, bl_s, br_s, l_s, r_s, t_s, b_s, c_s),
            (tl_r, tr_r, bl_r, br_r, l_r, r_r, t_r, b_r, c_r),
        ):
            if sr.w == 0 or sr.h == 0 or dr.w == 0 or dr.h == 0:
                continue
            origin = angle_origin
            if angle != 0:
                origin = (
                    angle_origin[0] - (dr.x - rect.x),
                    angle_origin[1] - (dr.y - rect.y),
                )
            image.draw(sr, dr, angle, origin, flip_x, flip_y)

    def _resolve_text(
        self, cache_key: int, text: str, style: TextStyle, wrap_width: int, height: int
    ) -> tuple[int, int]:
        if cache_key in self._cached_text:
            texture, rect, padding = self._cached_text[cache_key]
            return (rect.w + padding[L] + padding[R], rect.h + padding[T] + padding[B])
        surface, rect, padding = self._create_text_render(
            text, style, wrap_width, height
        )
        texture = _render.Texture(
            self.renderer, surface.size, 32, scale_quality=1 if style.antialias else 0
        )
        texture.update(surface)
        texture.blend_mode = pygame.BLENDMODE_BLEND
        self._cached_text[cache_key] = (texture, rect, padding)
        return (rect.w + padding[L] + padding[R], rect.h + padding[T] + padding[B])

    def _render_text(
        self, bounds: pygame.Rect, text: str, style: TextStyle, cache_key: int
    ):
        if cache_key not in self._cached_text:
            raise RuntimeError(
                "Internal error: text was not resolved during the two passes (cached text not found during render pass)"
            )
        texture, rect, padding = self._cached_text[cache_key]
        padded_rect = pygame.Rect(
            bounds.x + padding[L],
            bounds.y + padding[T],
            bounds.w - padding[L] - padding[R],
            bounds.h - padding[T] - padding[B],
        )
        padded_rect.x += style.offset[0]
        padded_rect.y += style.offset[1]
        anchor_rect(rect, padded_rect, style.anchor)
        texture.draw(None, rect)
        self._pinged_text_cache_keys.discard(cache_key)

    def _get_circle_corner(self, bw_br_antialias) -> _render.Texture:
        bw, br, antialias = bw_br_antialias
        br = max(1, br)
        bw = max(0, bw)
        if bw_br_antialias not in self._cached_circle_corners:
            surf = pygame.Surface((br, br), pygame.SRCALPHA)
            surf.fill((255, 255, 255, 0))
            draw_function = pygame.draw.aacircle if antialias else pygame.draw.circle
            draw_function(surf, (255, 255, 255, 255), (br, br), br, bw)
            tex = _render.Texture(
                self.renderer, surf.size, 32, scale_quality=1 if antialias else 0
            )
            tex.update(surf)
            tex.blend_mode = pygame.BLENDMODE_BLEND
            self._cached_circle_corners[bw_br_antialias] = tex
        self._pinged_circle_corners.discard(bw_br_antialias)
        return self._cached_circle_corners[bw_br_antialias]

    def _get_ellipse_quarter(self, qw_qh_bw_antialias) -> _render.Texture:
        qw, qh, bw, antialias = qw_qh_bw_antialias
        bw = max(0, bw)
        if qw_qh_bw_antialias not in self._cached_ellipse_corners:
            if qw == qh:
                surf = pygame.Surface((qw, qh), pygame.SRCALPHA)
                surf.fill((255, 255, 255, 0))
                draw_function = (
                    pygame.draw.aacircle if antialias else pygame.draw.circle
                )
                draw_function(surf, (255, 255, 255, 255), (qw, qh), qw, bw)
                tex = _render.Texture(
                    self.renderer, surf.size, 32, scale_quality=1 if antialias else 0
                )
                tex.update(surf)
                tex.blend_mode = pygame.BLENDMODE_BLEND
                self._cached_ellipse_corners[qw_qh_bw_antialias] = tex
            else:
                mult = 1
                if antialias:
                    mult = 4
                surf = pygame.Surface((qw * mult, qh * mult), pygame.SRCALPHA)
                surf.fill((255, 255, 255, 0))
                pygame.draw.ellipse(
                    surf, (255, 255, 255, 255), (0, 0, qw * 2 * mult, qh * 2 * mult), bw
                )
                if mult != 1:
                    surf = pygame.transform.smoothscale_by(surf, 1 / mult)
                tex = _render.Texture(
                    self.renderer, surf.size, 32, scale_quality=1 if antialias else 0
                )
                tex.update(surf)
                tex.blend_mode = pygame.BLENDMODE_BLEND
                self._cached_ellipse_corners[qw_qh_bw_antialias] = tex
        self._pinged_ellipse_corners.discard(qw_qh_bw_antialias)
        return self._cached_ellipse_corners[qw_qh_bw_antialias]

    # todo: draw a vertical and horizontal line avoiding middle line gaps
    def _render_ellipse(self, bounds: pygame.Rect, _, style: EllipseStyle):
        if style.color is None:
            return
        padded_rect, border_width = ellipse_parse_style(bounds, style)
        if padded_rect.w == 0 or padded_rect.h == 0:
            return
        quarter_w, quarter_h = round(padded_rect.w / 2), round(padded_rect.h / 2)
        quarter = self._get_ellipse_quarter(
            (quarter_w, quarter_h, border_width, style.antialias)
        )
        quarter.color = style.color
        quarter.draw(None, (padded_rect.x, padded_rect.y, quarter_w, quarter_h))
        quarter.draw(
            None,
            (padded_rect.right - quarter_w, padded_rect.y, quarter_w, quarter_h),
            flip_x=True,
        )
        quarter.draw(
            None,
            (padded_rect.x, padded_rect.bottom - quarter_h, quarter_w, quarter_h),
            flip_y=True,
        )
        quarter.draw(
            None,
            (
                padded_rect.right - quarter_w,
                padded_rect.bottom - quarter_h,
                quarter_w,
                quarter_h,
            ),
            flip_x=True,
            flip_y=True,
        )

    def _render_rect(self, bounds: pygame.Rect, _, style: RectStyle):
        if style.color is None:
            return
        padded_rect, border_width, radius = rect_parse_style(bounds, style)
        if padded_rect.w == 0 or padded_rect.h == 0:
            return
        self.renderer.draw_color = style.color
        if all(br == 0 for br in radius):
            if border_width == 0:
                self.renderer.fill_rect(padded_rect)
            else:
                self.renderer.fill_rect(
                    (padded_rect.x, padded_rect.y, border_width, padded_rect.h)
                )
                self.renderer.fill_rect(
                    (
                        padded_rect.x + border_width,
                        padded_rect.y,
                        padded_rect.w - border_width,
                        border_width,
                    )
                )
                self.renderer.fill_rect(
                    (
                        padded_rect.x + border_width,
                        padded_rect.bottom - border_width,
                        padded_rect.w - border_width,
                        border_width,
                    )
                )
                self.renderer.fill_rect(
                    (
                        padded_rect.right - border_width,
                        padded_rect.y + border_width,
                        border_width,
                        padded_rect.h - border_width * 2,
                    )
                )
        else:
            if radius[TL] != 0:
                tl = self._get_circle_corner(
                    (border_width, radius[TL], style.antialias)
                )
                tl.color = style.color
                tl.draw(None, (padded_rect.x, padded_rect.y, radius[TL], radius[TL]))
            if radius[TR] != 0:
                tr = self._get_circle_corner(
                    (border_width, radius[TR], style.antialias)
                )
                tr.color = style.color
                tr.draw(
                    None,
                    (
                        padded_rect.right - radius[TR],
                        padded_rect.y,
                        radius[TR],
                        radius[TR],
                    ),
                    flip_x=True,
                )
            if radius[BR] != 0:
                br = self._get_circle_corner(
                    (border_width, radius[BR], style.antialias)
                )
                br.color = style.color
                br.draw(
                    None,
                    (
                        padded_rect.right - radius[BR],
                        padded_rect.bottom - radius[BR],
                        radius[BR],
                        radius[BR],
                    ),
                    flip_x=True,
                    flip_y=True,
                )
            if radius[BL]:
                bl = self._get_circle_corner(
                    (border_width, radius[BL], style.antialias)
                )
                bl.color = style.color
                bl.draw(
                    None,
                    (
                        padded_rect.x,
                        padded_rect.bottom - radius[BL],
                        radius[BL],
                        radius[BL],
                    ),
                    flip_y=True,
                )
            width = height = border_width
            if border_width == 0:
                width = padded_rect.h / 2
                height = padded_rect.w / 2
            if width != 0:
                self.renderer.fill_rect(
                    (
                        padded_rect.x + radius[TL],
                        padded_rect.y,
                        padded_rect.w - radius[TL] - radius[TR],
                        width,
                    )
                )
                self.renderer.fill_rect(
                    (
                        padded_rect.x + radius[BL],
                        padded_rect.bottom - width,
                        padded_rect.w - radius[BR] - radius[BL],
                        width,
                    )
                )
            if height != 0:
                self.renderer.fill_rect(
                    (
                        padded_rect.x,
                        padded_rect.y + radius[TL],
                        height,
                        padded_rect.h - radius[TL] - radius[BL],
                    )
                )
                self.renderer.fill_rect(
                    (
                        padded_rect.right - height,
                        padded_rect.y + radius[TR],
                        height,
                        padded_rect.h - radius[TR] - radius[BR],
                    )
                )


class SurfaceCanvas(Canvas):
    __module__ = "dimi"


    def __init__(self, surface: pygame.Surface):
        super().__init__()
        self.surface: pygame.Surface = surface
        self._component_render_methods = {
            Component.RECT: self._render_rect,
            Component.ELLIPSE: self._render_ellipse,
            Component.TEXT: self._render_text,
        }
        self._cached_text: dict[int, tuple[pygame.Surface, pygame.Rect, tuple]] = {}
        self._pinged_text_cache_keys: set[int] = set()
        self._cached_antialiased_ellipses: dict[
            tuple[int, int, int, tuple], pygame.Surface
        ] = {}
        self._pinged_antialiased_ellipses: set[tuple[int, int, int, tuple]] = set()

    @property
    def viewport(self) -> pygame.Rect:
        return self.surface.get_clip()

    @viewport.setter
    def viewport(self, value: pygame.typing.RectLike):
        self.surface.set_clip(value)

    def _get_render_rect(
        self, absolute_rect: pygame.Rect, viewport: pygame.Rect
    ) -> pygame.Rect:
        return absolute_rect

    def _render_start(self):
        self._pinged_text_cache_keys = set(self._cached_text.keys())
        self._pinged_antialiased_ellipses = set(
            self._cached_antialiased_ellipses.keys()
        )

    def _render_end(self):
        for key in self._pinged_text_cache_keys:
            self._cached_text.pop(key)
        for key in self._pinged_antialiased_ellipses:
            self._cached_antialiased_ellipses.pop(key)

    def _resolve_text(
        self, cache_key: int, text: str, style: TextStyle, wrap_width: int, height: int
    ) -> tuple[int, int]:
        if cache_key in self._cached_text:
            surface, rect, padding = self._cached_text[cache_key]
            return (rect.w + padding[L] + padding[R], rect.h + padding[T] + padding[B])
        surface, rect, padding = self._create_text_render(
            text, style, wrap_width, height
        )
        self._cached_text[cache_key] = (surface, rect, padding)
        return (rect.w + padding[L] + padding[R], rect.h + padding[T] + padding[B])

    def _render_text(
        self, bounds: pygame.Rect, text: str, style: TextStyle, cache_key: int
    ):
        if cache_key not in self._cached_text:
            raise RuntimeError(
                "Internal error: text was not resolved during the two passes (cached text not found during render pass)"
            )
        surface, rect, padding = self._cached_text[cache_key]
        padded_rect = pygame.Rect(
            bounds.x + padding[L],
            bounds.y + padding[T],
            bounds.w - padding[L] - padding[R],
            bounds.h - padding[T] - padding[B],
        )
        padded_rect.x += style.offset[0]
        padded_rect.y += style.offset[1]
        anchor_rect(rect, padded_rect, style.anchor)
        self.surface.blit(surface, rect)

    def _render_ellipse(self, bounds: pygame.Rect, _, style: EllipseStyle):
        if style.color is None:
            return
        padded_rect, border_width = ellipse_parse_style(bounds, style)
        if padded_rect.w == 0 or padded_rect.h == 0:
            return
        if padded_rect.w == padded_rect.h:
            draw_function = (
                pygame.draw.aacircle if style.antialias else pygame.draw.circle
            )
            draw_function(
                self.surface,
                style.color,
                (padded_rect.w / 2, padded_rect.h / 2),
                padded_rect.w / 2,
                border_width,
            )
        else:
            if not style.antialias:
                pygame.draw.ellipse(
                    self.surface, style.color, padded_rect, border_width
                )
            else:
                color = tuple(pygame.Color(style.color))
                key = padded_rect.w, padded_rect.h, border_width, color
                if key not in self._cached_antialiased_ellipses:
                    mult = 4
                    surf = pygame.Surface(
                        (padded_rect.w * mult, padded_rect.h * mult), pygame.SRCALPHA
                    )
                    pygame.draw.ellipse(
                        surf,
                        color,
                        (0, 0, padded_rect.w * mult, padded_rect.h * mult),
                        border_width,
                    )
                    surf = pygame.transform.smoothscale_by(surf, 1 / mult)
                    self._cached_antialiased_ellipses[key] = surf
                self._pinged_antialiased_ellipses.discard(key)
                ellipse = self._cached_antialiased_ellipses[key]
                self.surface.blit(ellipse, padded_rect.topleft)

    def _render_rect(self, bounds: pygame.Rect, _, style: RectStyle):
        if style.color is None:
            return
        padded_rect, border_width, radius = rect_parse_style(bounds, style)
        if padded_rect.w == 0 or padded_rect.h == 0:
            return
        if all(br == 0 for br in radius) or not style.antialias:
            pygame.draw.rect(
                self.surface,
                style.color,
                padded_rect,
                border_width,
                -1,
                radius[TL],
                radius[TR],
                radius[BL],
                radius[BR],
            )
            return
        circle_func = pygame.draw.aacircle if style.antialias else pygame.draw.circle
        if radius[TL] != 0:
            circle_func(
                self.surface,
                style.color,
                (padded_rect.x + radius[TL], padded_rect.y + radius[TL]),
                radius[TL],
                border_width,
                False,
                True,
                False,
                False,
            )
        if radius[TR] != 0:
            circle_func(
                self.surface,
                style.color,
                (padded_rect.right - radius[TR] - 1, padded_rect.y + radius[TR]),
                radius[TR],
                border_width,
                True,
                False,
                False,
                False,
            )
        if radius[BR] != 0:
            circle_func(
                self.surface,
                style.color,
                (
                    padded_rect.right - radius[BR] - 1,
                    padded_rect.bottom - radius[BR] - 1,
                ),
                radius[BR],
                border_width,
                False,
                False,
                False,
                True,
            )
        if radius[BL]:
            circle_func(
                self.surface,
                style.color,
                (padded_rect.x + radius[BL], padded_rect.bottom - radius[BL] - 1),
                radius[BL],
                border_width,
                False,
                False,
                True,
                False,
            )
        width = height = border_width
        if border_width == 0:
            width = round(padded_rect.h / 2)
            height = round(padded_rect.w / 2)
        if width != 0:
            pygame.draw.rect(
                self.surface,
                style.color,
                (
                    padded_rect.x + radius[TL],
                    padded_rect.y,
                    padded_rect.w - radius[TL] - radius[TR],
                    width,
                ),
            )
            pygame.draw.rect(
                self.surface,
                style.color,
                (
                    padded_rect.x + radius[BL],
                    padded_rect.bottom - width,
                    padded_rect.w - radius[BR] - radius[BL],
                    width,
                ),
            )
        if height != 0:
            pygame.draw.rect(
                self.surface,
                style.color,
                (
                    padded_rect.x,
                    padded_rect.y + radius[TL],
                    height,
                    padded_rect.h - radius[TL] - radius[BL],
                ),
            )
            pygame.draw.rect(self.surface, style.color,
                (
                    padded_rect.right - height,
                    padded_rect.y + radius[TR],
                    height,
                    padded_rect.h - radius[TR] - radius[BR],
                )
            )
