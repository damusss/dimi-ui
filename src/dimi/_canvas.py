import math
import typing
import warnings
from abc import ABC, abstractmethod

import pygame
from pygame import _render

from dimi._components import (
    Component,
    ellipse_parse_style,
    image_parse_style,
    image_parse_transform,
    image_repeat_translate_angle,
    line_parse_style,
    rect_parse_style,
)
from dimi._primitives import (
    BL,
    BR,
    TL,
    TR,
    Axis,
    B,
    Font,
    ImageRepeat,
    L,
    R,
    ScaleQuality,
    T,
    anchor_rect,
    get_directional_measure,
    measure_value,
)
from dimi._style import EllipseStyle, ImageStyle, LineStyle, RectStyle, TextStyle
from dimi.error import CacheRegistrationError, TextRenderingError


class Canvas(ABC):
    __module__ = "dimi.typehinting"

    _registered_caches: typing.ClassVar[set[str]]

    def __init__(self):
        self._component_render_methods: dict[str, typing.Callable] = {}
        self._fonts: dict[tuple[str, bool, bool, bool] | None, pygame.Font] = {}

        self._caches: dict[str, dict[typing.Hashable, typing.Any]] = {}
        self._inactive_caches: dict[str, set[typing.Hashable]] = {}
        for cache in self._registered_caches:
            self._caches[cache] = {}
            self._inactive_caches[cache] = set()

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
        if style.font is None or type(style.font) is Font:
            font: pygame.Font = self._get_font(style.font)
            if style.size is None:
                raise TextRenderingError(
                    "When a manual pygame.Font isn't specified the size style must not be None"
                )
        else:
            font: pygame.Font = style.font
        if style.size is not None:
            size = max(
                1,
                int(measure_value(style.size, wrap_width, available_h, Axis.Y)),
            )
            font.point_size = size
        else:
            size = font.point_size
        outline_width = int(
            measure_value(style.outline_width, wrap_width, size, Axis.Y)
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
                int(measure_value(style.line_skip, wrap_width, size, Axis.Y))
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
                raise TextRenderingError(
                    "The text color can only be None if the outline width is not zero."
                )

        return surface, surface.get_rect(), padding

    def _prepare_caches(self):
        for cache, caches in self._caches.items():
            self._inactive_caches[cache] = set(caches.keys())

    def _cleanup_caches(self):
        for cache, inactive_keys in self._inactive_caches.items():
            for key in inactive_keys:
                self._caches[cache].pop(key, None)

    def _render_start(self):
        self._prepare_caches()

    def _render_end(self):
        self._cleanup_caches()

    def get_cache(self, cache: str, key: typing.Hashable) -> typing.Any | None:
        if cache not in self._registered_caches:
            raise CacheRegistrationError(cache, self.__class__)
        if cache not in self._caches:
            self._caches[cache] = {}
            self._inactive_caches[cache] = set()
        caches = self._caches[cache]
        if key in caches:
            self._inactive_caches[cache].discard(key)
            return caches[key]
        return None

    def set_cache[ValueType](
        self, cache: str, key: typing.Hashable, value: ValueType
    ) -> ValueType:
        if cache not in self._registered_caches:
            raise CacheRegistrationError(cache, self.__class__)
        if cache not in self._caches:
            self._caches[cache] = {}
            self._inactive_caches[cache] = set()
        self._caches[cache][key] = value
        if key in self._inactive_caches[cache][key]:
            self._inactive_caches[cache].discard(key)
        return value

    def _get_cache(
        self, cache: str, key: typing.Hashable, ping=True
    ) -> typing.Any | None:
        if ping:
            self._inactive_caches[cache].discard(key)
        return self._caches[cache].get(key, None)

    def _set_cache(
        self, cache: str, key: typing.Hashable, value: typing.Any, ping: bool = False
    ):
        self._caches[cache][key] = value
        if ping:
            self._inactive_caches[cache].discard(key)

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
    ) -> pygame.Rect: ...

    @abstractmethod
    def _resolve_text(
        self, cache_key: int, text: str, style: TextStyle, wrap_width: int, height: int
    ) -> tuple[int, int]: ...

    @abstractmethod
    def _get_image_1pixels(self): ...


