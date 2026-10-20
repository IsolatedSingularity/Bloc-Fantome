$ErrorActionPreference='Stop'
$workspace=Split-Path (Split-Path $PSScriptRoot)
$work=Join-Path $workspace '.qa/kh-assets'
$apps=Join-Path $work 'openkh/openkh/Apps'
foreach($n in @('Xe.BinaryMapper','OpenKh.Common','OpenKh.Imaging','OpenKh.Ps2','OpenKh.Kh2','OpenKh.Engine','OpenKh.Kh2AnimEmu')) {
 [Reflection.Assembly]::LoadFrom((Join-Path $apps "$n.dll"))|Out-Null
}
Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Numerics;
using System.Runtime.InteropServices;
public static class PoseWriter {
 public static void Write(Stream stream, Matrix4x4[] pose) {
  stream.Write(MemoryMarshal.AsBytes(pose.AsSpan()));
 }
}
'@
$source=Join-Path $work 'extracted/kh2_fifth'
$dest=Join-Path $work 'export'
New-Item -ItemType Directory -Force $dest | Out-Null
$modelStream=[IO.File]::OpenRead((Join-Path $source 'B_EX100.mdlx'))
$bar=[OpenKh.Kh2.Bar]::Read($modelStream)
$entry=$bar | Where-Object {$_.Type -eq 'Model'} | Select-Object -First 1
$parser=[OpenKh.Engine.Parsers.MdlxParser]::new([OpenKh.Kh2.Mdlx]::Read($entry.Stream))
$meshData=@(foreach($mesh in $parser.MeshDescriptors) {
 @{texture=$mesh.TextureIndex;indices=$mesh.Indices;vertices=@(foreach($v in $mesh.Vertices){,@($v.X,$v.Y,$v.Z,$v.Tu,$v.Tv)});
 weights=@(foreach($weights in $mesh.VertexBoneWeights){ ,@(foreach($w in $weights){ ,@($w.MatrixIndex,$w.Weight) }) })}
})
@{bones=$parser.Bones;meshes=$meshData} | ConvertTo-Json -Depth 12 -Compress | Set-Content (Join-Path $dest 'rig.json')
$out=[IO.File]::Create((Join-Path $dest 'bind.bin'))
[PoseWriter]::Write($out,$parser.InitialPose);$out.Dispose()
$motionStream=[IO.File]::OpenRead((Join-Path $source 'B_EX100.mset'))
$motions=[OpenKh.Kh2.Bar]::Read($motionStream)
$metadata=@()
foreach($entry in $motions) {
 if($entry.Type -ne 'Anb' -or $entry.Stream.Length -eq 0){continue}
 $entry.Stream.Position=0
 $anb=[OpenKh.Kh2.Bar]::Read($entry.Stream)
 $modelStream.Position=0
 $provider=[OpenKh.Kh2Anim.Mset.AnbIndir]::new($anb).GetAnimProvider($modelStream)
 $count=[int][Math]::Ceiling($provider.FrameEnd)
 Write-Output "$($entry.Name): frames=$count fps=$($provider.FramePerSecond) bones=$($provider.MatrixCount)"
 $out=[IO.File]::Create((Join-Path $dest ($entry.Name+'.bin')))
 try {
  for($frame=0;$frame -le $count;$frame++) {
   # The emulator takes a frame DELTA, accumulating it internally.
   $delta=if($frame -eq 0){0.0}else{1.0}
   $matrices=$provider.ProvideMatrices($delta)
   [PoseWriter]::Write($out,$matrices)
  }
 } finally {$out.Dispose()}
 $metadata+=@{name=$entry.Name;frames=$count+1;fps=$provider.FramePerSecond;bones=$provider.MatrixCount;loop=$provider.FrameLoop}
}
$metadata | ConvertTo-Json | Set-Content (Join-Path $dest 'motions.json')
$motionStream.Dispose();$modelStream.Dispose()
