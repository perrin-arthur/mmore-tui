"""Run a mmore command in a worker thread, streaming logs to a RichLog."""

from __future__ import annotations

import contextlib
import io
import logging
import traceback
from dataclasses import dataclass
from typing import Callable, Optional


class _LogStreamer(logging.Handler):
    def __init__(self, sink: Callable[[str], None]):
        super().__init__()
        self.sink = sink
        self.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s — %(message)s", "%H:%M:%S"))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.sink(self.format(record))
        except Exception:
            pass


@dataclass
class RunResult:
    ok: bool
    error: Optional[str] = None


def run_blocking(target: Callable[[], object], sink: Callable[[str], None]) -> RunResult:
    """Run `target()` synchronously, routing logs and stdout/stderr to `sink`.

    Intended to be invoked from a Textual @work(thread=True) worker.
    """
    handler = _LogStreamer(sink)
    root = logging.getLogger()
    prev_level = root.level
    root.addHandler(handler)
    if root.level > logging.INFO:
        root.setLevel(logging.INFO)

    stdout_buf = _LineBuffer(sink)
    stderr_buf = _LineBuffer(sink, prefix="[stderr] ")

    try:
        with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
            target()
        stdout_buf.flush()
        stderr_buf.flush()
        return RunResult(ok=True)
    except Exception as e:
        stdout_buf.flush()
        stderr_buf.flush()
        sink("[bold red]✘ Erreur :[/]")
        for line in traceback.format_exception(e):
            sink(line.rstrip())
        return RunResult(ok=False, error=str(e))
    finally:
        root.removeHandler(handler)
        root.setLevel(prev_level)


class _LineBuffer(io.TextIOBase):
    def __init__(self, sink: Callable[[str], None], prefix: str = ""):
        super().__init__()
        self._sink = sink
        self._prefix = prefix
        self._buf = ""

    def write(self, s: str) -> int:  # type: ignore[override]
        self._buf += s
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            self._sink(self._prefix + line)
        return len(s)

    def flush(self) -> None:  # type: ignore[override]
        if self._buf:
            self._sink(self._prefix + self._buf)
            self._buf = ""
