# Starts Codex in this repository with access to Git metadata, uv's user cache,
# Python installations, and the network. Run from your own PowerShell terminal.
# This disables the command sandbox for the child session; commands have your
# Windows user's filesystem and network access. Approval prompts remain enabled.
# Global Codex configuration is not changed. Managed policies still apply.
#
# Examples:
#   .\scripts\codex.ps1
#   .\scripts\codex.ps1 "Run the tests and commit the changes"
#   .\scripts\codex.ps1 resume --last

$ErrorActionPreference = 'Stop'

# Resolve the executable explicitly so this script cannot invoke itself.
$codexCommand = Get-Command codex.exe -CommandType Application -ErrorAction SilentlyContinue
if (-not $codexCommand) {
    throw 'codex.exe was not found on PATH. Install Codex CLI and reopen PowerShell.'
}

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$launchArguments = @(
    '--cd', $repositoryRoot,
    '--no-daemon',
    '--sandbox', 'danger-full-access',
    '--ask-for-approval', 'on-request'
)

# Pass arguments as individual values, preserving spaces in paths and prompts.
& $codexCommand.Source @launchArguments @args
exit $LASTEXITCODE
