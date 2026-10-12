import sys
import threading
import time
from pathlib import Path

import pytest

from app.core import proc

PY = sys.executable


def test_passes_tricky_paths_untouched(tmp_path: Path) -> None:
    weird = tmp_path / "Bài hát & thử (1) 'x'.txt"
    weird.write_text("xin chào", encoding="utf-8")
    code = "import sys; print(open(sys.argv[1], encoding='utf-8').read())"
    r = proc.run([PY, "-c", code, weird])
    assert r.ok
    assert r.stdout.decode("utf-8").strip() == "xin chào"


def test_nonzero_exit_is_reported_not_raised() -> None:
    r = proc.run([PY, "-c", "import sys; sys.stderr.write('boom'); sys.exit(3)"])
    assert r.returncode == 3 and not r.ok
    assert "boom" in r.stderr_text()


def test_cancel_kills_process_tree_quickly() -> None:
    cancel = threading.Event()
    child = (
        "import subprocess, sys, time; "
        "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); "
        "time.sleep(60)"
    )
    threading.Timer(0.3, cancel.set).start()
    t0 = time.monotonic()
    with pytest.raises(proc.Cancelled):
        proc.run([PY, "-c", child], cancel=cancel)
    assert time.monotonic() - t0 < 5


def test_timeout() -> None:
    with pytest.raises(TimeoutError):
        proc.run([PY, "-c", "import time; time.sleep(30)"], timeout=0.3)


def test_streams_stdout_lines() -> None:
    lines: list[str] = []
    r = proc.run([PY, "-c", "print('a'); print('b=2')"], on_stdout_line=lines.append)
    assert r.ok and lines == ["a", "b=2"]
