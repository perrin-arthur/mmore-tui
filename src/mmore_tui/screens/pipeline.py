"""End-to-end pipeline: process → postprocess → index → chat.

We delegate each stage to the existing per-command screens
(ConfigChoiceScreen → RunScreen). The user picks/generates a config for
each step, watches it run, then advances. Output paths are not auto-piped
between stages in v1 — mmore writes outputs to paths defined inside each
stage's config, and threading them automatically would require parsing
each dataclass for its output field. For now we display the resolved
config so the user can copy paths if needed.
"""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static

from ..commands import get_command


PIPELINE_STAGES = ["process", "postprocess", "index", "ragcli"]


class PipelineScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Retour")]
    CSS = """
    #pipe-root { padding: 2 4; }
    #pipe-root Static { padding-bottom: 1; }
    #pipe-root Button { width: 100%; margin: 1 0; }
    .breadcrumb { color: $text-muted; }
    """

    def __init__(self) -> None:
        super().__init__()
        self.stage_index = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Vertical(id="pipe-root"):
            yield Static(self._breadcrumb(), id="pipe-crumb", classes="breadcrumb")
            yield Static(
                "La pipeline enchaîne les étapes mmore canoniques. "
                "Pour chaque étape, choisissez un YAML existant ou générez-en un.",
            )
            yield Button("▶  Étape suivante", id="next", variant="primary")
            yield Button("Retour à l'accueil", id="home")
        yield Footer()

    def _breadcrumb(self) -> str:
        parts = []
        for i, s in enumerate(PIPELINE_STAGES):
            if i < self.stage_index:
                parts.append(f"[green]✓ {s}[/]")
            elif i == self.stage_index:
                parts.append(f"[b]▶ {s}[/]")
            else:
                parts.append(f"[dim]{s}[/]")
        return "   ".join(parts)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "home":
            self.app.pop_screen()
            return
        if event.button.id == "next":
            if self.stage_index >= len(PIPELINE_STAGES):
                self.app.pop_screen()
                return
            stage = PIPELINE_STAGES[self.stage_index]
            self.stage_index += 1
            self.query_one("#pipe-crumb", Static).update(self._breadcrumb())
            spec = get_command(stage)
            if stage == "ragcli":
                from .chat import ChatRunScreen

                self.app.push_screen(ChatRunScreen(spec))
            else:
                from .config_choice import ConfigChoiceScreen

                self.app.push_screen(ConfigChoiceScreen(spec))
