# auto_push.ps1 - weekly snapshot of the zzhclimbing content project to GitHub
#
# Why ASCII only: Windows PowerShell 5.1 reads a .ps1 with no BOM as ANSI,
# so any non-ASCII literal here would be mangled at parse time. The repo has
# a .gitattributes forcing LF; this file is intentionally plain.
#
# Registered as a Windows Scheduled Task (Fridays). See README for the command.
# Log: .cheat-cache\auto-push.log  (gitignored)

$ErrorActionPreference = 'Continue'

# resolve repo root from this script's location (tools\..)
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$logDir = Join-Path $root '.cheat-cache'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir 'auto-push.log'

function Say([string]$m) {
    $line = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '  ' + $m
    Write-Output $line
    Add-Content -Path $log -Value $line -Encoding UTF8
}

Say '=== auto push start ==='
Say ("repo: " + $root)

# ssh must not prompt (see ~/.ssh/config: github.com -> ssh.github.com:443)
$env:GIT_SSH_COMMAND = $null
$env:GIT_TERMINAL_PROMPT = '0'

$dirty = git status --porcelain
if ([string]::IsNullOrWhiteSpace($dirty)) {
    Say 'working tree clean - nothing to commit'
} else {
    $n = ($dirty -split "`n" | Where-Object { $_.Trim() }).Count
    Say ("staging " + $n + " changed path(s)")
    git add -A 2>&1 | ForEach-Object { Say ("  " + $_) }
    $msg = 'auto: weekly snapshot ' + (Get-Date -Format 'yyyy-MM-dd')
    git -c core.safecrlf=false commit -q -m $msg 2>&1 | ForEach-Object { Say ("  " + $_) }
    Say ("committed: " + $msg)
}

# push (no-op when already up to date)
$out = git push origin main 2>&1
$out | ForEach-Object { Say ("  " + $_) }
$code = $LASTEXITCODE

if ($code -eq 0) {
    $head = (git rev-parse HEAD).Trim().Substring(0, 7)
    Say ("OK - pushed, HEAD=" + $head)
} else {
    Say ("FAILED - git push exit code " + $code)
    Say '  check: ~/.ssh/config, ~/.ssh/id_ed25519, and that api.github.com is reachable'
}
Say '=== auto push end ==='
exit $code
