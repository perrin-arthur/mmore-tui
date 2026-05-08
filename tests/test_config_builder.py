"""Unit tests for config_builder — pure introspection, no Textual."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

import pytest

from mmore_tui.config_builder import (
    KIND_BOOL,
    KIND_INT,
    KIND_LIST_STR,
    KIND_NESTED,
    KIND_SELECT,
    KIND_STR,
    build_specs,
    specs_to_dict,
)


@dataclass
class Inner:
    endpoint: str = "http://localhost"
    port: int = 8000


@dataclass
class Outer:
    name: str
    enabled: bool = False
    mode: Literal["fast", "slow"] = "fast"
    tags: list[str] = field(default_factory=list)
    note: Optional[str] = None
    inner: Inner = field(default_factory=Inner)


def test_primitive_kinds():
    specs = build_specs(Outer)
    by_name = {s.name: s for s in specs}
    assert by_name["name"].kind == KIND_STR
    assert by_name["name"].required is True
    assert by_name["enabled"].kind == KIND_BOOL
    assert by_name["mode"].kind == KIND_SELECT
    assert by_name["mode"].choices == ["fast", "slow"]
    assert by_name["tags"].kind == KIND_LIST_STR
    assert by_name["note"].optional is True


def test_nested_dataclass_recurses():
    specs = build_specs(Outer)
    inner = next(s for s in specs if s.name == "inner")
    assert inner.kind == KIND_NESTED
    child_names = {c.name for c in inner.children}
    assert child_names == {"endpoint", "port"}
    port = next(c for c in inner.children if c.name == "port")
    assert port.kind == KIND_INT


def test_specs_to_dict_filters_empty_and_nests():
    specs = build_specs(Outer)
    flat = {
        "name": "thing",
        "enabled": True,
        "mode": "slow",
        "tags": ["a", "b"],
        # note: not provided
        "inner.endpoint": "http://x",
        "inner.port": 9000,
    }
    out = specs_to_dict(specs, flat)
    assert out["name"] == "thing"
    assert out["enabled"] is True
    assert out["mode"] == "slow"
    assert out["tags"] == ["a", "b"]
    assert "note" not in out
    assert out["inner"] == {"endpoint": "http://x", "port": 9000}


@pytest.mark.parametrize(
    "import_path",
    [
        "mmore.run_process:ProcessInference",
        "mmore.run_index:IndexConfig",
        "mmore.run_rag:RAGInferenceConfig",
    ],
)
def test_real_mmore_dataclasses_introspect(import_path: str):
    """If mmore is installed, build_specs must not crash on its real configs."""
    pytest.importorskip("mmore")
    module_name, attr = import_path.split(":")
    import importlib

    try:
        cls = getattr(importlib.import_module(module_name), attr)
    except ModuleNotFoundError as e:
        pytest.skip(f"mmore optional dep missing: {e.name}")
    specs = build_specs(cls)
    assert specs, f"no specs produced for {import_path}"
