# cd-todo shell integration

These scripts make `cd-todo` run automatically when you change directories,
printing the current git repository's `todo.md` banner.

They work by **hooking** the shell's directory-change mechanism. Your `cd`
(or `Set-Location`) command is **not** replaced or wrapped — it keeps working
exactly as before. The hook simply notices when the working directory changed
and runs the tool.

## Install

### bash

Add to `~/.bashrc`:

```bash
source /path/to/cd-todo/shell/cd-todo.sh
```

bash has no native directory-change hook, so this registers a
`PROMPT_COMMAND` handler that checks whether `$PWD` changed since the last
prompt.

### zsh

Add to `~/.zshrc`:

```zsh
source /path/to/cd-todo/shell/cd-todo.sh
```

zsh gets the real thing: a native `chpwd` hook that fires only on directory
changes.

### PowerShell (Windows PowerShell 5.1 or PowerShell 7+)

Add to your `$PROFILE` (run `notepad $PROFILE` to edit it):

```powershell
. C:\path\to\cd-todo\shell\cd-todo.ps1
```

On PowerShell 6.2+ this uses the native
`$ExecutionContext.InvokeCommand.LocationChangedAction` hook. On Windows
PowerShell 5.1 (which has no such hook) it installs a `prompt` function that
detects directory changes; any existing `prompt` is preserved and still runs.

## Configuration

Override these before sourcing the script.

| Variable | Default | Purpose |
| --- | --- | --- |
| `CD_TODO_PYTHON` | `python3` (sh) / `python` (ps1) | Interpreter used to run the tool |
| `CD_TODO_SCRIPT` | resolved relative to the hook file | Path to `src/main.py` |
| `CD_TODO_ON_START` | unset | If set, also show the banner once when a shell starts |
| `CD_TODO_NO_UTF8` | unset | PowerShell only. If set, the hook leaves the console encoding alone (see below) |

Example (bash/zsh):

```bash
export CD_TODO_PYTHON=python          # e.g. git-bash on Windows
export CD_TODO_ON_START=1
source /path/to/cd-todo/shell/cd-todo.sh
```

Example (PowerShell):

```powershell
$env:CD_TODO_ON_START = 1
. C:\path\to\cd-todo\shell\cd-todo.ps1
```

## Notes

- The tool stays quiet unless you are inside a git repository that contains a
  `todo.md`, so changing into ordinary directories prints nothing.
- The banner is **not** shown when a shell first starts (even inside a repo) —
  only when you change directories afterwards. Set `CD_TODO_ON_START` if you
  want it on launch too.
- **Windows PowerShell 5.1 and UTF-8:** 5.1 defaults to the OEM code page, which
  renders the banner's box-drawing glyphs as mojibake (`ΓöîΓöÇ...`). The hook
  therefore sets `[Console]::OutputEncoding` to UTF-8 for the session. If you
  already manage console encoding (e.g. in your profile), set `CD_TODO_NO_UTF8`
  to skip it. PowerShell 7+ already uses UTF-8, so this is a no-op there.
- Because this is a directory-change hook (not a `cd` wrapper), it cannot see
  flags passed to `cd`. A planned option like `cd --show-completed` will need a
  small `cd` wrapper or a separate command instead; the hook itself is
  unaffected.
- Every directory change spawns the Python tool plus a couple of `git` calls.
  That is fine for interactive use; suppressing repeat displays within the same
  repository is a planned optimization.
