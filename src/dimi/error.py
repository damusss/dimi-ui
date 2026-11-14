class IllegalOperationError(RuntimeError): ...


class IllegalLayoutError(IllegalOperationError): ...


class IllegalHugCombinationError(IllegalLayoutError):
    def __init__(self, child_size_type: str, size_name: str):
        super().__init__(
            f"Child with {child_size_type} {size_name} cannot be measured inside a parent with Hug {size_name}"
        )


class IllegalRatioCombinationError(IllegalLayoutError):
    def __init__(self, ratio_size: str, opposite_size: str):
        super().__init__(
            f"Element with Ratio {ratio_size} needs a well defined {opposite_size} (number/percentage string/Exact/Percent/Span)"
        )


class IllegalAbsoluteAnchorCombinationError(IllegalLayoutError):
    def __init__(self, require_fill: bool, required_fill_size: str):
        super().__init__(
            f"An absolutely positioned element can't fulfill both lateral anchor requests simultaneously if the element's {required_fill_size} isn't Fill(1)."
            if require_fill
            else "An absolutely positioned element can't fulfill both the central anchor request and either of the later anchors simultaneously."
        )


class IllegalSizeIntentForMeasure(IllegalLayoutError):
    def __init__(self, type_name: str):
        super().__init__(
            f"The {type_name} SizeIntent isn't designed to be used as a measure"
        )


class MissingActiveContexError(IllegalOperationError):
    def __init__(self):
        super().__init__(
            "UI operation requires an active context (with dimi.using(context): ...)"
        )


class IllegalWidgetOperationError(IllegalOperationError): ...


class MissingElementForWidget(IllegalWidgetOperationError):
    def __init__(self, widget: str):
        super().__init__(
            f"'{widget}' widget can only be called in the active context of an element"
        )


class IllegalComponentShortcutError(IllegalLayoutError):
    def __init__(self):
        super().__init__(
            "Component shortcuts are intended to be used for childless elements without context managers"
        )


class IllegalStyleEditError(IllegalOperationError):
    def __init__(self, style_name: str | None = None, valid_element=True):
        super().__init__(
            (
                "Styles of an element can only be edited before the declaration pass is over (with dimi.using(context): ...)"
                if valid_element
                else "The return value of 'Context.get_interaction()' cannot edit the element styles"
            )
            if style_name is None
            else f"The '{style_name}' style of an element cannot be edited after element declaration"
        )


class RegistrationError(IllegalOperationError): ...


class WidgetRegistrationError(RegistrationError): ...


class CacheRegistrationError(RegistrationError):
    def __init__(self, cache: str, canvas: type, already=False):
        super().__init__(
            f"Cache '{cache}' was already registered on '{canvas.__name__}'"
            if already
            else f"Cannot get or set a cache that wasn't registered. Use dimi.register_canvas_cache('{cache}', ({canvas.__name__},)) to register it"
        )


class TextLayoutError(IllegalLayoutError): ...


class TextRenderingError(TextLayoutError): ...


class IconFetchError(RuntimeError): ...


class IllegalSubclassError(TypeError):
    def __init__(self, cls):
        super().__init__(
            f"Due to performance/layout concerns it is not allowed to subclass 'dimi.{cls.__name__}'"
        )
