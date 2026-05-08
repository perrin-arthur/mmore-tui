"""RAG chat screen.

Wraps mmore.run_ragcli.RagCLI. RagCLI exposes a `do_rag(query)` method we
can call directly without taking over stdin — perfect for embedding in
Textual. The launcher screen lets the user pick a YAML rag config first.
"""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DirectoryTree, Footer, Header, Input, RichLog, Static

from ..commands import get_command


class ChatLauncherScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Retour")]
    CSS = """
    #chat-launcher { padding: 1 2; }
    DirectoryTree { height: 1fr; border: solid $accent; }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Vertical(id="chat-launcher"):
            yield Static("Choisir le YAML de config RAG :")
            yield DirectoryTree(str(Path.cwd()))
            yield Static("", id="chat-status")
        yield Footer()

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        path = Path(event.path)
        if path.suffix.lower() not in (".yaml", ".yml"):
            self.query_one("#chat-status", Static).update("[red]Sélectionnez un .yaml[/]")
            return
        spec = get_command("ragcli")
        self.app.push_screen(ChatRunScreen(spec, str(path)))


class ChatRunScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Retour")]
    CSS = """
    #chat-root { height: 1fr; padding: 1 2; }
    RichLog { height: 1fr; border: solid $accent; }
    #chat-prompt { dock: bottom; }
    """

    def __init__(self, spec, config_path: str | None = None) -> None:
        super().__init__()
        self.spec = spec
        self.config_path = config_path
        self._rag = None
        self._log: RichLog | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Vertical(id="chat-root"):
            yield Static(f"💬  Chat RAG  ({self.config_path or '— pas de config —'})")
            yield RichLog(highlight=True, markup=True, wrap=True)
            yield Input(placeholder="Posez votre question…", id="chat-prompt")
        yield Footer()

    def on_mount(self) -> None:
        self._log = self.query_one(RichLog)
        if self.config_path is None:
            self._log.write("[red]Aucun config fourni — retournez à l'accueil.[/]")
            return
        self._log.write("[dim]Initialisation du RAG…[/]")
        self.run_worker(self._init_rag, thread=True, exclusive=True)

    def _init_rag(self) -> None:
        from mmore.run_ragcli import RagCLI

        try:
            cli = RagCLI(self.config_path)
            cli.init_config()
            cli.initialize_ragpp()
            self._rag = cli
            self.app.call_from_thread(self._log.write, "[green]Prêt.[/]")
        except Exception as e:  # noqa: BLE001
            self.app.call_from_thread(
                self._log.write, f"[red]Erreur init RAG :[/] {e}"
            )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if self._rag is None:
            self._log.write("[red]RAG non initialisé.[/]")
            return
        query = event.value.strip()
        if not query:
            return
        event.input.value = ""
        self._log.write(f"[b cyan]?[/] {query}")
        self.run_worker(lambda q=query: self._answer(q), thread=True)

    def _answer(self, query: str) -> None:
        try:
            answer = self._rag.do_rag(query)
        except Exception as e:  # noqa: BLE001
            self.app.call_from_thread(self._log.write, f"[red]Erreur :[/] {e}")
            return
        self.app.call_from_thread(self._log.write, f"[b green]→[/] {answer}")
