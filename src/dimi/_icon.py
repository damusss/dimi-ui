import dataclasses
import enum
import hashlib
import io
import os
import threading
import typing
import urllib.error
import urllib.parse
import urllib.request
from abc import ABCMeta, abstractmethod

import pygame
from pygame._render import Renderer, Texture

from dimi._dimi import get_current_context

DEFAULT_SVG_SIZE = 128


# todo consider exporting to dimi.typehinting
class IconFetchError(Exception): ...


class FetchFailBehavior(enum.Enum):
    RAISE = enum.auto()
    RETRY_NEXT_GET = enum.auto()
    RETURN_NONE = enum.auto()
    RETURN_EMPTY_IMAGE = enum.auto()


class LoadFailBehavior(enum.Enum):
    RAISE = enum.auto()
    RETURN_NONE = enum.auto()
    RETURN_EMPTY_IMAGE = enum.auto()


@dataclasses.dataclass(slots=True, frozen=True)
class IconifyStyle:
    __module__ = "dimi.icon"

    size: int = DEFAULT_SVG_SIZE
    color: pygame.typing.ColorLike | None = "white"
    tint: pygame.typing.ColorLike | None = None
    flip_x: bool = False
    flip_y: bool = False
    rotations_90deg: int = 0
    async_fetch: bool = True
    fetch_fail_behavior: FetchFailBehavior = FetchFailBehavior.RAISE
    get_raw: bool = False


class IconifyStyleOverrides(typing.TypedDict, total=False):
    __module__ = "dimi.typehinting"

    size: int
    color: pygame.typing.ColorLike | None
    tint: pygame.typing.ColorLike | None
    flip_x: bool
    flip_y: bool
    rotations_90deg: int
    async_fetch: bool
    fetch_fail_behavior: FetchFailBehavior
    get_raw: bool


@dataclasses.dataclass(slots=True, frozen=True)
class URLSVGStyle:
    __module__ = "dimi.icon"

    size: int = DEFAULT_SVG_SIZE
    tint: pygame.typing.ColorLike | None = None
    async_fetch: bool = True
    fetch_fail_behavior: FetchFailBehavior = FetchFailBehavior.RAISE
    get_raw: bool = False


class URLSVGStyleOverrides(typing.TypedDict, total=False):
    __module__ = "dimi.typehinting"

    size: int
    tint: pygame.typing.ColorLike | None
    async_fetch: bool
    fetch_fail_behavior: FetchFailBehavior
    get_raw: bool


@dataclasses.dataclass(slots=True, frozen=True)
class LocalSVGStyle:
    __module__ = "dimi.icon"

    size: int = DEFAULT_SVG_SIZE
    tint: pygame.typing.ColorLike | None = None
    async_load: bool = True
    load_fail_behavior: LoadFailBehavior = LoadFailBehavior.RAISE
    get_raw: bool = False


class LocalSVGStyleOverrides(typing.TypedDict, total=False):
    __module__ = "dimi.typehinting"

    size: int
    tint: pygame.typing.ColorLike | None
    async_load: bool
    load_fail_behavior: LoadFailBehavior
    get_raw: bool


@dataclasses.dataclass(slots=True, frozen=True)
class SVGStyle:
    __module__ = "dimi.icon"

    size: int = 128
    tint: pygame.typing.ColorLike | None = None


class SVGStyleOverrides(typing.TypedDict, total=False):
    __module__ = "dimi.typehinting"

    size: int
    tint: pygame.typing.ColorLike | None


@dataclasses.dataclass(slots=True, frozen=True)
class URLImageStyle:
    __module__ = "dimi.icon"

    tint: pygame.typing.ColorLike | None = None
    load_namehint: str = ""
    async_fetch: bool = True
    bytes_fetcher: typing.Callable[[str], bytes] | None = None
    fetch_fail_behavior: FetchFailBehavior = FetchFailBehavior.RAISE


