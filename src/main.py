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
import re
import sys
import subprocess
import unicodedata
from pathlib import Path
from dataclasses import dataclass


# --- ANSI styling -----------------------------------------------------------
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
STRIKE = "\033[9m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
GREEN = "\033[32m"

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


# --- themeable glyphs -------------------------------------------------------
@dataclass(frozen=True)
class Theme:
    """A swappable set of glyphs for the banner.

    Keeping every glyph here (instead of scattered literals) means the look
    can be changed in one place, and new presets added without touching the
    rendering logic. Widths are measured at render time, so a preset may use
    any glyphs that render single-width in the target terminal."""
    top_left: str
    top_right: str
    bot_left: str
    bot_right: str
    sep_left: str
    sep_right: str
    horizontal: str
    vertical: str
    branch: str
    check_done: str
    check_todo: str
    bullet: str
    clean: str


# Hand-picked single-width glyphs; render crisply in standard terminal fonts
# (Cascadia, Consolas, DejaVu Sans Mono) with nothing extra to install.
UNICODE_THEME = Theme(
    top_left="┌", top_right="┐",
    bot_left="└", bot_right="┘",
    sep_left="├", sep_right="┤",
    horizontal="─", vertical="│",
    branch="⎇", check_done="✓", check_todo="▸", bullet="•", clean="✓",
)

# Requires a Nerd Font installed and selected in the terminal, otherwise these
# Private-Use-Area codepoints show as tofu boxes.
NERD_THEME = Theme(
    top_left="╭", top_right="╮",
    bot_left="╰", bot_right="╯",
    sep_left="├", sep_right="┤",
    horizontal="─", vertical="│",
    branch="", check_done="", check_todo="",
    bullet="", clean="",
)

# Pure ASCII: identical on any font, terminal, or SSH session.
ASCII_THEME = Theme(
    top_left="+", top_right="+",
    bot_left="+", bot_right="+",
    sep_left="+", sep_right="+",
    horizontal="-", vertical="|",
    branch="branch", check_done="[x]", check_todo="[ ]", bullet="*", clean="ok",
)

THEMES = {
    "unicode": UNICODE_THEME,
    "nerd": NERD_THEME,
    "ascii": ASCII_THEME,
}


def active_theme() -> Theme:
    """Selects the theme from the CD_TODO_THEME env var, defaulting to unicode."""
    name = os.environ.get("CD_TODO_THEME", "unicode").strip().lower()
    return THEMES.get(name, UNICODE_THEME)


def display_width(text: str) -> int:
    """Visible column width of `text`, ignoring ANSI escapes.

    Measuring the real column width (rather than counting code points) keeps
    the box borders aligned even when a glyph is wide or combines with the
    previous one. ANSI colour codes contribute nothing to width."""
    plain = _ANSI_RE.sub("", text)
    width = 0
    for ch in plain:
        if unicodedata.combining(ch):
            continue
        width += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return width


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


def get_git_branch():
    """Returns the current branch name, or None if it cannot be determined.

    A detached HEAD reports as "HEAD"; falls back to the short commit hash
    so the header still shows something meaningful."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    branch = result.stdout.strip()
    if branch == "HEAD":
        try:
            short = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                check=True
            )
            return f"({short.stdout.strip()})"
        except (subprocess.CalledProcessError, FileNotFoundError):
            return branch
    return branch


def get_worktree_status():
    """Summarises the working tree as (staged, modified, untracked) counts.

    Returns None if git is unavailable. Counts are per file: a file staged
    and then modified again counts toward both staged and modified."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    staged = modified = untracked = 0
    for line in result.stdout.splitlines():
        if not line:
            continue
        if line.startswith("??"):
            untracked += 1
            continue
        index_state, worktree_state = line[0], line[1]
        if index_state != " ":
            staged += 1
        if worktree_state != " ":
            modified += 1
    return staged, modified, untracked


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


def render_line(line: str, theme: Theme) -> str:
    """Renders one markdown line into an ANSI-styled string.

    Width is measured separately via display_width(), so this only needs to
    return the styled text."""
    stripped = line.rstrip()
    if not stripped.strip():
        return ""

    body = stripped.lstrip()
    indent = stripped[: len(stripped) - len(body)]

    # Heading parsing from # ... up to ###### ...
    if body.startswith("#"):
        """@TODO: As a proof of concept this is fine for now. This can be
        be expanded much much more with better capabilities"""
        level = len(body) - len(body.lstrip("#"))
        text = body[level:].strip()
        if level == 1:
            return f"{BOLD}{CYAN}{text.upper()}{RESET}"
        # @TODO: These levels can be handled later
        # elif level == 2:
        # elif level == 3:
        # elif level == 4:
        return f"{BOLD}{YELLOW}{text}{RESET}"

    # Task checkboxes: - [ ] / - [x]
    if body[:5] in ("- [ ]", "- [x]", "- [X]"):
        checked = body[3].lower() == "x"
        text = body[5:].strip()
        if checked:
            return f"{indent}{GREEN}{theme.check_done}{RESET} {DIM}{STRIKE}{text}{RESET}"
        return f"{indent}{theme.check_todo} {text}"

    # Bullet lists: - item / * item
    if body[:2] in ("- ", "* "):
        text = body[2:].strip()
        return f"{indent}{theme.bullet} {text}"

    return stripped


def render_header(theme: Theme):
    """Renders the branch + working-tree status line, or None if unavailable.

    Returns the styled header string, so the banner omits the header entirely
    rather than drawing an empty one."""
    branch = get_git_branch()
    if branch is None:
        return None

    parts = [f"{BOLD}{CYAN}{theme.branch} {branch}{RESET}"]

    status = get_worktree_status()
    if status is not None:
        staged, modified, untracked = status
        if staged == modified == untracked == 0:
            parts.append(f"{GREEN}{theme.clean} clean{RESET}")
        else:
            bits = []
            if staged:
                bits.append(f"+{staged}")
            if modified:
                bits.append(f"~{modified}")
            if untracked:
                bits.append(f"?{untracked}")
            parts.append(f"{YELLOW}{' '.join(bits)}{RESET}")

    return "  ".join(parts)


def print_banner(root: Path, todo_filename: str, theme: Theme = None):
    """Prints a bordered, markdown-rendered banner for the repository's todo list.

    When git info is available, a header line (branch + working-tree status)
    is drawn at the top, separated from the todo body by a divider."""
    theme = theme or active_theme()

    todo_file = root / todo_filename
    if not todo_file.is_file():
        return

    todo_output = read_output(todo_file)
    if len(todo_output) == 0:
        return

    body = [render_line(line, theme) for line in todo_output.splitlines()]
    header = render_header(theme)

    rows = body if header is None else [header] + body
    inner_width = max((display_width(row) for row in rows), default=0)

    def emit(styled: str):
        padding = " " * (inner_width - display_width(styled))
        print(f"{theme.vertical} {styled}{padding} {theme.vertical}")

    print(f"{theme.top_left}{theme.horizontal * (inner_width + 2)}{theme.top_right}")
    if header is not None:
        emit(header)
        print(f"{theme.sep_left}{theme.horizontal * (inner_width + 2)}{theme.sep_right}")
    for styled in body:
        emit(styled)
    print(f"{theme.bot_left}{theme.horizontal * (inner_width + 2)}{theme.bot_right}")


def main():
    git_root = get_git_root()
    if git_root is None:
        return

    enable_ansi_output()
    print_banner(git_root, "todo.md")


if __name__ == "__main__":
    main()
