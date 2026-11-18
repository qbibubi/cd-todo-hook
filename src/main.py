"""Proof of Concept for a cd-todo project

The project is a small tool to help me with my own todo lists
in a git repistory. This program runs after `cd` in both Linux
and Windows operating systems and check whether the current
directory is a git repository. If it is then it checks for a
presence of `todo.md` file and displays it's contets to get back
on track with what is already being done and develped in a terminal

The program would have to be added to path in a proper manner depending
on the Windows and Linux versions. Since this is a simple script and tool
it does not require C alternative.
"""
import os
import sys
import subprocess
from pathlib import Path


# --- ANSI styling -----------------------------------------------------------
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
STRIKE = "\033[9m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
GREEN = "\033[32m"

# --- box drawing -------------------------------------------------------------
TOP_LEFT, TOP_RIGHT = "┌", "┐"      # ┌ ┐
BOT_LEFT, BOT_RIGHT = "└", "┘"      # └ ┘
HORIZONTAL, VERTICAL = "─", "│"     # ─ │

CHECK_DONE = "✔"   # ✔
CHECK_TODO = "☐"   # ☐
BULLET = "•"        # •


def enable_ansi_output():
    """Prepares the console so styled, UTF-8 output renders correctly.

    Reconfigures stdout to UTF-8 (so box-drawing glyphs survive on Windows)
    and enables virtual-terminal processing so ANSI escapes are honoured on
    Windows 10+ consoles. Both are best-effort and silently skipped if the
    environment does not support them."""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            kernel32.SetConsoleMode(handle, mode.value | 0x0004)
    except Exception:
        pass


def get_git_root():
    """Finds the root of a git repository if the repository is nested

    Returns git repository root; else None"""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def read_output(path):
    """Reads output from a path based on the console environment encoding in Windows OS

    First bytes dictates encoding requiring proper decoding method"""
    data = path.read_bytes()

    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16").strip()
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig").strip()
    try:
        return data.decode("utf-8").strip()
    except UnicodeDecodeError:
        return data.decode("cp1252").strip()


def render_line(line: str):
    """Renders one markdown line into a (styled, plain) pair.

    `styled` carries ANSI escapes for display; `plain` is the same text with
    no escapes, so the banner can measure the visible width for padding."""
    stripped = line.rstrip()
    if not stripped.strip():
        return "", ""

    body = stripped.lstrip()
    indent = stripped[: len(stripped) - len(body)]

    # Heading parsing from # ... up to ###### ...
    if body.startswith("#"):
        """@TODO: As a proof of concept this is fine for now. This can be
        be expanded much much more with better capabilities"""
        level = len(body) - len(body.lstrip("#"))
        text = body[level:].strip()
        if level == 1:
            plain = text.upper()
            styled = f"{BOLD}{CYAN}{plain}{RESET}"
        # @TODO: These levels can be handled later
        # elif level == 2:
        # elif level == 3:
        # elif level == 4:
        else:
            plain = text
            styled = f"{BOLD}{YELLOW}{plain}{RESET}"
        return styled, plain
    
    # Task checkboxes: - [ ] / - [x]
    if body[:5] in ("- [ ]", "- [x]", "- [X]"):
        checked = body[3].lower() == "x"
        text = body[5:].strip()
        if checked:
            plain = f"{indent}{CHECK_DONE} {text}"
            styled = f"{indent}{GREEN}{CHECK_DONE}{RESET} {DIM}{STRIKE}{text}{RESET}"
        else:
            plain = f"{indent}{CHECK_TODO} {text}"
            styled = f"{indent}{CHECK_TODO} {text}"
        return styled, plain

    # Bullet lists: - item / * item
    if body[:2] in ("- ", "* "):
        text = body[2:].strip()
        plain = f"{indent}{BULLET} {text}"
        styled = f"{indent}{BULLET} {text}"
        return styled, plain

    return stripped, stripped


def print_banner(root: Path, todo_filename: str):
    """Prints a bordered, markdown-rendered banner for the repository's todo list."""
    todo_file = root / todo_filename
    if not todo_file.is_file():
        return

    todo_output = read_output(todo_file)
    if len(todo_output) == 0:
        return

    rendered = [render_line(line) for line in todo_output.splitlines()]
    inner_width = max((len(plain) for _, plain in rendered), default=0)

    print(f"{TOP_LEFT}{HORIZONTAL * (inner_width + 2)}{TOP_RIGHT}")
    for styled, plain in rendered:
        padding = " " * (inner_width - len(plain))
        print(f"{VERTICAL} {styled}{padding} {VERTICAL}")
    print(f"{BOT_LEFT}{HORIZONTAL * (inner_width + 2)}{BOT_RIGHT}")


def main():
    git_root = get_git_root()
    if git_root is None:
        return

    enable_ansi_output()
    print_banner(git_root, "todo.md")


if __name__ == "__main__":
    main()