class URLImageStyleOverrides(typing.TypedDict, total=False):
    __module__ = "dimi.typehinting"

    tint: pygame.typing.ColorLike | None
    load_namehint: str
    async_fetch: bool
    bytes_fetcher: typing.Callable[[str], bytes] | None
    fetch_fail_behavior: FetchFailBehavior


@dataclasses.dataclass(slots=True, frozen=True)
class LocalImageStyle:
    __module__ = "dimi.icon"

    tint: pygame.typing.ColorLike | None = None
    async_load: bool = True
    load_fail_behavior: LoadFailBehavior = LoadFailBehavior.RAISE


class LocalImageStyleOverrides(typing.TypedDict, total=False):
    __module__ = "dimi.typehinting"

    tint: pygame.typing.ColorLike | None
    async_load: bool
    load_fail_behavior: LoadFailBehavior


DEFAULT_ICONIFY_STYLE = IconifyStyle()
DEFAULT_LOCAL_SVG_STYLE = LocalSVGStyle()
DEFAULT_LOCAL_STYLE = LocalImageStyle()
DEFAULT_SVG_STYLE = SVGStyle()
DEFAULT_URL_SVG_STYLE = URLSVGStyle()
DEFAULT_URL_STYLE = URLImageStyle()

PENDING = object()
SURFACE_1PIXELS = pygame.Surface((1, 1), pygame.SRCALPHA)
SURFACE_1PIXELS.fill(0)

settings: dict = {
    "cache_to": None,
    "iconify_icon_set": None,
    "iconify_cache_to": None,
    "url_svg_cache_to": None,
    "url_image_cache_to": None,
    "iconify_style": None,
    "url_svg_style": None,
    "url_image_style": None,
    "local_svg_style": None,
    "local_image_style": None,
    "svg_style": None,
    "local_svg_folder": None,
    "local_image_folder": None,
}
iconify_defaults_for: dict[str, IconifyStyle] = {}
cached_data: dict = {}


def iconify_parse_args(
    icon_set: str | None,
    style: IconifyStyle | None,
    style_overrides: IconifyStyleOverrides,
) -> tuple[str, IconifyStyle]:
    if icon_set is None:
        if settings["iconify_icon_set"] is None:
            raise ValueError("Can't omit icon_set if no default has been set")
        icon_set = settings["iconify_icon_set"]
    if style is None:
        if icon_set in iconify_defaults_for:
            style = iconify_defaults_for[icon_set]
        elif settings["iconify_style"] is not None:
            style = settings["iconify_style"]
        else:
            style = DEFAULT_ICONIFY_STYLE
    if len(style_overrides) > 0:
        style = dataclasses.replace(style, **style_overrides)
    return icon_set, style


def path_style_parse_args(
    path: str,
    style: LocalSVGStyle | LocalImageStyle | None,
    style_overrides: LocalSVGStyleOverrides | LocalImageStyleOverrides,
    folder_name,
    style_name,
    default_style,
):
    if settings[folder_name] is not None:
        path = os.path.join(settings[folder_name], path)
    if style is None:
        if settings[style_name] is not None:
            style = settings[style_name]
        else:
            style = default_style
    if len(style_overrides) > 0:
        style = dataclasses.replace(style, **style_overrides)
    return path, style


def style_parse_args(
    style: URLSVGStyle | URLImageStyle | SVGStyle | None,
    style_overrides: URLSVGStyleOverrides | URLImageStyleOverrides | SVGStyleOverrides,
    style_name,
    default_style,
):
    if style is None:
        if settings[style_name] is not None:
            style = settings[style_name]
        else:
            style = default_style
    if len(style_overrides) > 0:
        style = dataclasses.replace(style, **style_overrides)
    return style


def hash_url_key(url_key: str):
    return hashlib.sha256(url_key.encode("utf-8")).hexdigest()


def get_cache_to(config_name):
    specific_cache_to = settings[config_name]
    if specific_cache_to is None:
        return settings["cache_to"]
    return specific_cache_to


