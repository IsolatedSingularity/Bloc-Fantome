param([switch]$Apply)
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$reportDir=Join-Path $root '.qa\architecture'
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null
$tracked=@{}
git -C $root ls-files | ForEach-Object { $tracked[([IO.Path]::GetFullPath((Join-Path $root $_))).ToLowerInvariant()]=$true }
if($LASTEXITCODE -ne 0){throw 'Cannot establish tracked-file protection'}
$candidates=@()
# Keep the newest two installers, including the preceding known-good release.
$installerDir=Join-Path $root 'Code\build\installer'
$installers=@(if(Test-Path -LiteralPath $installerDir){Get-ChildItem -LiteralPath $installerDir -File |
    Where-Object Name -Match '^BlocFantome_Setup_(\d+\.\d+\.\d+)\.exe$' |
    Sort-Object { [version]($_.BaseName -replace '^BlocFantome_Setup_','') } -Descending})
$candidates+=@($installers | Select-Object -Skip 2)
foreach($base in @('Code','tests')){
    $candidates+=@(Get-ChildItem -LiteralPath (Join-Path $root $base) -Directory -Recurse -Filter '__pycache__')
}
# Pytest fixture trees are disposable; visual evidence, logs, captures and
# original asset/reference libraries are deliberately outside this allowlist.
$candidates+=@(Get-ChildItem -LiteralPath (Join-Path $root '.qa') -Directory -Recurse |
    Where-Object { $_.Name -match '^pytest(?:-|$)' })
$work=Join-Path $root 'Code\build\work'
if(Test-Path -LiteralPath $work){$candidates+=Get-Item -LiteralPath $work}
$selected=@()
foreach($item in ($candidates | Sort-Object { $_.FullName.Length })){
    $path=[IO.Path]::GetFullPath($item.FullName)
    if(!$path.StartsWith($root+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw "Outside workspace: $path"}
    if($selected | Where-Object { $path.StartsWith($_.Path+'\',[StringComparison]::OrdinalIgnoreCase) }){continue}
    $ancestry=$item
    while($ancestry -and $ancestry.FullName -ne $root){
        if($ancestry.Attributes -band [IO.FileAttributes]::ReparsePoint){throw "Refusing linked target: $path"}
        $ancestry=if($ancestry.PSIsContainer){$ancestry.Parent}else{$ancestry.Directory}
    }
    $children=if($item.PSIsContainer){@(Get-ChildItem -LiteralPath $path -Force -Recurse)}else{@($item)}
    if($children | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }){throw "Linked descendant: $path"}
    $files=@($children | Where-Object { !$_.PSIsContainer })
    if($files | Where-Object { $tracked.ContainsKey($_.FullName.ToLowerInvariant()) }){continue}
    $selected+=[pscustomobject]@{Path=$path;Files=$files.Count;Bytes=($files | Measure-Object Length -Sum).Sum}
}
$report=[pscustomobject]@{Applied=[bool]$Apply;Root=$root;Files=($selected | Measure-Object Files -Sum).Sum;Bytes=($selected | Measure-Object Bytes -Sum).Sum;Targets=$selected}
$report | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $reportDir $(if($Apply){'cleanup-applied.json'}else{'cleanup-plan.json'}))
if($Apply){foreach($target in $selected){Remove-Item -LiteralPath $target.Path -Recurse -Force}}
[pscustomobject]@{Applied=[bool]$Apply;Targets=$selected.Count;Files=$report.Files;GiB=[math]::Round($report.Bytes/1GB,3)} | Format-List
