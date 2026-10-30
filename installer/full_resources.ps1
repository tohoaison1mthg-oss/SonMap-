param([Parameter(Mandatory=$true)][string]$InstallRoot,
      [Parameter(Mandatory=$true)][string]$BundleRoot,[switch]$ValidateOnly)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$allowed=@('assets/TrichLucTT26 -ThanhTan.dgn','assets/Mau03CLBD.dgn','ThanhTanApp.mvba')
$zip=[IO.Compression.ZipFile]::OpenRead((Join-Path $BundleRoot 'resources.zip'))
try {
 $manifestEntry=$zip.GetEntry('resources-manifest.json')
 if(-not $manifestEntry){throw 'Missing resource manifest.'}
 $reader=New-Object IO.StreamReader($manifestEntry.Open())
 try {$manifest=$reader.ReadToEnd()|ConvertFrom-Json}finally{$reader.Dispose()}
 if(@($manifest).Count -ne $allowed.Count -or $zip.Entries.Count -ne ($allowed.Count+1)){throw 'Unexpected resources.'}
 foreach($name in $allowed) {
  $items=@($manifest|Where-Object {$_.file -ceq $name})
  $entries=@($zip.Entries|Where-Object {$_.FullName -ceq $name})
  if($items.Count -ne 1 -or $entries.Count -ne 1){throw ('Missing or duplicate resource: '+$name)}
  $hash=[Security.Cryptography.SHA256]::Create();$stream=$entries[0].Open()
  try {$actual=([BitConverter]::ToString($hash.ComputeHash($stream))).Replace('-','').ToLowerInvariant()}
  finally {$stream.Dispose();$hash.Dispose()}
  if($actual -ne $items[0].sha256){throw ('Resource checksum mismatch: '+$name)}
 }
 if(-not $ValidateOnly) {
  $root=[IO.Path]::GetFullPath($InstallRoot).TrimEnd('\')
  foreach($name in $allowed) {
   $target=[IO.Path]::GetFullPath((Join-Path $root $name))
   if(-not $target.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid resource destination.'}
   if(Test-Path -LiteralPath $target){Write-Host ('Preserved existing resource: '+$name);continue}
   [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target))
   [IO.Compression.ZipFileExtensions]::ExtractToFile($zip.GetEntry($name),$target,$false)
   Write-Host ('Installed resource: '+$name)
  }
 }
} finally {$zip.Dispose()}
