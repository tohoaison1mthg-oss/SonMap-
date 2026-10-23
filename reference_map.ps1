param([string]$Source,[string]$Target,[switch]$ProbeOnly)
$ErrorActionPreference='Stop'
try {
 $Source=[IO.Path]::GetFullPath($Source);$Target=[IO.Path]::GetFullPath($Target)
 if($Source -eq $Target){throw 'Source and output must be different files.'}
 if(-not (Test-Path -LiteralPath $Source) -or -not (Test-Path -LiteralPath $Target)){throw 'Source or output DGN is missing.'}
 $a=[Runtime.InteropServices.Marshal]::GetActiveObject('MicroStationDGN.Application')
 $fs=New-Object -ComObject Scripting.FileSystemObject
 if($fs.GetFile($a.ActiveDesignFile.FullName).ShortPath -ne $fs.GetFile($Target).ShortPath){throw 'Open the exported DGN before attaching its source map.'}
 if($ProbeOnly){Write-Output 'READY';exit 0}
 foreach($ref in $a.ActiveModelReference.Attachments){
  if(-not $ref.IsMissingFile -and $fs.FileExists($ref.AttachName) -and $fs.GetFile($ref.AttachName).ShortPath -eq $fs.GetFile($Source).ShortPath){
   $ref.DisplayFlag=-not $ref.DisplayFlag;$ref.Rewrite();$a.ActiveDesignFile.Save()
   if($ref.DisplayFlag){Write-Output 'DISPLAY_ON'}else{Write-Output 'DISPLAY_OFF'}
   exit 0
  }
 }
 # Bentley MsdAddAttachmentFlags: TrueScale=1, CoincidentWorld=2, entsVisible=4.
 # Match world coordinates and master units, including differing global origins.
 $ref=$a.ActiveModelReference.Attachments.AddCoincident1($fs.GetFile($Source).ShortPath,'','SonMap_Source','SonMap world-coordinate source map',7)
 if($ref.IsMissingFile -or $ref.IsMissingModel){throw 'Reference did not resolve.'}
 $ref.SetAttachNameDeferred($Source)
 $ref.NestLevel=0;$ref.DisplayFlag=$true;$ref.Rewrite();$a.ActiveDesignFile.Save()
 Write-Output 'ATTACHED: TrueScale + CoincidentWorld + Display ON'
}catch{Write-Output $_.Exception.Message;exit 1}
