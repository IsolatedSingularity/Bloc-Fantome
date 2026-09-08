Add-Type @"
using System;
using System.Runtime.InteropServices;
public class MapSmokeWindows {
 public delegate bool Callback(IntPtr h, IntPtr l);
 [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetClassName(IntPtr h, System.Text.StringBuilder text, int count);
 [DllImport("user32.dll")] public static extern bool EnumWindows(Callback cb, IntPtr l);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
 [DllImport("user32.dll", SetLastError=true)] public static extern IntPtr SendMessageTimeout(IntPtr h, uint m, IntPtr w, IntPtr l, uint flags, uint timeout, out IntPtr result);
}
"@
$rootExe = (Resolve-Path 'BlocFantome.exe').Path
$installedExe = 'C:\Users\hunkb\AppData\Local\Programs\Bloc Fantôme\BlocFantome.exe'
$linkPath = 'C:\Users\hunkb\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Bloc Fantôme\Bloc Fantôme.lnk'
$results = @()
foreach ($exePath in @($installedExe)) {
 if (@(Get-Process BlocFantome -ErrorAction SilentlyContinue | Where-Object Path -eq $exePath).Count) { throw 'App already running' }
 $launchPath = if ($exePath -eq $installedExe) { $linkPath } else { $exePath }
 Start-Process -FilePath $launchPath -WorkingDirectory (Split-Path $exePath) -WindowStyle Hidden
 Start-Sleep -Seconds 20
 $running = @(Get-Process BlocFantome -ErrorAction SilentlyContinue | Where-Object Path -eq $exePath)
 $processIds = @($running.Id)
 $handles = [System.Collections.Generic.List[IntPtr]]::new()
 [MapSmokeWindows]::EnumWindows({param($handle,$unused) [uint32]$windowPid=0; [void][MapSmokeWindows]::GetWindowThreadProcessId($handle,[ref]$windowPid); if ($processIds -contains [int]$windowPid) {$handles.Add($handle)}; return $true},[IntPtr]::Zero) | Out-Null
 $responsive = 0
 $windowDetails = @()
 foreach ($handle in $handles) {
  $messageResult=[IntPtr]::Zero
  $className = [System.Text.StringBuilder]::new(256)
  [void][MapSmokeWindows]::GetClassName($handle,$className,256)
  $answered = [MapSmokeWindows]::SendMessageTimeout($handle,0,[IntPtr]::Zero,[IntPtr]::Zero,2,2000,[ref]$messageResult) -ne [IntPtr]::Zero
  if ($answered) {$responsive++}
  $windowDetails += [pscustomobject]@{Class=$className.ToString();Responsive=$answered}
 }
 $running | Stop-Process -Force
 Start-Sleep -Seconds 2
 Get-Process BlocFantome -ErrorAction SilentlyContinue | Where-Object Path -eq $exePath | Stop-Process -Force
 $remaining = @(Get-Process BlocFantome -ErrorAction SilentlyContinue | Where-Object Path -eq $exePath).Count
 $results += [pscustomobject]@{Path=$exePath;Version=(Get-Item -LiteralPath $exePath).VersionInfo.FileVersion;ProcessCount=$running.Count;WindowCount=$handles.Count;ResponsiveWindows=$responsive;Windows=$windowDetails;Remaining=$remaining;SHA256=(Get-FileHash -LiteralPath $exePath).Hash}
}
$results | ConvertTo-Json | Set-Content .qa/worldmap-273-installed-ready.json
$results | ConvertTo-Json -Depth 5
if (@($results | Where-Object {$_.ResponsiveWindows -eq 0 -or $_.Remaining -ne 0}).Count) {throw 'Smoke failed'}


if (-not @($windowDetails | Where-Object {$_.Class -eq 'pygame' -and $_.Responsive}).Count) {throw 'SDL app window not responsive'}

