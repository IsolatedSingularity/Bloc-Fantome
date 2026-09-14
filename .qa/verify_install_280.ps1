$ErrorActionPreference = 'Stop'
$rootExe = (Resolve-Path -LiteralPath 'BlocFantome.exe').Path
$installedDir = 'C:\Users\hunkb\AppData\Local\Programs\Bloc Fantôme'
$installedExe = Join-Path $installedDir 'BlocFantome.exe'
$linkPath = 'C:\Users\hunkb\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Bloc Fantôme\Bloc Fantôme.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($linkPath)
$rootHash = (Get-FileHash -LiteralPath $rootExe).Hash
$installedHash = (Get-FileHash -LiteralPath $installedExe).Hash
$version = (Get-Item -LiteralPath $installedExe).VersionInfo.FileVersion
$configBefore = Get-Content -Raw -LiteralPath '.qa/guided-280-installed-config-before.json' | ConvertFrom-Json
$configAfter = Get-Content -Raw -LiteralPath (Join-Path $installedDir 'config.json') | ConvertFrom-Json
$preserved = ($configBefore.hotbar | ConvertTo-Json -Compress) -eq ($configAfter.hotbar | ConvertTo-Json -Compress)
$preserved2 = ($configBefore.hotbar2 | ConvertTo-Json -Compress) -eq ($configAfter.hotbar2 | ConvertTo-Json -Compress)
$required = @('Assets\Fonts\Zekton\Zekton-Regular.otf','Assets\Icons\Splash_Background_Warped_Forest.png','References\Titles\horror.png')
foreach ($asset in $required) { if (-not (Test-Path -LiteralPath (Join-Path $installedDir $asset))) { throw "Missing asset: $asset" } }
$result = [pscustomobject]@{Version=$version;Target=$shortcut.TargetPath;WorkingDirectory=$shortcut.WorkingDirectory;Icon=$shortcut.IconLocation;TargetExists=(Test-Path -LiteralPath $shortcut.TargetPath);SHA256=$installedHash;RootHashMatches=($rootHash -eq $installedHash);HotbarPreserved=$preserved;Hotbar2Preserved=$preserved2;RequiredAssets=$required}
$result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath '.qa/guided-280-install-verification.json'
$result | Format-List
if ($version -ne '2.8.0' -or $rootHash -ne $installedHash -or $shortcut.TargetPath -ne $installedExe -or $shortcut.WorkingDirectory -ne $installedDir -or -not $shortcut.IconLocation.StartsWith($installedDir) -or -not $preserved -or -not $preserved2) { throw 'Installed release verification failed' }

