# Per-user source updater. No administrator access or private CAD data required.
param([string]$InstallRoot,[switch]$NoLaunch)
$ErrorActionPreference='Stop'
if(-not $InstallRoot){$InstallRoot=Join-Path $env:LOCALAPPDATA 'SonMapPlus\App'}
$InstallRoot=[IO.Path]::GetFullPath($InstallRoot)
$storage=Split-Path -Parent $InstallRoot
$stage=Join-Path ([IO.Path]::GetTempPath()) ('SonMapUpdate-'+[Guid]::NewGuid().ToString('N'))
$backup=$null;$written=New-Object 'System.Collections.Generic.List[string]';$committed=$false
[void](New-Item -ItemType Directory -Path $stage -Force)
[void](New-Item -ItemType Directory -Path (Join-Path $storage 'Logs') -Force)
$log=Join-Path $storage ('Logs\install-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.log')
function Log([string]$Message){Write-Host $Message;Add-Content -LiteralPath $log -Value $Message -Encoding UTF8}
try {
 Add-Type -AssemblyName System.IO.Compression.FileSystem
 $zip=[IO.Compression.ZipFile]::OpenRead((Join-Path $PSScriptRoot 'payload.zip'))
 try {
  foreach($entry in $zip.Entries) {
   $path=[IO.Path]::GetFullPath((Join-Path $stage $entry.FullName))
   if(-not $path.StartsWith($stage+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid package path.'}
   if($entry.FullName.EndsWith('/')){continue}
   [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($path))
   [IO.Compression.ZipFileExtensions]::ExtractToFile($entry,$path,$false)
  }
 } finally {$zip.Dispose()}
 $version=([IO.File]::ReadAllText((Join-Path $stage 'VERSION'))).Trim()
 if($version -notmatch '^\d+\.\d+$'){throw 'Invalid application version.'}
 Log ('SonMap+ V'+$version+' - install/update')
 $manifest=Get-Content -LiteralPath (Join-Path $stage 'MANIFEST.json') -Raw -Encoding UTF8 | ConvertFrom-Json
 foreach($item in $manifest) {
  $relative=[string]$item.file
  # Runtime/user files must never be part of the update's replaceable file list.
  if($relative -match '(^|[/\\])(data|assets|runtime|exports|\.git|\.venv-topology)([/\\]|$)' -or $relative -eq 'settings.json' -or $relative -match '\.(mdb|dgn|mvba|dll)$'){throw 'Package includes protected user files.'}
  $path=[IO.Path]::GetFullPath((Join-Path $stage $relative))
  if(-not $path.StartsWith($stage+[IO.Path]::DirectorySeparatorChar,[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid manifest path.'}
  if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $item.sha256){throw ('Package checksum mismatch: '+$relative)}
 }
 $old=$null
 $installed=Join-Path $InstallRoot 'VERSION'
 if(Test-Path -LiteralPath $installed) {
  $old=([IO.File]::ReadAllText($installed)).Trim()
  if([version]$old -gt [version]$version){throw ('A newer version V'+$old+' is installed; refusing to downgrade.')}
 }
 # Never replace application modules while the old copy is running.
 foreach($proc in Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'") {
  if($proc.CommandLine -and $proc.CommandLine.IndexOf($InstallRoot,[StringComparison]::OrdinalIgnoreCase) -ge 0 -and $proc.CommandLine -match '(launch|app)\.py') {
   throw 'Close the installed SonMap window, then run this installer again.'
  }
 }
 [void](New-Item -ItemType Directory -Path $InstallRoot -Force)
 # Prepare dependencies first. If this fails, existing application files are unchanged.
 Log 'Preparing Python and dependencies. Internet is required on first install.'
 $powershell=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
 $previous=$ErrorActionPreference
 try {
  $ErrorActionPreference='Continue'
  & $powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $stage 'start_topology.ps1') -PrepareOnly -EnvironmentRoot $InstallRoot -InstallPython 2>&1 | ForEach-Object {Log ([string]$_)}
  $code=$LASTEXITCODE
 } finally {$ErrorActionPreference=$previous}
 if($code -ne 0){throw 'Python/dependency preparation failed. See the messages above.'}
 $backup=Join-Path $storage ('Backups\before-'+$version+'-'+[Guid]::NewGuid().ToString('N'))
 [void](New-Item -ItemType Directory -Path $backup -Force)
 $files=@($manifest | ForEach-Object {[string]$_.file})+@('MANIFEST.json')
 $restoreEntries=New-Object 'System.Collections.Generic.List[object]'
 foreach($relative in $files) {
  $target=Join-Path $InstallRoot $relative
  $existed=Test-Path -LiteralPath $target
  $record=@{file=$relative;existed=[bool]$existed;sha256=$null}
  $restoreEntries.Add($record)
  if($existed) {
   $saved=Join-Path $backup $relative
   [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($saved))
   Copy-Item -LiteralPath $target -Destination $saved
   $record.sha256=(Get-FileHash -LiteralPath $saved -Algorithm SHA256).Hash.ToLowerInvariant()
  }
  [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($target))
  $written.Add($relative)
  Copy-Item -LiteralPath (Join-Path $stage $relative) -Destination $target -Force
 }
 $restoreInfo=@{schema=1;from_version=$old;installed_version=$version;files=@($restoreEntries.ToArray())}
 [IO.File]::WriteAllText((Join-Path $backup 'restore.json'),(ConvertTo-Json -InputObject $restoreInfo -Depth 6),(New-Object Text.UTF8Encoding($false)))
 # Reuse private export resources from the legacy local installation if available.
 $legacy=Join-Path $env:LOCALAPPDATA 'ThanhTanApp'
 foreach($relative in @('assets','ThanhTanApp.mvba')) {
  $target=Join-Path $InstallRoot $relative;$source=Join-Path $legacy $relative
  if(-not (Test-Path -LiteralPath $target) -and (Test-Path -LiteralPath $source)){Copy-Item -LiteralPath $source -Destination $target -Recurse}
 }
 $shell=New-Object -ComObject WScript.Shell
 $shortcut=$shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'SonMap+.lnk'))
 $shortcut.TargetPath=Join-Path $InstallRoot 'start_topology.cmd'
 $shortcut.WorkingDirectory=$InstallRoot
 $shortcut.IconLocation=Join-Path $InstallRoot 'sonmap.ico'
 $shortcut.Description='SonMap+ V'+$version
 $shortcut.Save()
 $tools=Join-Path $storage 'Tools';[void](New-Item -ItemType Directory -Path $tools -Force)
 Copy-Item -LiteralPath (Join-Path $stage 'installer/restore.ps1') -Destination (Join-Path $tools 'Khoi_phuc.ps1') -Force
 Copy-Item -LiteralPath (Join-Path $stage 'installer/restore.cmd') -Destination (Join-Path $tools 'Khoi_phuc.cmd') -Force
 $restoreShortcut=$shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'SonMap+ - Khoi phuc.lnk'))
 $restoreShortcut.TargetPath=Join-Path $tools 'Khoi_phuc.cmd'
 $restoreShortcut.Arguments='-InstallRoot "'+$InstallRoot+'"'
 $restoreShortcut.WorkingDirectory=$tools
 $restoreShortcut.IconLocation=Join-Path $InstallRoot 'sonmap.ico'
 $restoreShortcut.Save()
 $committed=$true
 Log ('Installed SonMap+ V'+$version+' to '+$InstallRoot)
 Log ('Previous program files saved in '+$backup)
 Log 'Desktop shortcut: SonMap+. Your DGN/MDB and existing user data are preserved.'
 if(-not $NoLaunch){Start-Process -FilePath (Join-Path $InstallRoot 'start_topology.cmd') -WorkingDirectory $InstallRoot}
 exit 0
} catch {
 if(-not $committed -and $backup) {
  foreach($relative in $written) {
   $saved=Join-Path $backup $relative;$target=Join-Path $InstallRoot $relative
   if(Test-Path -LiteralPath $saved){Copy-Item -LiteralPath $saved -Destination $target -Force}
   elseif(Test-Path -LiteralPath $target){Remove-Item -LiteralPath $target}
  }
 }
 Log ('INSTALLATION STOPPED: '+$_.Exception.Message)
 Log ('Log file: '+$log)
 exit 1
} finally {
 if(Test-Path -LiteralPath $stage){Remove-Item -LiteralPath $stage -Recurse -Force}
}
