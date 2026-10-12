"""The ONLY place allowed to start external processes (FFmpeg, ffprobe, yt-dlp).

Rules (docs/CODING-GUIDE.md §6.2): argument lists only — never shell=True, so file names with
Vietnamese characters, spaces or '&' are passed through untouched; no console window on Windows;
every process can be cancelled, and cancelling kills the whole process tree.
"""

from __future__ import annotations

import contextlib
import logging
import os
import signal
import subprocess
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

Arg = str | Path
CREATE_NO_WINDOW = 0x08000000


class Cancelled(Exception):
    """Raised when a cancel event fires while a process is running."""


@dataclass(frozen=True)
class ProcResult:
    args: list[str]
    returncode: int
    stdout: bytes
    stderr: bytes

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    def stderr_text(self, limit: int = 2000) -> str:
        return self.stderr.decode("utf-8", errors="replace")[-limit:]


def _popen(args: list[str], cwd: Path | None) -> subprocess.Popen[bytes]:
    if os.name == "nt":
        return subprocess.Popen(
            args,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=CREATE_NO_WINDOW,
        )
    return subprocess.Popen(
        args,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,  # own process group → killpg
    )


def kill_tree(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
            creationflags=CREATE_NO_WINDOW,
            check=False,
        )
    else:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(proc.pid, signal.SIGKILL)
    proc.wait()


def _drain(stream: object, sink: bytearray) -> None:
    for chunk in iter(lambda: stream.read(65536), b""):  # type: ignore[attr-defined]
        sink.extend(chunk)


def run(
    args: Sequence[Arg],
    *,
    cancel: threading.Event | None = None,
    timeout: float | None = None,
    cwd: Path | None = None,
    on_stdout_line: Callable[[str], None] | None = None,
) -> ProcResult:
    """Run to completion. With on_stdout_line, stdout is streamed line by line (for -progress)."""
    argv = [str(a) for a in args]
    proc = _popen(argv, cwd)
    assert proc.stdout and proc.stderr
    out, err = bytearray(), bytearray()
    t_err = threading.Thread(target=_drain, args=(proc.stderr, err), daemon=True)
    t_err.start()
    if on_stdout_line:

        def _lines() -> None:
            assert proc.stdout
            for raw in iter(proc.stdout.readline, b""):
                out.extend(raw)
                on_stdout_line(raw.decode("utf-8", errors="replace").rstrip("\r\n"))

        t_out = threading.Thread(target=_lines, daemon=True)
    else:
        t_out = threading.Thread(target=_drain, args=(proc.stdout, out), daemon=True)
    t_out.start()

    waited = 0.0
    while True:
        try:
            proc.wait(timeout=0.1)
            break
        except subprocess.TimeoutExpired:
            waited += 0.1
            if cancel is not None and cancel.is_set():
                kill_tree(proc)
                raise Cancelled(argv[0]) from None
            if timeout is not None and waited >= timeout:
                kill_tree(proc)
                raise TimeoutError(f"{argv[0]} timed out after {timeout}s") from None
    t_out.join()
    t_err.join()
    result = ProcResult(argv, proc.returncode, bytes(out), bytes(err))
    if not result.ok:
        log.warning("process failed (%s): %s\n%s", result.returncode, argv, result.stderr_text())
    return result