class RendererCanvas(Canvas):
    __module__ = "dimi"

    _registered_caches: typing.ClassVar[set[str]] = {
        "circle_corner",
        "ellipse_corner",
        "text",
        "image_layers",
        "line",
        "icon",
    }

    def __init__(self, renderer: _render.Renderer):
        super().__init__()
        self.renderer = renderer
        self._component_render_methods = {
            Component.RECT: self._render_rect,
            Component.ELLIPSE: self._render_ellipse,
            Component.TEXT: self._render_text,
            Component.IMAGE: self._render_image,
            Component.LINE: self._render_line,
        }

        self._texture_1pixels = _render.Texture(self.renderer, (1, 1), 32)
        self._texture_1pixels.blend_mode = pygame.BLENDMODE_BLEND
        surf_1pixels = pygame.Surface((1, 1), pygame.SRCALPHA)
        surf_1pixels.fill(0)
        self._texture_1pixels.update(surf_1pixels)

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

    def _get_image_1pixels(self):
        return self._texture_1pixels

    def _resolve_text(
        self, cache_key: int, text: str, style: TextStyle, wrap_width: int, height: int
    ) -> tuple[int, int]:
        cached_text = self._get_cache("text", cache_key)
        if cached_text is not None:
            texture, rect, padding = cached_text
            return (rect.w + padding[L] + padding[R], rect.h + padding[T] + padding[B])
        surface, rect, padding = self._create_text_render(
            text, style, wrap_width, height
        )
        if surface.size[0] <= 0 or surface.size[1] <= 0:
            texture = self._texture_1pixels
        else:
            texture = _render.Texture(
                self.renderer,
                surface.size,
                32,
                scale_quality=1 if style.antialias else 0,
            )
            texture.update(surface)
            texture.blend_mode = pygame.BLENDMODE_BLEND
        self._set_cache("text", cache_key, (texture, rect, padding), ping=True)
        return rect.w + padding[L] + padding[R], rect.h + padding[T] + padding[B]

    def _render_text(
        self, bounds: pygame.Rect, _text: str, style: TextStyle, cache_key: int
    ):
        cached_text = self._get_cache("text", cache_key, ping=False)
        if cached_text is None:
            raise RuntimeError(
                "Internal error: text was not resolved during the two passes (cached text not found during render pass)"
            )
        texture, rect, padding = cached_text
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

    def _get_circle_corner(self, bw_br_antialias) -> _render.Texture:
        bw, br, antialias = bw_br_antialias
        br = max(1, br)
        bw = max(0, bw)
        tex = self._get_cache("circle_corner", bw_br_antialias)
        if tex is None:
            surf = pygame.Surface((br, br), pygame.SRCALPHA)
            surf.fill((255, 255, 255, 0))
            draw_function = pygame.draw.aacircle if antialias else pygame.draw.circle
            draw_function(surf, (255, 255, 255, 255), (br, br), br, bw)
            tex = _render.Texture(
                self.renderer, surf.size, 32, scale_quality=1 if antialias else 0
            )
            tex.update(surf)
            tex.blend_mode = pygame.BLENDMODE_BLEND
            self._set_cache("circle_corner", bw_br_antialias, tex)
        return tex

    def _get_ellipse_corner(self, qw_qh_bw_antialias) -> _render.Texture:
        qw, qh, bw, antialias = qw_qh_bw_antialias
        bw = max(0, bw)
        tex = self._get_cache("ellipse_corner", qw_qh_bw_antialias)
        if tex is None:
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
                self._set_cache("ellipse_corner", qw_qh_bw_antialias, tex)
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
                self._set_cache("ellipse_corner", qw_qh_bw_antialias, tex)
        return tex

    def _render_ellipse(self, bounds: pygame.Rect, _, style: EllipseStyle):
        if style.color is None:
            return
        padded_rect, border_width = ellipse_parse_style(bounds, style)
        quarter_w, quarter_h = round(padded_rect.w / 2), round(padded_rect.h / 2)
        if quarter_w <= 0 or quarter_h <= 0:
            return
        quarter = self._get_ellipse_corner(
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
        self.renderer.draw_color = style.color
        self.renderer.draw_line(
            (padded_rect.left + quarter_w, padded_rect.top),
            (padded_rect.left + quarter_w, padded_rect.bottom - 1),
        )
        self.renderer.draw_line(
            (padded_rect.left, padded_rect.top + quarter_h),
            (padded_rect.right - 1, padded_rect.top + quarter_h),
        )

    def _render_rect(self, bounds: pygame.Rect, _, style: RectStyle):
        if style.color is None:
            return
        padded_rect, border_width, radius = rect_parse_style(bounds, style)
        if padded_rect.w <= 0 or padded_rect.h <= 0:
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

    def _render_line(
        self, bounds: pygame.Rect, start_end: tuple[tuple, tuple], style: LineStyle
    ):
        point_a, point_b, line_size = line_parse_style(bounds, start_end, style)
        if line_size <= 0:
            return
        self.renderer.draw_color = style.color
        if style.antialias or line_size != 1:
            half_x = half_y = int(line_size // 2)
            color = pygame.Color(style.color).hex
            if point_a[0] > point_b[0]:
                point_a, point_b = point_b, point_a
            dabx = point_b[0] - point_a[0]
            daby = point_b[1] - point_a[1]
            if dabx >= daby:
                half_x = 0
            elif daby > dabx:
                half_y = 0
            left = min(point_a[0], point_b[0]) - half_x
            top = min(point_a[1], point_b[1]) - half_y
            antialias = style.antialias
            cache_key = (half_x, half_y, line_size, dabx, daby, color, antialias)
            tex = self._get_cache("line", cache_key)
            if tex is None:
                surf = pygame.Surface(
                    (abs(dabx) + half_x * 2, abs(daby) + half_y * 2), pygame.SRCALPHA
                )
                function = pygame.draw.aaline if antialias else pygame.draw.line
                function(
                    surf,
                    color,
                    (point_a[0] - left, point_a[1] - top),
                    (point_b[0] - left, point_b[1] - top),
                    int(line_size),
                )
                tex = _render.Texture(
                    self.renderer, surf.size, 32, scale_quality=1 if antialias else 0
                )
                tex.update(surf)
                tex.blend_mode = pygame.BLENDMODE_BLEND
                self._set_cache("line", cache_key, tex)
            tex.draw(
                None,
                (
                    left,
                    top,
                    tex.width,
                    tex.height,
                ),
            )
        else:
            self.renderer.draw_line(point_a, point_b)

    def _image_border_radius(
        self,
        image: _render.Texture,
        fit_rect: pygame.Rect,
        border_radius,
        style: ImageStyle,
        flip_x,
        flip_y,
        ninepatch_inset,
    ):
        radius_key = (fit_rect.w, fit_rect.h, border_radius)
        layer_cache = self._get_cache("image_layers", radius_key)
        if layer_cache is None:
            layer_tex = _render.Texture(
                self.renderer,
                fit_rect.size,
                32,
                target=True,
                scale_quality=0 if style.scale_quality == ScaleQuality.NEAREST else 1,
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
            layer_cache = layer_tex, corners
            self._set_cache("image_layers", radius_key, layer_cache)

        # todo: change the corners scale quality to the image's
        layer_texture, corner_textures = layer_cache
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
        return layer_texture, flip_x, flip_y, ninepatch_inset

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

        transformed_rect, angle, angle_origin, flip_x, flip_y = image_parse_transform(
            image.width, image.height, style.transform, fit_rect
        )

        if style.scale_quality is not None:
            warnings.warn(
                "Before pygame 3+ it is not possible to dynamically change a Texture's scale quality. Modify it through the Texture constructor or wait for pygame to be upgraded.",
                RuntimeWarning,
            )

        drawing_image = image
        if any(br != 0 for br in border_radius):
            drawing_image, flip_x, flip_y, ninepatch_inset = self._image_border_radius(
                image, fit_rect, border_radius, style, flip_x, flip_y, ninepatch_inset
            )

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
            self._image_repeat_x(
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
            self._image_repeat_y(
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

    def _image_repeat_x(
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
                    image_repeat_translate_angle(
                        transformed_rect, transformed_rect.move(cursor, 0), angle
                    ),
                    patch_size,
                    angle,
                    angle_origin,
                    flip_x,
                    flip_y,
                )
                if repeat == ImageRepeat.BOTH:
                    self._image_repeat_y(
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
                    image_repeat_translate_angle(
                        transformed_rect, transformed_rect.move(cursor, 0), angle
                    ),
                    patch_size,
                    angle,
                    angle_origin,
                    flip_x,
                    flip_y,
                )
                if repeat == ImageRepeat.BOTH:
                    self._image_repeat_y(
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

    def _image_repeat_y(
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
                    image_repeat_translate_angle(
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
                    image_repeat_translate_angle(
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


class SurfaceCanvas(Canvas):
    __module__ = "dimi"

    _registered_caches: typing.ClassVar[set[str]] = {
        "text",
        "image",
        "antialiased_ellipse",
        "icon",
    }

    def __init__(self, surface: pygame.Surface):
        super().__init__()
        self.surface: pygame.Surface = surface
        self._component_render_methods = {
            Component.RECT: self._render_rect,
            Component.ELLIPSE: self._render_ellipse,
            Component.TEXT: self._render_text,
            Component.IMAGE: self._render_image,
            Component.LINE: self._render_line,
        }

        self._surface_1pixels = pygame.Surface((1, 1), pygame.SRCALPHA)
        self._surface_1pixels.fill(0)

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

    def _get_image_1pixels(self):
        return self._surface_1pixels

    def _resolve_text(
        self, cache_key: int, text: str, style: TextStyle, wrap_width: int, height: int
    ) -> tuple[int, int]:
        cached_text = self._get_cache("text", cache_key)
        if cached_text is not None:
            surface, rect, padding = cached_text
            return (rect.w + padding[L] + padding[R], rect.h + padding[T] + padding[B])
        surface, rect, padding = self._create_text_render(
            text, style, wrap_width, height
        )
        self._set_cache("text", cache_key, (surface, rect, padding), ping=True)
        return (rect.w + padding[L] + padding[R], rect.h + padding[T] + padding[B])

    def _render_text(
        self, bounds: pygame.Rect, _text: str, style: TextStyle, cache_key: int
    ):
        cached_text = self._get_cache("text", cache_key)
        if cached_text is None:
            raise RuntimeError(
                "Internal error: text was not resolved during the two passes (cached text not found during render pass)"
            )
        surface, rect, padding = cached_text
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
                (padded_rect.x + padded_rect.w / 2, padded_rect.y + padded_rect.h / 2),
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
                surf = self._get_cache("antialiased_ellipse", key)
                if surf is None:
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
                    self._set_cache("antialiased_ellipse", key, surf)
                self.surface.blit(surf, padded_rect.topleft)

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
            pygame.draw.rect(
                self.surface,
                style.color,
                (
                    padded_rect.right - height,
                    padded_rect.y + radius[TR],
                    height,
                    padded_rect.h - radius[TR] - radius[BR],
                ),
            )

    def _render_line(
        self, bounds: pygame.Rect, start_end: tuple[tuple, tuple], style: LineStyle
    ):
        point_a, point_b, line_size = line_parse_style(bounds, start_end, style)
        if line_size <= 0:
            return
        function = pygame.draw.aaline if style.antialias else pygame.draw.line
        function(self.surface, style.color, point_a, point_b, int(line_size))

    def _image_border_radius(
        self,
        draw_image: pygame.Surface,
        border_radius,
        size,
        fit_size,
        circle_function,
        scale_by_function,
    ):
        tl, tr, bl, br = (
            border_radius[TL],
            border_radius[TR],
            border_radius[BL],
            border_radius[BR],
        )
        tl_mask = pygame.Surface((tl, tl), pygame.SRCALPHA)
        tr_mask = pygame.Surface((tr, tr), pygame.SRCALPHA)
        bl_mask = pygame.Surface((bl, bl), pygame.SRCALPHA)
        br_mask = pygame.Surface((br, br), pygame.SRCALPHA)
        tl_mask.fill(0)
        tr_mask.fill(0)
        bl_mask.fill(0)
        br_mask.fill(0)
        draw_image = draw_image.convert_alpha()
        circle_function(tl_mask, "white", (tl, tl), tl, draw_top_left=True)
        circle_function(tr_mask, "white", (0, tr), tr, draw_top_right=True)
        circle_function(bl_mask, "white", (bl, 0), bl, draw_bottom_left=True)
        circle_function(br_mask, "white", (0, 0), br, draw_bottom_right=True)
        if fit_size != size:
            factor = (size[0] / fit_size[0], size[1] / fit_size[1])
            tl_mask = scale_by_function(tl_mask, factor)
            tr_mask = scale_by_function(tr_mask, factor)
            bl_mask = scale_by_function(bl_mask, factor)
            br_mask = scale_by_function(br_mask, factor)
        draw_image.blit(tl_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        draw_image.blit(
            tr_mask,
            (draw_image.width - tr_mask.width, 0),
            special_flags=pygame.BLEND_RGBA_MULT,
        )
        draw_image.blit(
            bl_mask,
            (0, draw_image.height - bl_mask.height),
            special_flags=pygame.BLEND_RGBA_MULT,
        )
        draw_image.blit(
            br_mask,
            (draw_image.width - br_mask.width, draw_image.height - br_mask.height),
            special_flags=pygame.BLEND_RGBA_MULT,
        )
        return draw_image

    def _image_ninepatch(
        self, image: pygame.Surface, size: tuple[int, int], inset: int, scale_function
    ):
        rw, rh = size
        w, h = image.size
        x_s = w - inset * 2
        y_s = h - inset * 2
        rx_s = rw - inset * 2
        ry_s = rh - inset * 2
        base = pygame.Surface(size, pygame.SRCALPHA)
        base.blit(image.subsurface((0, 0, inset, inset)), (0, 0))
        base.blit(image.subsurface((w - inset, 0, inset, inset)), (rw - inset, 0))
        base.blit(image.subsurface((0, h - inset, inset, inset)), (0, rh - inset))
        base.blit(
            image.subsurface((w - inset, h - inset, inset, inset)),
            (rw - inset, rh - inset),
        )
        if x_s > 0:
            base.blit(
                scale_function(image.subsurface((inset, 0, x_s, inset)), (rx_s, inset)),
                (inset, 0),
            )
            base.blit(
                scale_function(
                    image.subsurface((inset, h - inset, x_s, inset)), (rx_s, inset)
                ),
                (inset, rh - inset),
            )
        if y_s > 0:
            base.blit(
                scale_function(image.subsurface((0, inset, inset, y_s)), (inset, ry_s)),
                (0, inset),
            )
            base.blit(
                scale_function(
                    image.subsurface((w - inset, inset, inset, y_s)), (inset, ry_s)
                ),
                (rw - inset, inset),
            )
        if x_s > 0 and y_s > 0:
            base.blit(
                scale_function(
                    image.subsurface((inset, inset, x_s, y_s)), (rx_s, ry_s)
                ),
                (inset, inset),
            )
        return base

    def _transform_image(
        self,
        image: pygame.Surface,
        size: tuple[int, int],
        fit_size: tuple[int, int],
        scale_quality: ScaleQuality,
        angle: float,
        flip_x: bool,
        flip_y: bool,
        ninepatch_inset: int | None,
        border_radius: tuple[int, int, int, int],
        color_mod: pygame.typing.ColorLike,
        alpha_mod: int,
    ) -> pygame.Surface:
        scale_function = pygame.transform.smoothscale
        scale_by_function = pygame.transform.smoothscale_by
        circle_function = pygame.draw.aacircle
        if scale_quality == ScaleQuality.NEAREST:
            scale_function = pygame.transform.scale
            scale_by_function = pygame.transform.scale_by
            circle_function = pygame.draw.circle

        draw_image = image

        if image.size != size:
            if ninepatch_inset is None:
                draw_image = scale_function(draw_image, size)
            else:
                draw_image = self._image_ninepatch(
                    draw_image, size, ninepatch_inset, scale_function
                )

        if any(br != 0 for br in border_radius):
            draw_image = self._image_border_radius(
                draw_image,
                border_radius,
                size,
                fit_size,
                circle_function,
                scale_by_function,
            )

        if flip_x or flip_y:
            draw_image = pygame.transform.flip(draw_image, flip_x, flip_y)

        if color_mod is not None:
            if draw_image is image:
                draw_image = draw_image.copy()
            draw_image.fill(color_mod, special_flags=pygame.BLEND_RGBA_MULT)

        if alpha_mod is not None:
            if draw_image is image:
                draw_image = draw_image.copy()
            draw_image.set_alpha(alpha_mod)

        if angle != 0:
            draw_image = pygame.transform.rotate(draw_image, -angle)

        return draw_image

    def _render_image(
        self, bounds: pygame.Rect, image: pygame.Surface, style: ImageStyle, padding
    ):
        if not isinstance(image, pygame.Surface):
            raise TypeError("A Surface canvas can only draw Surface objects")

        fit_rect, border_radius, ninepatch_inset = image_parse_style(
            bounds, padding, image.width, image.height, style
        )

        transformed_rect, angle, angle_origin, flip_x, flip_y = image_parse_transform(
            image.width, image.height, style.transform, fit_rect
        )

        cache_key = (
            image,
            transformed_rect.size,
            fit_rect.size,
            style.scale_quality,
            angle,
            flip_x,
            flip_y,
            ninepatch_inset,
            border_radius,
            style.color_modifier,
            style.alpha_modifier,
        )
        draw_image = self._get_cache("image", cache_key)
        if draw_image is None:
            draw_image = self._transform_image(*cache_key)
            self._set_cache("image", cache_key, draw_image)

        blend_mode = 0
        if style.blend_mode is not None:
            blend_mode = style.blend_mode

        render_ox = render_oy = 0
        if angle != 0:
            angle_rad = math.radians(angle)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            dx = angle_origin[0] - (transformed_rect.w / 2.0)
            dy = angle_origin[1] - (transformed_rect.h / 2.0)
            rot_dx = dx * cos_a - dy * sin_a
            rot_dy = dx * sin_a + dy * cos_a
            new_ox = (draw_image.width / 2.0) + rot_dx
            new_oy = (draw_image.height / 2.0) + rot_dy
            render_ox = angle_origin[0] - new_ox
            render_oy = angle_origin[1] - new_oy

        self.surface.blit(
            draw_image,
            (transformed_rect.left + render_ox, transformed_rect.top + render_oy),
            special_flags=blend_mode,
        )
        if style.repeat in (ImageRepeat.X, ImageRepeat.BOTH):
            self._image_repeat_x(
                draw_image,
                bounds,
                transformed_rect,
                angle,
                style.repeat,
                render_ox,
                render_oy,
                blend_mode,
            )
        if style.repeat in (ImageRepeat.Y, ImageRepeat.BOTH):
            self._image_repeat_y(
                draw_image,
                bounds,
                transformed_rect,
                0,
                angle,
                render_ox,
                render_oy,
                blend_mode,
            )

    def _image_repeat_x(
        self,
        image,
        bounds,
        transformed_rect,
        angle,
        repeat,
        render_ox,
        render_oy,
        blend_mode,
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
                draw_loc = image_repeat_translate_angle(
                    transformed_rect, transformed_rect.move(cursor, 0), angle
                )
                self.surface.blit(
                    image,
                    (draw_loc.x + render_ox, draw_loc.y + render_oy),
                    special_flags=blend_mode,
                )
                if repeat == ImageRepeat.BOTH:
                    self._image_repeat_y(
                        image,
                        bounds,
                        transformed_rect,
                        cursor,
                        angle,
                        render_ox,
                        render_oy,
                        blend_mode,
                    )
                cursor += transformed_rect.w
                if transformed_rect.x + cursor > space_left_rect.right:
                    break
        right_space = space_left_rect.right - transformed_rect.right
        if right_space > 0:
            right_amount = int(right_space / transformed_rect.w) + 1
            cursor = transformed_rect.w * right_amount
            for i in range(right_amount):
                draw_loc = image_repeat_translate_angle(
                    transformed_rect, transformed_rect.move(cursor, 0), angle
                )
                self.surface.blit(
                    image,
                    (draw_loc.x + render_ox, draw_loc.y + render_oy),
                    special_flags=blend_mode,
                )
                if repeat == ImageRepeat.BOTH:
                    self._image_repeat_y(
                        image,
                        bounds,
                        transformed_rect,
                        cursor,
                        angle,
                        render_ox,
                        render_oy,
                        blend_mode,
                    )
                cursor -= transformed_rect.w
                if transformed_rect.x + cursor + transformed_rect.w < space_left_rect.x:
                    break

    def _image_repeat_y(
        self,
        image,
        bounds,
        transformed_rect,
        cursor_x,
        angle,
        render_ox,
        render_oy,
        blend_mode,
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
                draw_loc = image_repeat_translate_angle(
                    transformed_rect, transformed_rect.move(cursor_x, cursor), angle
                )
                self.surface.blit(
                    image,
                    (draw_loc.x + render_ox, draw_loc.y + render_oy),
                    special_flags=blend_mode,
                )
                cursor += transformed_rect.h
                if transformed_rect.y + cursor > space_left_rect.bottom:
                    break
        bottom_space = space_left_rect.bottom - transformed_rect.bottom
        if bottom_space > 0:
            bottom_amount = int(bottom_space / transformed_rect.h) + 1
            cursor = transformed_rect.h * bottom_amount
            for i in range(bottom_amount):
                draw_loc = image_repeat_translate_angle(
                    transformed_rect, transformed_rect.move(cursor_x, cursor), angle
                )
                self.surface.blit(
                    image,
                    (draw_loc.x + render_ox, draw_loc.y + render_oy),
                    special_flags=blend_mode,
                )
                cursor -= transformed_rect.h
                if transformed_rect.y + cursor + transformed_rect.h < space_left_rect.y:
                    break
