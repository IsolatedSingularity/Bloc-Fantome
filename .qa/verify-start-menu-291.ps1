$ErrorActionPreference = 'Stop'
$installFolder = 'C:\Users\hunkb\AppData\Local\Programs\Bloc Fantôme'
$menuFolder = 'C:\Users\hunkb\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Bloc Fantôme'
$stageFolder = Join-Path $PSScriptRoot 'start-menu-291'
New-Item -ItemType Directory -Force -Path $stageFolder, $menuFolder | Out-Null
$shortcutShell = New-Object -ComObject WScript.Shell
$results = foreach ($entry in @(
    @{ Name='Bloc Fantôme.lnk'; Exe='BlocFantome.exe' },
    @{ Name='Uninstall Bloc Fantôme.lnk'; Exe='unins000.exe' }
)) {
    $expectedTarget = Join-Path $installFolder $entry.Exe
    if (!(Test-Path -LiteralPath $expectedTarget)) { throw "Missing target: $expectedTarget" }
    $stagedPath = Join-Path $stageFolder $entry.Name
    $link = $shortcutShell.CreateShortcut($stagedPath)
    $link.TargetPath = $expectedTarget
    $link.WorkingDirectory = $installFolder
    $link.IconLocation = (Join-Path $installFolder 'Assets\Icons\Respawn_Anchor.ico') + ',0'
    $link.Save()
    $staged = $shortcutShell.CreateShortcut($stagedPath)
    if ($staged.TargetPath -ne $expectedTarget) { throw 'Staged target mismatch' }
    $destination = Join-Path $menuFolder $entry.Name
    Copy-Item -LiteralPath $stagedPath -Destination $destination -Force
    $verified = $shortcutShell.CreateShortcut($destination)
    if ($verified.TargetPath -ne $expectedTarget -or $verified.WorkingDirectory -ne $installFolder -or $verified.IconLocation -ne $staged.IconLocation) { throw 'Installed shortcut mismatch' }
    [pscustomobject]@{ Shortcut=$destination; Target=$verified.TargetPath; WorkingDirectory=$verified.WorkingDirectory; Icon=$verified.IconLocation; TargetExists=(Test-Path -LiteralPath $verified.TargetPath) }
}
$installedExe = Join-Path $installFolder 'BlocFantome.exe'
$installedHash = (Get-FileHash -LiteralPath $installedExe -Algorithm SHA256).Hash
$rootHash = (Get-FileHash -LiteralPath (Join-Path (Split-Path $PSScriptRoot) 'BlocFantome.exe') -Algorithm SHA256).Hash
if ($installedHash -ne $rootHash) { throw 'Installed executable hash mismatch' }
$version = (Get-Item -LiteralPath $installedExe).VersionInfo.ProductVersion
if ($version -ne '2.9.1') { throw "Unexpected installed version: $version" }
$report = [pscustomobject]@{ Version=$version; SHA256=$installedHash; Shortcuts=$results }
$report | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $PSScriptRoot 'consistency-start-menu-291.json')
$report | ConvertTo-Json -Depth 5
