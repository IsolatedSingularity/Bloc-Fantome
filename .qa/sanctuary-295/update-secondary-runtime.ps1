$ErrorActionPreference='Stop'
$sourceRoot='C:\Users\hunkb\OneDrive\Documents\Embryo\Bloc-Fantome'
$destinationRoot='C:\Users\hunkb\OneDrive\Documents\GitHub\Bloc-Fantome'
$sourceExe=Join-Path $sourceRoot 'BlocFantome.exe'
if((Get-Item -LiteralPath $sourceExe).VersionInfo.ProductVersion -ne '2.9.5'){throw 'Expected verified 2.9.5 source executable'}
if(!(Test-Path -LiteralPath (Join-Path $destinationRoot 'BlocFantome.exe'))){throw 'Expected existing secondary runtime'}
$relative=@('BlocFantome.exe','Assets\Sound Hub\opening\panoir-you-have-time.ogg','Assets\Fonts\Zekton\Zekton-Regular.otf','Assets\Icons\Splash_Swamp.jpg','Assets\Icons\Respawn_Anchor.ico')
foreach($texture in @('quartz_block_bottom.png','quartz_pillar.png','quartz_pillar_top.png','quartz_bricks.png','chiseled_quartz_block.png','polished_andesite.png','light_blue_stained_glass.png','yellow_stained_glass.png','glowstone.png','smooth_stone.png')){$relative+='Assets\Texture Hub\blocks\'+$texture}
foreach($sound in @('note\harp.ogg','block\grindstone\grindstone1.ogg','block\grindstone\grindstone2.ogg','note\icechime.ogg','block\lodestone\place1.ogg','dig\stone1.ogg')){$relative+='Assets\Sound Hub\'+$sound}
$results=@(foreach($item in $relative){
    $source=Join-Path $sourceRoot $item
    $destination=Join-Path $destinationRoot $item
    $expected=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
    $existing=if(Test-Path -LiteralPath $destination){(Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash}else{''}
    if($expected -ne $existing){
        New-Item -ItemType Directory -Force -Path (Split-Path $destination) | Out-Null
        Copy-Item -LiteralPath $source -Destination $destination -Force
    }
    $actual=(Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash
    if($expected -ne $actual){throw "Copy mismatch: $destination"}
    [pscustomobject]@{Path=$destination;Updated=($existing -ne $expected);SHA256=$actual}
})
$results | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $PSScriptRoot 'secondary-runtime.json')
Write-Output "Verified $($results.Count) runtime files; updated $(@($results | Where-Object Updated).Count)."
