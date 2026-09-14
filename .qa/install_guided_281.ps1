$ErrorActionPreference = 'Stop'
$installerPath = (Resolve-Path -LiteralPath 'Code/build/installer/BlocFantome_Setup_2.8.1.exe').Path
$logPath = Join-Path (Get-Location).Path '.qa\guided-281-install.log'
$installedExe = 'C:\Users\hunkb\AppData\Local\Programs\Bloc Fantôme\BlocFantome.exe'
if (@(Get-Process BlocFantome -ErrorAction SilentlyContinue | Where-Object Path -eq $installedExe).Count) { throw 'Installed app is running; preserve the active session' }
$installArguments = @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/DIR="C:\Users\hunkb\AppData\Local\Programs\Bloc Fantôme"',('/LOG="'+$logPath+'"'))
$installerProcess = Start-Process -FilePath $installerPath -ArgumentList $installArguments -WindowStyle Hidden -Wait -PassThru
if ($installerProcess.ExitCode -ne 0) { throw "Installer exited $($installerProcess.ExitCode)" }
& '.qa\verify_install_281.ps1'