def fetch_handle_exception(
    cache_key: str,
    style: IconifyStyle | URLSVGStyle | URLImageStyle,
    exception: Exception,
):
    if style.fetch_fail_behavior == FetchFailBehavior.RETURN_EMPTY_IMAGE:
        cached_data[cache_key] = PENDING
    elif style.fetch_fail_behavior == FetchFailBehavior.RETURN_NONE:
        cached_data[cache_key] = None
    elif style.fetch_fail_behavior == FetchFailBehavior.RETRY_NEXT_GET:
        cached_data.pop(cache_key, None)
    elif style.fetch_fail_behavior == FetchFailBehavior.RAISE:
        cached_data[cache_key] = exception


def load_handle_exception(
    cache_key: str, style: LocalImageStyle | LocalSVGStyle, exception: Exception
):
    if style.load_fail_behavior == LoadFailBehavior.RETURN_EMPTY_IMAGE:
        cached_data[cache_key] = PENDING
    elif style.load_fail_behavior == LoadFailBehavior.RETURN_NONE:
        cached_data[cache_key] = None
    elif style.load_fail_behavior == LoadFailBehavior.RAISE:
        cached_data[cache_key] = exception


def iconify_threaded_fetch_svg(
    cache_key: str, name: str, icon_set: str, color: str | None, style: IconifyStyle
):
    cache_to = get_cache_to("iconify_cache_to")
    cache_file = None
    if cache_to is not None:
        cache_file = os.path.join(cache_to, f"{cache_key}.svg")
        if os.path.exists(cache_file):
            with open(cache_file, "r") as svg_file:
                raw_svg = svg_file.read()
                cached_data[cache_key] = raw_svg
                return
    base_url = f"https://api.iconify.design/{icon_set}/{name}.svg"
    flip = None
    if style.flip_x and style.flip_y:
        flip = "horizontal,vertical"
    elif style.flip_x:
        flip = "horizontal"
    elif style.flip_y:
        flip = "vertical"
    query_args = {}
    if color is not None:
        query_args["color"] = color
    if flip is not None:
        query_args["flip"] = flip
    if style.rotations_90deg != 0:
        query_args["rotate"] = str(style.rotations_90deg)
    query = urllib.parse.urlencode({**query_args, "width": "unset"})
    iconify_url = f"{base_url}?{query}"
    try:
        req = urllib.request.Request(iconify_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                svg_data = response.read().decode("utf-8")
                cached_data[cache_key] = svg_data
                if cache_file is not None:
                    with open(cache_file, "w") as svg_file:
                        svg_file.write(svg_data)
                return
            else:
                raise IconFetchError(f"HTTP Error: {response.status}")
    except (urllib.error.URLError, urllib.error.HTTPError, IconFetchError) as e:
        fetch_handle_exception(cache_key, style, e)


def iconify_fetch_svg(
    cache_key: str, name: str, icon_set: str, color: str | None, style: IconifyStyle
):
    if style.async_fetch:
        cached_data[cache_key] = PENDING
        thread = threading.Thread(
            target=iconify_threaded_fetch_svg,
            args=(cache_key, name, icon_set, color, style),
        )
        thread.daemon = True
        thread.start()
        return None
    iconify_threaded_fetch_svg(cache_key, name, icon_set, color, style)
    return cached_data.get(cache_key, None)


def url_svg_threaded_fetch(cache_key: str, svg_url: str, style: URLSVGStyle):
    cache_to = get_cache_to("url_svg_cache_to")
    cache_file = None
    if cache_to is not None:
        cache_file = os.path.join(cache_to, f"{hash_url_key(cache_key)}.svg")
        if os.path.exists(cache_file):
            with open(cache_file, "r") as svg_file:
                raw_svg = svg_file.read()
                cached_data[cache_key] = raw_svg
                return
    try:
        req = urllib.request.Request(svg_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                svg_data = response.read().decode("utf-8")
                cached_data[cache_key] = svg_data
                if cache_file is not None:
                    with open(cache_file, "w") as svg_file:
                        svg_file.write(svg_data)
                return
            else:
                raise IconFetchError(f"HTTP Error: {response.status}")
    except (urllib.error.URLError, urllib.error.HTTPError, IconFetchError) as e:
        fetch_handle_exception(cache_key, style, e)


def default_image_fetch_request(image_url):
    req = urllib.request.Request(image_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response:
        if response.status == 200:
            return response.read()
        else:
            raise IconFetchError(f"HTTP Error: {response.status}")


def url_image_threaded_fetch(cache_key: str, image_url: str, style: URLImageStyle):
    cache_to = get_cache_to("url_image_cache_to")
    cache_file = None
    if cache_to is not None:
        cache_file = os.path.join(cache_to, f"{hash_url_key(cache_key)}.png")
        if os.path.exists(cache_file):
            surf = pygame.image.load(cache_file, style.load_namehint).convert(
                SURFACE_1PIXELS
            )
            cached_data[cache_key] = surf
            return
    try:
        image_fetch_request = default_image_fetch_request
        if style.bytes_fetcher is not None:
            image_fetch_request = style.bytes_fetcher
        image_bytes = image_fetch_request(image_url)
        surf = pygame.image.load(io.BytesIO(image_bytes))
        cached_data[cache_key] = surf
        if cache_file is not None:
            pygame.image.save(surf, cache_file)
    except (urllib.error.URLError, urllib.error.HTTPError, IconFetchError) as e:
        fetch_handle_exception(cache_key, style, e)


def local_svg_threaded_load(cache_key: str, file_path: str, style: LocalSVGStyle):
    try:
        with open(file_path, "r") as svg_file:
            raw_svg = svg_file.read()
            cached_data[cache_key] = raw_svg
    except (pygame.error, FileNotFoundError, OSError) as e:
        load_handle_exception(cache_key, style, e)


def local_image_threaded_load(cache_key: str, file_path: str, style: LocalImageStyle):
    try:
        surf = pygame.image.load(file_path).convert(SURFACE_1PIXELS)
        cached_data[cache_key] = surf
    except (pygame.error, FileNotFoundError, OSError) as e:
        load_handle_exception(cache_key, style, e)


def fetch_or_load_surf_or_svg(
    cache_key: str, data: str, style, async_operation, threaded_function
):
    if async_operation:
        cached_data[cache_key] = PENDING
        thread = threading.Thread(
            target=threaded_function, args=(cache_key, data, style)
        )
        thread.daemon = True
        thread.start()
        return None
    threaded_function(cache_key, data, style)
    return cached_data.get(cache_key, None)


def rasterize_and_tint_svg(
    raw_svg: str,
    size: int,
    tint: pygame.typing.ColorLike | None,
    renderer: Renderer | None,
):
    svg_io = io.BytesIO(raw_svg.encode("utf-8"))
    rasterized_surface = pygame.image.load_sized_svg(svg_io, (size, size))
    if tint is not None:
        tint_surface = pygame.Surface(rasterized_surface.size, pygame.SRCALPHA)
        tint_surface.fill(tint)
        rasterized_surface.blit(tint_surface, special_flags=pygame.BLEND_RGBA_MULT)
    if renderer is not None:
        tex = Texture(renderer, rasterized_surface.size, 32, scale_quality=1)
        tex.blend_mode = pygame.BLENDMODE_BLEND
        tex.update(rasterized_surface)
        return tex
    return rasterized_surface


def tint_surf(
    surf: pygame.Surface,
    tint: pygame.typing.ColorLike | None,
    renderer: Renderer | None,
):
    if tint is not None:
        tint_surface = pygame.Surface(surf.size, pygame.SRCALPHA)
        tint_surface.fill(tint)
        surf = surf.copy()
        surf.blit(tint_surface, special_flags=pygame.BLEND_RGBA_MULT)
    if renderer is not None:
        tex = Texture(renderer, surf.size, 32, scale_quality=1)
        tex.blend_mode = pygame.BLENDMODE_BLEND
        tex.update(surf)
        return tex
    return surf


def svg_rasterize_tint_context_cache(
    context,
    raw_svg,
    svg_cache_key,
    style: IconifyStyle | LocalSVGStyle | URLSVGStyle | SVGStyle,
):
    if context is None:
        return rasterize_and_tint_svg(raw_svg, style.size, style.tint, None)
    tint = style.tint
    if tint is not None:
        tint = pygame.Color(tint).hex
    canva_key = (svg_cache_key, f"{style.size}_{tint}")
    if canva_key in context.canvas._icon_cache:
        rasterized = context.canvas._icon_cache[canva_key]
    else:
        rasterized = rasterize_and_tint_svg(
            raw_svg,
            style.size,
            style.tint,
            getattr(context.canvas, "renderer", None),
        )
        context.canvas._icon_cache[canva_key] = rasterized
    context.canvas._icon_pinged.discard(canva_key)
    return rasterized


def surf_tint_context_cache(context, surf, surf_cache_key, style):
    if context is None:
        return tint_surf(surf, style.tint, None)
    tint = style.tint
    if tint is not None:
        tint = pygame.Color(tint).hex
    canva_key = (surf_cache_key, tint)
    if canva_key in context.canvas._icon_cache:
        tinted = context.canvas._icon_cache[canva_key]
    else:
        tinted = tint_surf(surf, style.tint, getattr(context.canvas, "renderer", None))
        context.canvas._icon_cache[canva_key] = tinted
    context.canvas._icon_pinged.discard(canva_key)
    return tinted


def get_context_for_svg(
    detect_context: bool, style: SVGStyle | IconifyStyle | LocalSVGStyle | URLSVGStyle
):
    context = None
    image_1pixels = SURFACE_1PIXELS
    if detect_context:
        context = get_current_context()
    if style.get_raw:
        image_1pixels = ""
    elif context is not None:
        image_1pixels = context.canvas._get_image_1pixels()
    return context, image_1pixels


def get_context_for_image(detect_context: bool):
    context = None
    image_1pixels = SURFACE_1PIXELS
    if detect_context:
        context = get_current_context()
    if context is not None:
        image_1pixels = context.canvas._get_image_1pixels()
    return context, image_1pixels


def cache_to(default_cache_to: str | None):
    settings["cache_to"] = default_cache_to


class PackedIcon(metaclass=ABCMeta):
    __module__ = "dimi.typehinting"

    @abstractmethod
    def get(self): ...


class StaticPackedIcon(PackedIcon):
    __module__ = "dimi.icon"

    def __init__(self, image):
        self.image = image

    def get(self):
        return self.image


class DynamicPackedIcon(PackedIcon):
    __module__ = "dimi.icon"

    def __init__(
        self, icon_getter: typing.Callable, getter_args: tuple, getter_kwargs: dict
    ):
        self.icon_getter = icon_getter
        self.getter_args = getter_args
        self.getter_kwargs = getter_kwargs

    def get(self):
        return self.icon_getter(*self.getter_args, **self.getter_kwargs)


class iconify:
    __module__ = "dimi.icon"

    @staticmethod
    def set_defaults(default_style: IconifyStyle | None, default_icon_set: str | None):
        settings["iconify_style"] = default_style
        settings["iconify_icon_set"] = default_icon_set

    @staticmethod
    def set_default_for(icon_set: str, style: IconifyStyle):
        iconify_defaults_for[icon_set] = style

    @staticmethod
    def cache_to(cache_svg_to: str | None):
        settings["iconify_cache_to"] = cache_svg_to

    @staticmethod
    def pack(
        name: str,
        icon_set: str | None = None,
        style: IconifyStyle | None = None,
        detect_context: bool = True,
        **style_overrides: typing.Unpack[IconifyStyleOverrides],
    ) -> PackedIcon:
        return DynamicPackedIcon(
            iconify.get, (name, icon_set, style, detect_context), style_overrides
        )

    @staticmethod
    def get(
        name: str,
        icon_set: str | None = None,
        style: IconifyStyle | None = None,
        detect_context: bool = True,
        **style_overrides: typing.Unpack[IconifyStyleOverrides],
    ):
        icon_set, style = iconify_parse_args(icon_set, style, style_overrides)
        if style.color is None:
            request_color = None
        else:
            request_color = pygame.Color(style.color).hex
        context, image_1pixels = get_context_for_svg(detect_context, style)
        svg_cache_key = f"iconify_{name}_{icon_set}_{request_color}_{style.flip_x}_{style.flip_y}_{style.rotations_90deg}"
        if svg_cache_key in cached_data:
            raw_svg = cached_data[svg_cache_key]
        else:
            raw_svg = iconify_fetch_svg(
                svg_cache_key, name, icon_set, request_color, style
            )
        if raw_svg is None or raw_svg == PENDING:
            return image_1pixels
        elif isinstance(raw_svg, Exception):
            raise raw_svg
        if style.get_raw:
            return raw_svg
        return svg_rasterize_tint_context_cache(context, raw_svg, svg_cache_key, style)


class url_svg:
    __module__ = "dimi.icon"

    @staticmethod
    def set_defaults(default_style: URLSVGStyle | None):
        settings["url_svg_style"] = default_style

    @staticmethod
    def cache_to(cache_svg_to: str | None):
        settings["url_svg_cache_to"] = cache_svg_to

    @staticmethod
    def pack(
        svg_url: str,
        style: URLSVGStyle | None = None,
        detect_context: bool = True,
        **style_overrides: typing.Unpack[URLSVGStyleOverrides],
    ) -> PackedIcon:
        return DynamicPackedIcon(
            url_svg.get, (svg_url, style, detect_context), style_overrides
        )

    @staticmethod
    def get(
        svg_url: str,
        style: URLSVGStyle | None = None,
        detect_context: bool = True,
        **style_overrides: typing.Unpack[URLSVGStyleOverrides],
    ):
        style = style_parse_args(
            style, style_overrides, "url_svg_style", DEFAULT_URL_SVG_STYLE
        )
        context, image_1pixels = get_context_for_svg(detect_context, style)
        svg_cache_key = svg_url
        if svg_cache_key in cached_data:
            raw_svg = cached_data[svg_cache_key]
        else:
            raw_svg = fetch_or_load_surf_or_svg(
                svg_cache_key,
                svg_url,
                style,
                style.async_fetch,
                url_svg_threaded_fetch,
            )
        if raw_svg is None or raw_svg == PENDING:
            return image_1pixels
        elif isinstance(raw_svg, Exception):
            raise raw_svg
        if style.get_raw:
            return raw_svg
        return svg_rasterize_tint_context_cache(context, raw_svg, svg_cache_key, style)


class local_svg:
    __module__ = "dimi.icon"

    @staticmethod
    def set_defaults(
        default_style: LocalSVGStyle | None, parent_folder: str | None = None
    ):
        settings["local_svg_style"] = default_style
        settings["local_svg_folder"] = parent_folder

    @staticmethod
    def pack(
        file_path: str,
        style: LocalSVGStyle | None = None,
        detect_context: bool = True,
        **style_overrides: typing.Unpack[LocalSVGStyleOverrides],
    ):
        return DynamicPackedIcon(
            local_svg.get, (file_path, style, detect_context), style_overrides
        )

    @staticmethod
    def get(
        file_path: str,
        style: LocalSVGStyle | None = None,
        detect_context: bool = True,
        **style_overrides: typing.Unpack[LocalSVGStyleOverrides],
    ):
        file_path, style = path_style_parse_args(
            file_path,
            style,
            style_overrides,
            "local_svg_folder",
            "local_svg_style",
            DEFAULT_LOCAL_SVG_STYLE,
        )
        context, image_1pixels = get_context_for_svg(detect_context, style)
        svg_cache_key = f"svg_{file_path}"
        if svg_cache_key in cached_data:
            raw_svg = cached_data[svg_cache_key]
        else:
            raw_svg = fetch_or_load_surf_or_svg(
                svg_cache_key,
                file_path,
                style,
                style.async_load,
                local_svg_threaded_load,
            )
        if raw_svg is None or raw_svg == PENDING:
            return image_1pixels
        elif isinstance(raw_svg, Exception):
            raise raw_svg
        if style.get_raw:
            return raw_svg
        return svg_rasterize_tint_context_cache(context, raw_svg, svg_cache_key, style)


class svg:
    __module__ = "dimi.icon"

    @staticmethod
    def set_defaults(default_style: SVGStyle | None):
        settings["svg_style"] = default_style

    @staticmethod
    def pack(
        raw_svg: str,
        style: SVGStyle | None = None,
        detect_context: bool = True,
        **style_overrides: typing.Unpack[SVGStyleOverrides],
    ):
        return DynamicPackedIcon(
            svg.get, (raw_svg, style, detect_context), style_overrides
        )

    @staticmethod
    def get(
        raw_svg: str,
        style: SVGStyle | None = None,
        detect_context: bool = True,
        **style_overrides: typing.Unpack[SVGStyleOverrides],
    ):
        style = style_parse_args(style, style_overrides, "svg_style", DEFAULT_SVG_STYLE)
        context = None
        if detect_context:
            context = get_current_context()
        return svg_rasterize_tint_context_cache(context, raw_svg, raw_svg, style)


class url_image:
    __module__ = "dimi.icon"

    @staticmethod
    def set_defaults(default_style: URLImageStyle | None):
        settings["url_image_style"] = default_style

    @staticmethod
    def cache_to(cache_png_to: str | None):
        settings["url_image_cache_to"] = cache_png_to

    @staticmethod
    def pack(
        image_url: str,
        style: URLImageStyle | None = None,
        detect_context: bool = True,
        **style_overrides: typing.Unpack[URLImageStyleOverrides],
    ):
        return DynamicPackedIcon(
            url_image.get, (image_url, style, detect_context), style_overrides
        )

    @staticmethod
    def get(
        image_url: str,
        style: URLImageStyle | None = None,
        detect_context: bool = True,
        **style_overrides: typing.Unpack[URLImageStyleOverrides],
    ):
        style = style_parse_args(
            style,
            style_overrides,
            "url_image_style",
            DEFAULT_URL_STYLE,
        )
        context, image_1pixels = get_context_for_image(detect_context)
        surf_cache_key = f"url_{image_url}"
        if surf_cache_key in cached_data:
            surf = cached_data[surf_cache_key]
        else:
            surf = fetch_or_load_surf_or_svg(
                surf_cache_key,
                image_url,
                style,
                style.async_fetch,
                url_image_threaded_fetch,
            )
        if surf is None or surf == PENDING:
            return image_1pixels
        elif isinstance(surf, Exception):
            raise surf
        return surf_tint_context_cache(context, surf, surf_cache_key, style)


class local_image:
    __module__ = "dimi.icon"

    @staticmethod
    def set_defaults(
        default_style: LocalImageStyle | None, parent_folder: str | None = None
    ):
        settings["local_image_style"] = default_style
        settings["local_image_folder"] = parent_folder

    @staticmethod
    def pack(
        file_path: str,
        style: LocalImageStyle | None = None,
        detect_context: bool = True,
        **style_overrides: typing.Unpack[LocalImageStyleOverrides],
    ):
        return DynamicPackedIcon(
            local_image.get, (file_path, style, detect_context), style_overrides
        )

    @staticmethod
    def get(
        file_path: str,
        style: LocalImageStyle | None = None,
        detect_context: bool = True,
        **style_overrides: typing.Unpack[LocalImageStyleOverrides],
    ):
        file_path, style = path_style_parse_args(
            file_path,
            style,
            style_overrides,
            "local_image_folder",
            "local_image_style",
            DEFAULT_LOCAL_STYLE,
        )
        context, image_1pixels = get_context_for_image(detect_context)
        surf_cache_key = f"local_{file_path}"
        if surf_cache_key in cached_data:
            surf = cached_data[surf_cache_key]
        else:
            surf = fetch_or_load_surf_or_svg(
                surf_cache_key,
                file_path,
                style,
                style.async_load,
                local_image_threaded_load,
            )
        if surf is None or surf == PENDING:
            return image_1pixels
        elif isinstance(surf, Exception):
            raise surf
        return surf_tint_context_cache(context, surf, surf_cache_key, style)
