# Restore program files only. Keep a reciprocal snapshot for undoing the restore.
param([string]$InstallRoot,[string]$BackupPath)
$ErrorActionPreference='Stop'
if(-not $InstallRoot){$InstallRoot=Join-Path $env:LOCALAPPDATA 'SonMapPlus\App'}
$InstallRoot=[IO.Path]::GetFullPath($InstallRoot)
$storage=Split-Path -Parent $InstallRoot
$backupRoot=Join-Path $storage 'Backups'
$undo=$null;$applied=New-Object 'System.Collections.Generic.List[object]'
function SafePath($root,[string]$relative) {
 if($relative -match '(^|[/\\])(data|assets|runtime|exports|\.git|\.venv-topology)([/\\]|$)' -or $relative -eq 'settings.json' -or $relative -match '\.(mdb|dgn|mvba|dll)$'){throw 'Refusing to restore protected user files.'}
 $path=[IO.Path]::GetFullPath((Join-Path $root $relative))
 if(-not $path.StartsWith($root+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid backup file path.'}
 return $path
}
try {
 foreach($proc in Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'") {
  if($proc.CommandLine -and $proc.CommandLine.IndexOf($InstallRoot,[StringComparison]::OrdinalIgnoreCase) -ge 0 -and $proc.CommandLine -match '(launch|app)\.py'){throw 'Close SonMap before restoring a version.'}
 }
 if(-not $BackupPath) {
  $choices=@()
  if(Test-Path -LiteralPath $backupRoot) {
   foreach($folder in Get-ChildItem -LiteralPath $backupRoot -Directory | Sort-Object LastWriteTime -Descending) {
    $metadata=Join-Path $folder.FullName 'restore.json'
    if(Test-Path -LiteralPath $metadata) {
     $info=Get-Content -LiteralPath $metadata -Raw -Encoding UTF8 | ConvertFrom-Json
     if($info.schema -eq 1 -and $info.from_version){$choices+=@{path=$folder.FullName;info=$info}}
    }
   }
  }
  if($choices.Count -eq 0){throw 'No previous installed version is available yet. Backups are created when updating an existing installation.'}
  Write-Host 'CAC BAN CO THE KHOI PHUC:'
  for($i=0;$i -lt $choices.Count;$i++){Write-Host (($i+1).ToString()+'. SonMap+ V'+$choices[$i].info.from_version+' - '+(Split-Path -Leaf $choices[$i].path))}
  $answer=Read-Host 'Nhap so thu tu (Enter de huy)'
  if(-not $answer){exit 0}
  $number=0
  if(-not [int]::TryParse($answer,[ref]$number) -or $number -lt 1 -or $number -gt $choices.Count){throw 'Invalid selection.'}
  $BackupPath=$choices[$number-1].path
 }
 $BackupPath=[IO.Path]::GetFullPath($BackupPath)
 if(-not $BackupPath.StartsWith([IO.Path]::GetFullPath($backupRoot)+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Select a backup from this installation.'}
 $info=Get-Content -LiteralPath (Join-Path $BackupPath 'restore.json') -Raw -Encoding UTF8 | ConvertFrom-Json
 if($info.schema -ne 1 -or -not $info.from_version){throw 'No previous program version in this backup.'}
 $current=([IO.File]::ReadAllText((Join-Path $InstallRoot 'VERSION'))).Trim()
 # Validate every path and source before modifying any installed file.
 foreach($entry in $info.files) {
  $target=SafePath $InstallRoot $entry.file;$saved=SafePath $BackupPath $entry.file
  if($entry.existed) {
   if(-not (Test-Path -LiteralPath $saved)){throw ('Backup file missing: '+$entry.file)}
   if(-not $entry.sha256 -or (Get-FileHash -LiteralPath $saved -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256){throw ('Backup checksum mismatch: '+$entry.file)}
  }
 }
 $undo=Join-Path $backupRoot ('before-restore-'+[Guid]::NewGuid().ToString('N'))
 [void](New-Item -ItemType Directory -Path $undo -Force)
 $records=New-Object 'System.Collections.Generic.List[object]'
 foreach($entry in $info.files) {
  $target=SafePath $InstallRoot $entry.file;$exists=Test-Path -LiteralPath $target
  $record=@{file=[string]$entry.file;existed=[bool]$exists;sha256=$null};$records.Add($record)
  if($exists) {
   $saved=SafePath $undo $entry.file;[void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($saved))
   Copy-Item -LiteralPath $target -Destination $saved
   $record.sha256=(Get-FileHash -LiteralPath $saved -Algorithm SHA256).Hash.ToLowerInvariant()
  }
 }
 $undoInfo=@{schema=1;from_version=$current;installed_version=$info.from_version;files=@($records.ToArray())}
 [IO.File]::WriteAllText((Join-Path $undo 'restore.json'),(ConvertTo-Json -InputObject $undoInfo -Depth 6),(New-Object Text.UTF8Encoding($false)))
 for($i=0;$i -lt $info.files.Count;$i++) {
  $entry=$info.files[$i];$target=SafePath $InstallRoot $entry.file
  $applied.Add($records[$i])
  if($entry.existed) {
   [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target))
   Copy-Item -LiteralPath (SafePath $BackupPath $entry.file) -Destination $target -Force
  } elseif(Test-Path -LiteralPath $target){Remove-Item -LiteralPath $target}
 }
 Write-Host ('Restored SonMap+ V'+$info.from_version+'. Current version V'+$current+' saved for recovery in '+$undo)
 Write-Host 'DGN/MDB and private data unchanged. Open SonMap using its Desktop shortcut.'
 exit 0
} catch {
 if($undo) {
  foreach($entry in $applied) {
   $target=SafePath $InstallRoot $entry.file;$saved=SafePath $undo $entry.file
   if($entry.existed){Copy-Item -LiteralPath $saved -Destination $target -Force}
   elseif(Test-Path -LiteralPath $target){Remove-Item -LiteralPath $target}
  }
 }
 Write-Host ('RESTORE STOPPED: '+$_.Exception.Message)
 exit 1
}
