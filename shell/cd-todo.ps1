# cd-todo - shell integration for PowerShell (Windows PowerShell 5.1 and 7+).
#
# Shows the current git repository's todo.md whenever you change into a new
# directory. It HOOKS location changes; it does NOT replace Set-Location (cd),
# so `cd` keeps behaving exactly as PowerShell intends.
#
#   PowerShell 6.2+        -> $ExecutionContext.InvokeCommand.LocationChangedAction
#                            (a native hook that fires on every location change,
#                             chaining any action already registered)
#   Windows PowerShell 5.1 -> a `prompt` function that detects PWD changes
#                            (5.1 has no location hook; the original prompt is
#                             preserved and still called)
#
# Install - add one line to your $PROFILE:
#
#     . C:\path\to\cd-todo\shell\cd-todo.ps1
#
# Configuration (set before dot-sourcing to override):
#
#     $env:CD_TODO_PYTHON    interpreter to run      (default: python)
#     $env:CD_TODO_SCRIPT    path to src/main.py     (default: resolved
#                                                      relative to this file)
#     $env:CD_TODO_ON_START  if set, also show once  (default: unset)
#                            when the shell starts

if (-not $global:CdTodoInstalled) {

    # --- configuration ------------------------------------------------------
    if ($env:CD_TODO_PYTHON) {
        $global:CdTodoPython = $env:CD_TODO_PYTHON
    } else {
        $global:CdTodoPython = 'python'
    }

    if ($env:CD_TODO_SCRIPT) {
        $global:CdTodoScript = $env:CD_TODO_SCRIPT
    } else {
        # repo root is the parent of this shell/ directory
        $global:CdTodoScript = Join-Path (Split-Path -Parent $PSScriptRoot) 'src\main.py'
    }

    # --- the worker ---------------------------------------------------------
    function global:Invoke-CdTodo {
        if (-not (Test-Path -LiteralPath $global:CdTodoScript)) { return }
        if (-not (Get-Command $global:CdTodoPython -ErrorAction SilentlyContinue)) { return }
        # Write straight to the host. Inside the `prompt` function the success
        # stream becomes the prompt text, so the banner must bypass it or it
        # would be mangled into (or captured away from) the prompt line.
        & $global:CdTodoPython $global:CdTodoScript | Out-Host
    }

    # --- ensure the console can render the banner's Unicode glyphs ----------
    # Windows PowerShell 5.1 defaults to the OEM code page (e.g. cp437), which
    # turns the box-drawing characters into mojibake like "ΓöîΓöÇ". Switching
    # console output to UTF-8 fixes it. Set CD_TODO_NO_UTF8 to skip this if you
    # manage console encoding yourself.
    if (-not $env:CD_TODO_NO_UTF8) {
        try {
            $global:CdTodoPrevConsoleEncoding = [Console]::OutputEncoding
            [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
        } catch { }
    }

    # --- wire up the hook ---------------------------------------------------
    $supportsLocationAction =
        $ExecutionContext.InvokeCommand.PSObject.Properties.Name -contains 'LocationChangedAction'

    if ($supportsLocationAction) {
        # PowerShell 6.2+: native location-changed hook. Preserve any existing
        # action and call it first so we cooperate with other tools.
        $global:CdTodoPrevLocationAction = $ExecutionContext.InvokeCommand.LocationChangedAction
        $ExecutionContext.InvokeCommand.LocationChangedAction = {
            param($oldPath, $newPath)
            if ($global:CdTodoPrevLocationAction) {
                & $global:CdTodoPrevLocationAction $oldPath $newPath
            }
            Invoke-CdTodo
        }
    } else {
        # Windows PowerShell 5.1: detect PWD changes at prompt time, preserving
        # whatever `prompt` was already defined. Start "unprimed" ($null) so the
        # first prompt after startup only records the directory and never shows
        # the banner -- otherwise a fresh shell launched inside a repo (or a
        # nested `powershell.exe`) would print it on launch.
        $global:CdTodoLastPath = $null
        if (-not (Test-Path Function:\_CdTodoOriginalPrompt)) {
            $existingPrompt = Get-Command prompt -CommandType Function -ErrorAction SilentlyContinue
            if ($existingPrompt) {
                Set-Item Function:\global:_CdTodoOriginalPrompt $existingPrompt.ScriptBlock
            } else {
                Set-Item Function:\global:_CdTodoOriginalPrompt { "PS $($PWD.Path)> " }
            }
        }
        function global:prompt {
            $here = $PWD.Path
            if ($null -eq $global:CdTodoLastPath) {
                $global:CdTodoLastPath = $here          # prime on first prompt
            } elseif ($here -ne $global:CdTodoLastPath) {
                $global:CdTodoLastPath = $here
                Invoke-CdTodo
            }
            _CdTodoOriginalPrompt
        }
    }

    # --- optional: show immediately when the shell starts -------------------
    if ($env:CD_TODO_ON_START) { Invoke-CdTodo }

    $global:CdTodoInstalled = $true
}
