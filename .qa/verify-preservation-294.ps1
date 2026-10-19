$ErrorActionPreference='Stop'
$root=Split-Path $PSScriptRoot
$baselineFiles=@('maintenance\userdata-before.json','tutorial-294\userdata-before.json','opening-294\source-settings-before-release.json','opening-294\packaged-settings-before.json')
$baseline=foreach($file in $baselineFiles){Get-Content -LiteralPath (Join-Path $PSScriptRoot $file) -Raw | ConvertFrom-Json}
$baseline=$baseline | Sort-Object Path -Unique
$changed=foreach($entry in $baseline){
 if(-not(Test-Path -LiteralPath $entry.Path)){[pscustomobject]@{Path=$entry.Path;Problem='Missing'}}
 elseif((Get-FileHash -LiteralPath $entry.Path -Algorithm SHA256).Hash -ne $entry.Hash){[pscustomobject]@{Path=$entry.Path;Problem='Hash changed'}}
}
$installed='C:\Users\hunkb\AppData\Local\Programs\Bloc Fantôme'
$assets=foreach($relative in @('Assets\Fonts\Zekton\Zekton-Regular.otf','Assets\Sound Hub\opening\panoir-you-have-time.ogg','Assets\Icons\Splash_Swamp.jpg')){
 $sourceHash=(Get-FileHash -LiteralPath (Join-Path $root $relative) -Algorithm SHA256).Hash
 $destHash=(Get-FileHash -LiteralPath (Join-Path $installed $relative) -Algorithm SHA256).Hash
 if($sourceHash -ne $destHash){throw "Installed asset differs: $relative"}
 [pscustomobject]@{Path=$relative;SHA256=$destHash}
}
$report=[pscustomobject]@{CheckedUserFiles=@($baseline).Count;Changed=@($changed);InstalledAssets=$assets}
$report | ConvertTo-Json -Depth 5 | Set-Content (Join-Path $PSScriptRoot 'opening-294\preservation-and-assets.json')
if(@($changed).Count){throw ($changed | ConvertTo-Json)}
$report | ConvertTo-Json -Depth 5
