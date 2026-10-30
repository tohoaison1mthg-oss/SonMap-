# Per-user source updater. No administrator access or private CAD data required.
param([string]$InstallRoot,[switch]$NoLaunch,[switch]$IsolatedTest)
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
 # Optional full-install resources stay separate from the public source payload.
 $resourceScript=Join-Path $stage 'installer\full_resources.ps1'
 if(Test-Path -LiteralPath (Join-Path $PSScriptRoot 'resources.zip')) {
  & $resourceScript -InstallRoot $InstallRoot -BundleRoot $PSScriptRoot -ValidateOnly
 }
 if(Test-Path -LiteralPath (Join-Path $PSScriptRoot 'prerequisites')) {
  Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'prerequisites') -Destination (Join-Path $stage 'prerequisites') -Recurse
 }
 $old=$null
 $installed=Join-Path $InstallRoot 'VERSION'
 if(Test-Path -LiteralPath $installed) {
  $old=([IO.File]::ReadAllText($installed)).Trim()
  if([version]$old -gt [version]$version){throw ('A newer version V'+$old+' is installed; refusing to downgrade.')}
 }
 # Never replace application modules while the old copy is running.
 if(-not $IsolatedTest) {
 foreach($proc in Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'") {
  if($proc.CommandLine -and $proc.CommandLine -match ('(?i)'+[regex]::Escape($InstallRoot+'\')+'(launch|app)\.py(?:"|\s|$)')) {
   throw 'Close the installed SonMap window, then run this installer again.'
  }
 }
 }
 [void](New-Item -ItemType Directory -Path $InstallRoot -Force)
 # Prepare dependencies first. If this fails, existing application files are unchanged.
 Log 'Preparing Python and dependencies (offline when full installer is used).'
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
 $legacy=if($IsolatedTest){Join-Path $storage 'isolated-legacy'}else{Join-Path $env:LOCALAPPDATA 'ThanhTanApp'}
 foreach($relative in @('assets','ThanhTanApp.mvba')) {
  $target=Join-Path $InstallRoot $relative;$source=Join-Path $legacy $relative
  if(-not (Test-Path -LiteralPath $target) -and (Test-Path -LiteralPath $source)){Copy-Item -LiteralPath $source -Destination $target -Recurse}
 }
 if(Test-Path -LiteralPath (Join-Path $PSScriptRoot 'resources.zip')) {
  & $resourceScript -InstallRoot $InstallRoot -BundleRoot $PSScriptRoot
 }
 if(-not $IsolatedTest) {
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
 $cadShortcut=$shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'SonMap+ - MicroStation V8i.lnk'))
 $cadShortcut.TargetPath=$powershell
 $cadShortcut.Arguments='-NoProfile -ExecutionPolicy Bypass -File "'+(Join-Path $InstallRoot 'start_v8i.ps1')+'" -NewSession'
 $cadShortcut.WorkingDirectory=$InstallRoot
 $cadShortcut.IconLocation=Join-Path $InstallRoot 'sonmap.ico'
 $cadShortcut.WindowStyle=7
 $cadShortcut.Save()
 }
 $committed=$true
 # Old MicroStation VBA can call ThanhTanApp/app.py directly, bypassing the
 # current Desktop shortcut. Preserve that app and forward its entry point.
 $repairPython=Join-Path $InstallRoot '.venv-topology\Scripts\python.exe'
 & $repairPython (Join-Path $InstallRoot 'legacy_startup.py') --legacy-root $legacy 2>&1 | ForEach-Object {Log ([string]$_)}
 if($LASTEXITCODE -ne 0){throw 'Program installed, but legacy startup repair failed. See install log.'}
 Log ('Installed SonMap+ V'+$version+' to '+$InstallRoot)
 Log ('Previous program files saved in '+$backup)
 Log 'Desktop shortcut: SonMap+. Your DGN/MDB and existing user data are preserved.'
 if(-not $NoLaunch) {
  Log 'Checking DGN scan in the running V8i (read-only snapshot test).'
  $scanShell=Join-Path $env:SystemRoot 'SysWOW64\WindowsPowerShell\v1.0\powershell.exe'
  $scanProcess=$null;$scanCode=1
  try {
   $scanInfo=New-Object Diagnostics.ProcessStartInfo
   $scanInfo.FileName=$scanShell
   $scanInfo.Arguments='-NoProfile -ExecutionPolicy Bypass -File "'+(Join-Path $InstallRoot 'test_scan_v8i.ps1')+'"'
   $scanInfo.UseShellExecute=$false;$scanInfo.CreateNoWindow=$true
   $scanInfo.RedirectStandardOutput=$true;$scanInfo.RedirectStandardError=$true
   $scanProcess=New-Object Diagnostics.Process;$scanProcess.StartInfo=$scanInfo
   [void]$scanProcess.Start()
   $scanOutput=$scanProcess.StandardOutput.ReadToEndAsync();$scanError=$scanProcess.StandardError.ReadToEndAsync()
   if($scanProcess.WaitForExit(150000)) {
    $scanCode=$scanProcess.ExitCode
    Log $scanOutput.Result;Log $scanError.Result
   } else {$scanProcess.Kill();Log 'V8i scan timed out; test not verified. Installation remains complete.'}
  } catch {Log ('V8i scan unavailable: '+$_.Exception.Message)}
  finally {if($scanProcess){$scanProcess.Dispose()}}
  if($scanCode -ne 0){Log 'V8i scan not verified. Open/save the DGN and run Kiem_tra_quet_DGN.cmd; send its report if it fails.'}
  Start-Process -FilePath (Join-Path $InstallRoot 'start_topology.cmd') -WorkingDirectory $InstallRoot
 }
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
