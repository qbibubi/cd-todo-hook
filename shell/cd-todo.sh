#!/usr/bin/env sh
# cd-todo - shell integration for bash and zsh.
#
# Shows the current git repository's todo.md whenever you change into a new
# directory. It HOOKS the shell's directory-change / prompt mechanism; it does
# NOT replace or wrap the `cd` builtin, so `cd` keeps behaving exactly as the
# shell intends.
#
#   zsh   -> native `chpwd` hook (fires on every directory change)
#   bash  -> `PROMPT_COMMAND` with a PWD-change guard (bash has no chpwd)
#
# Install - add one line to ~/.bashrc or ~/.zshrc:
#
#     source /path/to/cd-todo/shell/cd-todo.sh
#
# Configuration (export before sourcing to override):
#
#     CD_TODO_PYTHON    interpreter to run       (default: python3)
#     CD_TODO_SCRIPT    path to src/main.py      (default: resolved relative
#                                                 to this file)
#     CD_TODO_ON_START  if set, also show once   (default: unset)
#                       when the shell starts

# --- resolve this script's own location -------------------------------------
# Each shell exposes the sourced file's path differently. The zsh form uses
# syntax bash cannot parse, so it is hidden behind `eval` (bash sees only a
# string literal and never tries to parse it).
_cd_todo_self=""
if [ -n "${ZSH_VERSION:-}" ]; then
    eval '_cd_todo_self="${(%):-%x}"'
elif [ -n "${BASH_VERSION:-}" ]; then
    _cd_todo_self="${BASH_SOURCE[0]}"
fi

if [ -n "$_cd_todo_self" ]; then
    _cd_todo_dir="$(CDPATH= cd -- "$(dirname -- "$_cd_todo_self")" 2>/dev/null && pwd)"
else
    _cd_todo_dir=""
fi

# --- configuration ----------------------------------------------------------
: "${CD_TODO_PYTHON:=python3}"
if [ -z "${CD_TODO_SCRIPT:-}" ] && [ -n "$_cd_todo_dir" ]; then
    # repo root is the parent of this shell/ directory
    CD_TODO_SCRIPT="$(dirname -- "$_cd_todo_dir")/src/main.py"
fi

unset _cd_todo_self _cd_todo_dir

# --- the worker -------------------------------------------------------------
_cd_todo_run() {
    [ -n "${CD_TODO_SCRIPT:-}" ] && [ -f "$CD_TODO_SCRIPT" ] || return 0
    command -v "$CD_TODO_PYTHON" >/dev/null 2>&1 || return 0
    "$CD_TODO_PYTHON" "$CD_TODO_SCRIPT"
}

# --- wire up the hook -------------------------------------------------------
if [ -n "${ZSH_VERSION:-}" ]; then
    autoload -Uz add-zsh-hook
    add-zsh-hook chpwd _cd_todo_run
elif [ -n "${BASH_VERSION:-}" ]; then
    _cd_todo_last_pwd="$PWD"
    _cd_todo_prompt_hook() {
        if [ "$PWD" != "$_cd_todo_last_pwd" ]; then
            _cd_todo_last_pwd="$PWD"
            _cd_todo_run
        fi
    }
    # Prepend our hook to PROMPT_COMMAND, but only once.
    case ";${PROMPT_COMMAND:-};" in
        *";_cd_todo_prompt_hook;"*) : ;;
        *) PROMPT_COMMAND="_cd_todo_prompt_hook${PROMPT_COMMAND:+;$PROMPT_COMMAND}" ;;
    esac
fi

# --- optional: show immediately when the shell starts -----------------------
[ -n "${CD_TODO_ON_START:-}" ] && _cd_todo_run

return 0 2>/dev/null || true
