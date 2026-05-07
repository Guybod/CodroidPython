"""
Section banners aligned with C# ``PrintBanner``.

Uses `colorama`_ when installed (extra ``[color]``); otherwise plain ASCII.
Respects ``NO_COLOR``. Does not alter global ``print`` or stdout except when you call ``PrintBanner``.

.. _colorama: https://pypi.org/project/colorama/
"""
from __future__ import annotations

import os
import sys
from typing import Optional

_NO_COLOR = bool(os.environ.get("NO_COLOR", ""))

try:
    from colorama import Fore, Style, init

    init(autoreset=True)
    _COLORAMA = True
except ImportError:
    _COLORAMA = False

    class _E:
        CYAN = GREEN = YELLOW = RED = MAGENTA = WHITE = ""

    class _S:
        BRIGHT = DIM = RESET_ALL = ""

    Fore = _E()
    Style = _S()


def _use_color() -> bool:
    return _COLORAMA and not _NO_COLOR and sys.stdout.isatty()


def PrintBanner(
    title: str,
    subtitle: Optional[str] = None,
    *,
    width: int = 72,
    border: str = "=",
) -> None:
    """
    Print a framed banner (same role as C# ``PrintBanner``).

    With ``colorama`` installed: cyan border, bright green title, dim white subtitle.
    Without it: same layout, no escape codes.
    """
    line = (border * width)[:width] if width > 0 else border
    use = _use_color()

    if use:
        print(Fore.CYAN + line, flush=True)
        print(flush=True)
        print(Fore.GREEN + Style.BRIGHT + title.strip() + Style.RESET_ALL, flush=True)
    else:
        print(line, flush=True)
        print(flush=True)
        print(title.strip(), flush=True)

    if subtitle:
        if use:
            print(
                Fore.WHITE
                + Style.DIM
                + subtitle.strip()
                + Style.RESET_ALL,
                flush=True,
            )
        else:
            print(subtitle.strip(), flush=True)
        print(flush=True)

    if use:
        print(Fore.CYAN + line, flush=True)
    else:
        print(line, flush=True)
