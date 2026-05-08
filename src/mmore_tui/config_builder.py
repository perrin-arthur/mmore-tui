"""Introspect a dataclass / Pydantic model and emit form field specs.

The output is a flat-ish list of FieldSpec objects that the Textual form
screen turns into widgets. Nested dataclasses produce a nested
FieldSpec.children list; the form renders those inside a Collapsible.

This module is pure Python — no Textual import — so it can be unit-tested
without booting the UI.
"""

from __future__ import annotations

import dataclasses
import types
from dataclasses import dataclass, field
from typing import Any, Optional, Union, get_args, get_origin


# Widget kinds the form screen knows how to render.
KIND_STR = "str"
KIND_INT = "int"
KIND_FLOAT = "float"
KIND_BOOL = "bool"
KIND_SELECT = "select"  # for Literal / Enum-like
KIND_LIST_STR = "list_str"
KIND_NESTED = "nested"
KIND_FREEFORM = "freeform"  # fallback: YAML snippet input


@dataclass
class FieldSpec:
    name: str
    kind: str
    type_repr: str
    required: bool = True
    default: Any = None
    optional: bool = False  # True when the annotation is Optional[...]
    choices: list[str] = field(default_factory=list)
    children: list["FieldSpec"] = field(default_factory=list)
    help: str = ""


_MISSING = object()


def _is_dataclass_type(tp: Any) -> bool:
    return isinstance(tp, type) and dataclasses.is_dataclass(tp)


def _is_pydantic_model(tp: Any) -> bool:
    try:
        from pydantic import BaseModel  # type: ignore
    except ImportError:
        return False
    return isinstance(tp, type) and issubclass(tp, BaseModel)


def _unwrap_optional(tp: Any) -> tuple[Any, bool]:
    """Return (inner_type, is_optional). Handles Optional[X] and X | None."""
    origin = get_origin(tp)
    if origin in (Union, types.UnionType):
        args = [a for a in get_args(tp) if a is not type(None)]
        if len(args) == 1 and len(get_args(tp)) == 2:
            return args[0], True
        # Unsupported Union → treat as freeform
        return tp, False
    return tp, False


def build_specs(target: type) -> list[FieldSpec]:
    """Build form specs for a dataclass or Pydantic model class."""
    if _is_dataclass_type(target):
        return _from_dataclass(target)
    if _is_pydantic_model(target):
        return _from_pydantic(target)
    raise TypeError(f"Unsupported config type: {target!r}")


def _from_dataclass(cls: type) -> list[FieldSpec]:
    import typing

    try:
        hints = typing.get_type_hints(cls)
    except Exception:
        hints = {}
    specs: list[FieldSpec] = []
    for f in dataclasses.fields(cls):
        default: Any
        if f.default is not dataclasses.MISSING:
            default = f.default
            required = False
        elif f.default_factory is not dataclasses.MISSING:  # type: ignore[misc]
            try:
                default = f.default_factory()  # type: ignore[misc]
            except Exception:
                default = None
            required = False
        else:
            default = None
            required = True
        annotation = hints.get(f.name, f.type)
        specs.append(_field_spec(f.name, annotation, default, required))
    return specs


def _from_pydantic(cls: type) -> list[FieldSpec]:
    specs: list[FieldSpec] = []
    for name, info in cls.model_fields.items():  # type: ignore[attr-defined]
        annotation = info.annotation
        required = info.is_required()
        default = None if required else info.default
        specs.append(_field_spec(name, annotation, default, required))
    return specs


def _field_spec(name: str, annotation: Any, default: Any, required: bool) -> FieldSpec:
    inner, optional = _unwrap_optional(annotation)
    type_repr = _type_repr(annotation)

    # Nested dataclass / Pydantic model
    if _is_dataclass_type(inner) or _is_pydantic_model(inner):
        return FieldSpec(
            name=name,
            kind=KIND_NESTED,
            type_repr=type_repr,
            required=required,
            default=default,
            optional=optional,
            children=build_specs(inner),
        )

    origin = get_origin(inner)

    if _is_literal(inner):
        return FieldSpec(
            name=name,
            kind=KIND_SELECT,
            type_repr=type_repr,
            required=required,
            default=default,
            optional=optional,
            choices=[str(a) for a in get_args(inner)],
        )

    # List[str] (or list[str])
    if origin in (list,) and get_args(inner) and get_args(inner)[0] is str:
        return FieldSpec(
            name=name,
            kind=KIND_LIST_STR,
            type_repr=type_repr,
            required=required,
            default=default,
            optional=optional,
        )

    # Primitives
    if inner is str:
        kind = KIND_STR
    elif inner is bool:
        kind = KIND_BOOL
    elif inner is int:
        kind = KIND_INT
    elif inner is float:
        kind = KIND_FLOAT
    else:
        kind = KIND_FREEFORM

    return FieldSpec(
        name=name,
        kind=kind,
        type_repr=type_repr,
        required=required,
        default=default,
        optional=optional,
    )


def _is_literal(tp: Any) -> bool:
    try:
        from typing import Literal

        return get_origin(tp) is Literal
    except Exception:
        return False


def _type_repr(tp: Any) -> str:
    try:
        return tp.__name__  # type: ignore[union-attr]
    except AttributeError:
        return str(tp).replace("typing.", "")


def specs_to_dict(specs: list[FieldSpec], values: dict[str, Any]) -> dict[str, Any]:
    """Materialise the user's values into a YAML-serialisable dict.

    `values` is keyed by the dotted path of the field
    (e.g. "dispatcher_config.endpoint"). Nested specs recurse.
    """
    out: dict[str, Any] = {}
    for s in specs:
        if s.kind == KIND_NESTED:
            sub = specs_to_dict(s.children, _scope(values, s.name))
            if sub or s.required:
                out[s.name] = sub
            continue
        if s.name in values and values[s.name] is not None and values[s.name] != "":
            out[s.name] = values[s.name]
        elif s.required and s.default is not None:
            out[s.name] = s.default
    return out


def _scope(values: dict[str, Any], prefix: str) -> dict[str, Any]:
    p = f"{prefix}."
    return {k[len(p):]: v for k, v in values.items() if k.startswith(p)}
