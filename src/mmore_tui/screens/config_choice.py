from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DirectoryTree, Footer, Header, Static

from ..commands import CommandSpec


class ConfigChoiceScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Retour"), ("q", "app.quit", "Quitter")]
    CSS = """
    #choice-row { padding: 2 4; }
    #choice-row Button { width: 100%; margin: 1 0; }
    #choice-title { text-style: bold; padding-bottom: 1; }
    """

    def __init__(self, spec: CommandSpec) -> None:
        super().__init__()
        self.spec = spec

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Vertical(id="choice-row"):
            yield Static(f"Configurer : {self.spec.label}", id="choice-title")
            yield Static(self.spec.description, id="choice-desc")
            yield Button("📂  Utiliser un YAML existant", id="pick", variant="primary")
            yield Button("📝  Générer un YAML par formulaire", id="form")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "pick":
            self.app.push_screen(FilePickerScreen(self.spec))
        elif event.button.id == "form":
            from .config_form import ConfigFormScreen

            if self.spec.dataclass_path is None:
                self.notify(
                    "Cette commande n'a pas de dataclass introspectable. "
                    "Utilisez un YAML existant.",
                    severity="warning",
                )
                return
            self.app.push_screen(ConfigFormScreen(self.spec))


class _YamlOnlyTree(DirectoryTree):
    def filter_paths(self, paths):  # type: ignore[override]
        return [
            p
            for p in paths
            if p.is_dir() or p.suffix.lower() in (".yaml", ".yml")
        ]


class FilePickerScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Retour")]
    CSS = """
    #picker-root { padding: 1 2; }
    #picker-root Static { padding-bottom: 1; }
    DirectoryTree { height: 1fr; border: solid $accent; }
    """

    def __init__(self, spec: CommandSpec) -> None:
        super().__init__()
        self.spec = spec

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Vertical(id="picker-root"):
            yield Static(
                f"Choisir un YAML pour [b]{self.spec.label}[/] (Entrée pour valider)"
            )
            yield _YamlOnlyTree(str(Path.cwd()))
            yield Static("", id="picker-status")
        yield Footer()

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        path = Path(event.path)
        status = self.query_one("#picker-status", Static)
        # Validate against the dataclass if we have one
        if self.spec.dataclass_path is not None:
            try:
                from mmore.utils import load_config

                from ..commands import resolve_dataclass

                load_config(str(path), resolve_dataclass(self.spec))
            except Exception as e:
                status.update(f"[red]Config invalide :[/] {e}")
                return
        status.update(f"[green]OK :[/] {path}")
        from .run import RunScreen

        self.app.push_screen(RunScreen(self.spec, str(path)))
