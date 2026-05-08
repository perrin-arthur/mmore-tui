from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, ListItem, ListView, Static

from ..commands import COMMANDS, CommandSpec


class CommandListScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Retour"), ("q", "app.quit", "Quitter")]
    CSS = """
    #cmd-row { height: 1fr; }
    #cmd-list { width: 30; border-right: solid $accent; }
    #cmd-detail { padding: 1 2; }
    #cmd-detail .title { text-style: bold; padding-bottom: 1; }
    """

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="cmd-row"):
            yield ListView(
                *[ListItem(Static(c.label), id=f"cmd-{c.name}") for c in COMMANDS],
                id="cmd-list",
            )
            with Vertical(id="cmd-detail"):
                yield Static("", id="cmd-title", classes="title")
                yield Static("", id="cmd-desc")
                yield Static(
                    "[dim]Entrée : configurer cette commande[/]",
                    id="cmd-hint",
                )
        yield Footer()

    def on_mount(self) -> None:
        list_view = self.query_one(ListView)
        list_view.focus()
        if COMMANDS:
            self._show(COMMANDS[0])

    def _show(self, spec: CommandSpec) -> None:
        self.query_one("#cmd-title", Static).update(spec.label)
        self.query_one("#cmd-desc", Static).update(spec.description)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item is None or event.item.id is None:
            return
        name = event.item.id.removeprefix("cmd-")
        spec = next((c for c in COMMANDS if c.name == name), None)
        if spec:
            self._show(spec)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item is None or event.item.id is None:
            return
        name = event.item.id.removeprefix("cmd-")
        spec = next((c for c in COMMANDS if c.name == name), None)
        if spec:
            from .config_choice import ConfigChoiceScreen

            self.app.push_screen(ConfigChoiceScreen(spec))
