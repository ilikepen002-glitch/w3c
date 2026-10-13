function Get-CompilerSha256([string]$Path) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $stream = [System.IO.File]::OpenRead($Path)
    try {
        return [System.BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-', '')
    } finally {
        $stream.Dispose()
        $sha.Dispose()
    }
}
