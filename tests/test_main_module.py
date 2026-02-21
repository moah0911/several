from __future__ import annotations

import runpy
import sys


def test_main_module_executes_version(monkeypatch) -> None:
    monkeypatch.setattr(sys, "argv", ["several", "--version"])
    try:
        runpy.run_module("several.__main__", run_name="__main__")
    except SystemExit as exc:
        assert exc.code == 0
