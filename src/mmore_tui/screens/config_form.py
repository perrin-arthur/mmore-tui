"""Dynamic form screen built from a dataclass via config_builder."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Button,
    Collapsible,
    Footer,
    Header,
    Input,
    Label,
    Select,
    Static,
    Switch,
)

from ..commands import CommandSpec, resolve_dataclass
from ..config_builder import (
    KIND_BOOL,
    KIND_FLOAT,
    KIND_FREEFORM,
    KIND_INT,
    KIND_LIST_STR,
    KIND_NESTED,
    KIND_SELECT,
    KIND_STR,
    FieldSpec,
    build_specs,
    specs_to_dict,
)


class ConfigFormScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Annuler")]
    CSS = """
    #form-root { padding: 1 2; }
    #form-fields { height: 1fr; border: solid $accent; padding: 1; }
    .field-row { padding: 0 0 1 0; }
    .field-label { color: $text-muted; }
    #form-actions Button { margin-right: 2; }
    """

    def __init__(self, spec: CommandSpec) -> None:
        super().__init__()
        self.spec = spec
        cls = resolve_dataclass(spec)
        if cls is None:
            raise RuntimeError(f"{spec.name} has no dataclass")
        self.specs: list[FieldSpec] = build_specs(cls)
        self._inputs: dict[str, Any] = {}  # dotted-path -> widget

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Vertical(id="form-root"):
            yield Static(f"Générer un YAML pour [b]{self.spec.label}[/]")
            with VerticalScroll(id="form-fields"):
                for fs in self.specs:
                    yield from self._render(fs, prefix="")
            with Horizontal(id="form-actions"):
                yield Button("💾  Sauvegarder & lancer", id="save-run", variant="primary")
                yield Button("Sauvegarder seulement", id="save-only")
                yield Button("Annuler", id="cancel")
        yield Footer()

    def _render(self, fs: FieldSpec, prefix: str):
        path = f"{prefix}{fs.name}"
        label = f"{fs.name}  [dim]({fs.type_repr})[/]" + (
            "" if fs.required else "  [dim italic]optionnel[/]"
        )
        if fs.kind == KIND_NESTED:
            with Collapsible(title=fs.name, collapsed=not fs.required):
                yield Static(label, classes="field-label")
                for child in fs.children:
                    yield from self._render(child, prefix=f"{path}.")
            return

        with Vertical(classes="field-row"):
            yield Label(label, classes="field-label")
            widget: Any
            if fs.kind == KIND_BOOL:
                widget = Switch(value=bool(fs.default))
            elif fs.kind == KIND_SELECT and fs.choices:
                opts = [(c, c) for c in fs.choices]
                widget = Select(opts, value=str(fs.default) if fs.default in fs.choices else Select.BLANK)
            elif fs.kind == KIND_INT:
                widget = Input(
                    value="" if fs.default is None else str(fs.default),
                    placeholder="entier",
                    type="integer",
                )
            elif fs.kind == KIND_FLOAT:
                widget = Input(
                    value="" if fs.default is None else str(fs.default),
                    placeholder="nombre",
                    type="number",
                )
            elif fs.kind == KIND_LIST_STR:
                widget = Input(
                    value="" if not fs.default else ",".join(fs.default),
                    placeholder="valeurs séparées par des virgules",
                )
            elif fs.kind == KIND_FREEFORM:
                widget = Input(
                    value="" if fs.default is None else yaml.safe_dump(fs.default).strip(),
                    placeholder="snippet YAML",
                )
            else:  # KIND_STR and fallback
                widget = Input(
                    value="" if fs.default is None else str(fs.default),
                    placeholder=fs.type_repr,
                )
            self._inputs[path] = (fs, widget)
            yield widget

    def _collect(self) -> dict[str, Any]:
        flat: dict[str, Any] = {}
        for path, (fs, widget) in self._inputs.items():
            v = self._read_widget(fs, widget)
            if v is not None:
                flat[path] = v
        return specs_to_dict(self.specs, flat)

    def _read_widget(self, fs: FieldSpec, widget) -> Any:
        if fs.kind == KIND_BOOL:
            return widget.value
        if fs.kind == KIND_SELECT:
            return None if widget.value is Select.BLANK else widget.value
        text = widget.value.strip() if isinstance(widget.value, str) else widget.value
        if text == "" or text is None:
            return None
        if fs.kind == KIND_INT:
            try:
                return int(text)
            except ValueError:
                return None
        if fs.kind == KIND_FLOAT:
            try:
                return float(text)
            except ValueError:
                return None
        if fs.kind == KIND_LIST_STR:
            return [s.strip() for s in text.split(",") if s.strip()]
        if fs.kind == KIND_FREEFORM:
            try:
                return yaml.safe_load(text)
            except yaml.YAMLError:
                return text
        return text

    def _write_yaml(self, data: dict[str, Any]) -> Path:
        out_dir = Path("tui-configs")
        out_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = out_dir / f"{self.spec.name}-{ts}.yaml"
        with path.open("w") as f:
            yaml.safe_dump(data, f, sort_keys=False)
        return path

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()
            return
        data = self._collect()
        path = self._write_yaml(data)
        self.notify(f"YAML écrit : {path}", severity="information")
        if event.button.id == "save-run":
            from .run import RunScreen

            self.app.push_screen(RunScreen(self.spec, str(path)))
