"""mmore-tui Textual application entrypoint."""

from __future__ import annotations

from textual.app import App

from .screens.home import HomeScreen


class MmoreTuiApp(App):
    TITLE = "mmore-tui"
    SUB_TITLE = "Interface terminale pour mmore"
    BINDINGS = [("q", "quit", "Quitter")]

    def on_mount(self) -> None:
        self.push_screen(HomeScreen())


def main() -> None:
    """Console-script entrypoint registered in pyproject.toml."""
    MmoreTuiApp().run()


if __name__ == "__main__":
    main()
