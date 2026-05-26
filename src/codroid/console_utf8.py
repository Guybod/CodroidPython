"""
Windows 控制台 UTF-8（与 C++ ``console_utf8.hpp`` / C# ``ConsoleUtf8`` 对齐）。

官方示例应在 ``if __name__ == "__main__"`` 首行调用 ``InitConsoleUtf8()``；
非 Windows 平台为 no-op。
"""
from __future__ import annotations

import sys


def init_console_utf8() -> None:
    """Windows：控制台与 stdout/stderr 统一 UTF-8；其它平台 no-op。"""
    if sys.platform != "win32":
        return
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass
    try:
        import ctypes

        k32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        k32.SetConsoleOutputCP(65001)
        k32.SetConsoleCP(65001)
    except OSError:
        pass


InitConsoleUtf8 = init_console_utf8
