"""Smoke test: launch the app under Textual's Pilot and navigate Home → CommandList."""

from __future__ import annotations

import pytest

from mmore_tui.app import MmoreTuiApp


@pytest.mark.asyncio
async def test_home_to_command_list():
    app = MmoreTuiApp()
    async with app.run_test() as pilot:
        # The home card shows three buttons; clicking the first pushes CommandListScreen.
        await pilot.click("#cmd")
        await pilot.pause()
        # After the push, the topmost screen should be CommandListScreen.
        from mmore_tui.screens.command_list import CommandListScreen

        assert isinstance(app.screen, CommandListScreen)


@pytest.mark.asyncio
async def test_quits_cleanly():
    app = MmoreTuiApp()
    async with app.run_test() as pilot:
        await pilot.press("q")
        await pilot.pause()
    # Reaching here means the app exited without raising.
