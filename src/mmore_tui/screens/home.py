from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Static


class HomeScreen(Screen):
    BINDINGS = [("q", "app.quit", "Quitter")]
    CSS = """
    HomeScreen { align: center middle; }
    #home-card { width: 70; padding: 2 4; border: round $accent; }
    #home-card .title { content-align: center middle; text-style: bold; padding-bottom: 1; }
    #home-card Button { width: 100%; margin: 1 0; }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Vertical(id="home-card"):
            yield Static("mmore-tui", classes="title")
            yield Static(
                "Bienvenue. Choisissez ce que vous voulez faire :",
                classes="subtitle",
            )
            yield Button("▶  Lancer une commande", id="cmd", variant="primary")
            yield Button("⚙  Pipeline complète (process → index → chat)", id="pipeline")
            yield Button("💬  Chat avec mes documents indexés", id="chat")
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        from .command_list import CommandListScreen
        from .pipeline import PipelineScreen
        from .chat import ChatLauncherScreen

        if event.button.id == "cmd":
            self.app.push_screen(CommandListScreen())
        elif event.button.id == "pipeline":
            self.app.push_screen(PipelineScreen())
        elif event.button.id == "chat":
            self.app.push_screen(ChatLauncherScreen())
