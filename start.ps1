$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$btpNode = Get-Command node -ErrorAction SilentlyContinue
if ($btpNode) { $btpNodePath = $btpNode.Source } else {
    $btpNodePath = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
    if (-not (Test-Path -LiteralPath $btpNodePath)) { throw 'Install Node.js 22 or newer, then run start.ps1 again.' }
}
Write-Host 'Open http://127.0.0.1:8000 in your browser.'
Write-Host 'Starting local Llama for AES review. Set CRYPTAGENT_PYTHON if your model environment is elsewhere.'
& $btpNodePath (Join-Path $PSScriptRoot 'tools\start_local.mjs')
