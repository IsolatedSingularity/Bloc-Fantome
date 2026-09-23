[CmdletBinding()]
param(
    [switch]$Execute,
    [string]$Destination = (Join-Path (Split-Path $PSScriptRoot -Parent) "downloads"),
    [double]$MaxTotalMiB = 16,
    [string]$Python = "python"
)
$ErrorActionPreference = "Stop"
$CliArgs = @((Join-Path $PSScriptRoot "fetch_references.py"), "--dest", $Destination, "--max-total-mib", $MaxTotalMiB.ToString([Globalization.CultureInfo]::InvariantCulture))
$CliArgs += @("--group", "shaders")
if ($Execute) { $CliArgs += "--execute" }
& $Python @CliArgs
if ($LASTEXITCODE -ne 0) { throw "Reference retrieval failed with exit code $LASTEXITCODE. Read the receipt; nothing was installed." }
