$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$lock = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'stdlib/lock.json') -Raw | ConvertFrom-Json
$configuration = Get-Content -LiteralPath (Join-Path $projectRoot 'wurst.build')
if ($configuration -notcontains ('- ' + $lock.dependency)) {
    throw 'wurst.build does not select the locked damage-engine dependency.'
}

foreach ($repository in @($lock.source, (Join-Path $projectRoot '_build/dependencies/WurstStdlib2-source'))) {
    if (-not (Test-Path -LiteralPath (Join-Path $repository '.git'))) {
        throw "Missing locked standard library: $repository. See tools/stdlib/README.md."
    }
    $tree = & git -C $repository rev-parse 'HEAD^{tree}'
    if ($LASTEXITCODE -ne 0 -or $tree -ne $lock.fixedTree) {
        throw "Standard-library content does not match the locked tree: $repository"
    }
    $changes = & git -C $repository status --porcelain --untracked-files=all
    if ($LASTEXITCODE -ne 0 -or $changes) {
        throw "Standard-library checkout has local changes: $repository. Preserve and review them before building."
    }
}
