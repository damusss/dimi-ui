import typing

import pygame

from dimi._context import Context
from dimi._dimi import get_current_context, register_widget
from dimi.error import MissingActiveContexError, MissingElementForWidget


class CheckboxState:
    __module__ = "dimi.typehinting"

    def __init__(self, _instance: CheckboxDict):
        self._instance = _instance

    @property
    def selected(self) -> bool:
        return self._instance["selected"]

    @selected.setter
    def selected(self, value: bool):
        if self._instance["selected"] == value:
            return
        checkbox_toggle(self._instance)

    @property
    def marked_for_swap(self) -> bool:
        return self._instance["marked_for_swap"]

    @marked_for_swap.setter
    def marked_for_swap(self, value: bool):
        if self._instance["marked_for_swap"] == value:
            return
        checkbox_toggle_marked_for_swap(self._instance)

    def __enter__(self) -> typing.Self:
        return self

    def __exit__(self, *args, **kwargs): ...


class CheckboxDict(typing.TypedDict):
    id: int
    selected: bool
    marked_for_swap: bool
    group_id: str | None
    context: Context
    state: CheckboxState


class CheckboxGroupDict(typing.TypedDict):
    id: str
    min: int | None
    max: int | None
    checkboxes: set[int]


def checkbox_init(
    id_: int, initial_selected: bool, group_id: str | None, context: Context
) -> CheckboxDict:
    self = {
        "id": id_,
        "selected": initial_selected,
        "marked_for_swap": False,
        "group_id": group_id,
        "context": context,
    }
    self["state"] = CheckboxState(self)
    return self


def checkbox_group_init(
    _id: str, min_: int | None, max_: int | None
) -> CheckboxGroupDict:
    return {"id": _id, "min": min_, "max": max_, "checkboxes": set()}


def checkbox_toggle(self: CheckboxDict, group_state: CheckboxGroupDict | None = None):
    if self["group_id"] is None:
        self["selected"] = not self["selected"]
        self["marked_for_swap"] = False
        return
    if group_state is None:
        group_state: CheckboxGroupDict = self["context"].get_widget_state(
            "checkbox", None, self["group_id"]
        )
    selected_amount = 1 if self["selected"] else 0
    checkboxes: list[CheckboxDict] = []
    marked_for_swap_cb: CheckboxDict | None = None
    for cb_id in group_state["checkboxes"]:
        if cb_id == self["id"]:
            continue
        else:
            cb: CheckboxDict | None = self["context"].get_widget_state(
                "checkbox", None, cb_id
            )
            if cb is not None:
                checkboxes.append(cb)
                if cb["selected"]:
                    selected_amount += 1
                    if cb["marked_for_swap"]:
                        marked_for_swap_cb = cb
    if self["selected"]:  # deselecting
        if group_state["min"] is None or selected_amount > group_state["min"]:
            self["selected"] = False
            self["marked_for_swap"] = False
    else:  # selecting
        if group_state["max"] is None or selected_amount < group_state["max"]:
            self["selected"] = True
            self["marked_for_swap"] = False
        elif group_state["max"] == 1:
            for cb in checkboxes:
                if cb["selected"]:
                    cb["selected"] = False
                    cb["marked_for_swap"] = False
            self["selected"] = True
            self["marked_for_swap"] = False
        elif marked_for_swap_cb is not None:
            marked_for_swap_cb["selected"] = False
            marked_for_swap_cb["marked_for_swap"] = False
            self["selected"] = True
            self["marked_for_swap"] = False


def checkbox_toggle_marked_for_swap(
    self: CheckboxDict, group_state: CheckboxGroupDict | None = None
):
    if self["group_id"] is None:
        return
    if self["marked_for_swap"]:  # unmarking
        self["marked_for_swap"] = False
        return
    if not self["selected"]:
        return
    if group_state is None:
        group_state: CheckboxGroupDict = self["context"].get_widget_state(
            "checkbox", None, self["group_id"]
        )
    for cb_id in group_state["checkboxes"]:
        if cb_id == self["id"]:
            continue
        cb: CheckboxDict | None = self["context"].get_widget_state(
            "checkbox", None, cb_id
        )
        if cb is not None:
            cb["marked_for_swap"] = False
    self["marked_for_swap"] = True


def checkbox(initial_selected: bool = False) -> CheckboxState:
    context = get_current_context()
    if context is None:
        raise MissingActiveContexError()
    interaction = context.get_last_interaction()
    if interaction is None:
        raise MissingElementForWidget("checkbox")

    group: checkbox_group | None = checkbox_group._group_stack[-1]
    self: CheckboxDict = context.get_widget_state(
        "checkbox",
        checkbox_init,
        init_args=(
            initial_selected,
            group._state["id"] if group is not None else None,
            context,
        ),
    )

    if group is not None:
        group._state["checkboxes"].add(self["id"])

    clicked = interaction.clicked
    if (
        group is not None
        and self["selected"]
        and (
            (clicked and pygame.key.get_mods() & pygame.KMOD_CTRL)
            or interaction.right_clicked
        )
    ):
        checkbox_toggle_marked_for_swap(self, group._state)
    elif clicked:
        checkbox_toggle(self, group._state if group is not None else None)

    state = self["state"]
    return state


class checkbox_group:
    _group_stack: typing.ClassVar[list[checkbox_group | None]] = [None]
    __module__ = "dimi.widget"

    def __init__(self, min_selected: int | None = 0, max_selected: int | None = 1):
        context = get_current_context()
        if context is None:
            raise MissingActiveContexError()
        id_ = context.get_last_id()
        self._state: CheckboxGroupDict = context.get_widget_state(
            "checkbox",
            checkbox_group_init,
            f"group:{id_}",
            init_args=(min_selected, max_selected),
        )

    def __enter__(self) -> typing.Self:
        checkbox_group._group_stack.append(self)
        return self

    def __exit__(self, *args, **kwargs):
        checkbox_group._group_stack.pop()


register_widget("checkbox")
