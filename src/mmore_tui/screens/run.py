from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, RichLog, Static

from ..commands import CommandSpec, resolve
from ..runner import run_blocking


class RunScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Retour")]
    CSS = """
    #run-root { height: 1fr; padding: 1 2; }
    #run-status { padding-bottom: 1; text-style: bold; }
    RichLog { height: 1fr; border: solid $accent; }
    #run-actions Button { margin-top: 1; margin-right: 2; }
    """

    def __init__(
        self,
        spec: CommandSpec,
        config_path: str,
        input_data: str | None = None,
    ) -> None:
        super().__init__()
        self.spec = spec
        self.config_path = config_path
        self.input_data = input_data
        self._log: RichLog | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Vertical(id="run-root"):
            yield Static(
                f"⏳  Exécution : [b]{self.spec.label}[/]  ({self.config_path})",
                id="run-status",
            )
            yield RichLog(highlight=True, markup=True, wrap=True)
            yield Button("Retour au menu", id="back")
        yield Footer()

    def on_mount(self) -> None:
        self._log = self.query_one(RichLog)
        self.run_worker(self._execute, thread=True, exclusive=True)

    def _sink(self, line: str) -> None:
        # Worker thread → use call_from_thread to push UI update.
        if self._log is not None:
            self.app.call_from_thread(self._log.write, line)

    def _execute(self) -> None:
        spec = self.spec

        def target():
            fn = resolve(spec)
            if spec.call_kind == "config_input":
                if self.input_data is None:
                    raise ValueError("postprocess requires an input JSONL")
                fn(self.config_path, self.input_data)
            elif spec.call_kind == "ragcli":
                # ragcli is interactive — should not be reached via RunScreen.
                raise RuntimeError("Use the chat screen for ragcli")
            else:
                fn(self.config_path)

        result = run_blocking(target, self._sink)
        status = self.query_one("#run-status", Static)
        if result.ok:
            self.app.call_from_thread(status.update, f"✔  Terminé : {self.spec.label}")
        else:
            self.app.call_from_thread(status.update, f"✘  Échec : {self.spec.label}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
