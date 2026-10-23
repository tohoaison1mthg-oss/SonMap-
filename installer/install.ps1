param([string]$TestRoot)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$root=Join-Path $env:LOCALAPPDATA 'ThanhTanApp'
if($TestRoot){$root=[IO.Path]::GetFullPath($TestRoot)}
$backup=Join-Path $root ('backup-20261023-'+[Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $backup -Force | Out-Null
try {
 if(-not $TestRoot){
  foreach($proc in Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'"){
   if($proc.ExecutablePath -and $proc.ExecutablePath.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase) -and $proc.CommandLine -match '(launch|app)\.py'){
    $p=Get-Process -Id $proc.ProcessId -ErrorAction SilentlyContinue
    if($p){$null=$p.CloseMainWindow();if(-not $p.WaitForExit(8000)){throw 'Hay luu thong tin va dong ThanhTanApp roi chay lai file cai dat.'}}
   }
  }
 }
 $zip=[IO.Compression.ZipFile]::OpenRead((Join-Path $PSScriptRoot 'payload.zip'))
 try{
  foreach($entry in $zip.Entries){
   $dest=[IO.Path]::GetFullPath((Join-Path $root $entry.FullName))
   if(-not $dest.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid package path'}
   if($entry.FullName.EndsWith('/')){continue}
   $preserve=$entry.FullName.StartsWith('assets/') -or $entry.FullName.StartsWith('runtime/') -or $entry.FullName -eq 'ThanhTanApp.mvba'
   if((Test-Path -LiteralPath $dest) -and $preserve){continue}
   if(Test-Path -LiteralPath $dest){$b=Join-Path $backup $entry.FullName;[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($b))|Out-Null;Copy-Item -LiteralPath $dest -Destination $b}
   [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($dest))|Out-Null
   [IO.Compression.ZipFileExtensions]::ExtractToFile($entry,$dest,$true)
  }
 }finally{$zip.Dispose()}
 New-Item -ItemType Directory -Path (Join-Path $root 'data') -Force|Out-Null
 foreach($name in 'source.json','source_snapshot.mdb','overrides.json','parcels.tsv','runtime.txt','manifest.json'){
  $old=Join-Path $root ('data\'+$name)
  if(Test-Path -LiteralPath $old){$b=Join-Path $backup ('data\'+$name);[IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($b))|Out-Null;Copy-Item -LiteralPath $old -Destination $b}
 }
 $python=Join-Path $root 'runtime\python.exe'
 $out=& $python (Join-Path $root 'setup_prepare.py') $root 2>&1
 $out|Out-File -LiteralPath (Join-Path $root 'data\setup-20261023.log') -Encoding UTF8
 if($LASTEXITCODE -ne 0){throw 'Preparation failed. See data\setup-20261023.log'}
 if($TestRoot){Write-Output 'PASS: isolated installation and VBA generation';exit 0}
 $vbaLog=Join-Path $root 'data\setup-vba-20261023.log'
 $vbaError=Join-Path $root 'data\setup-vba-stderr.log'
 $vp=Start-Process -FilePath (Join-Path $env:WINDIR 'SysWOW64\WindowsPowerShell\v1.0\powershell.exe') -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+(Join-Path $root 'update_vba.ps1')+'"'),'-Root',('"'+$root+'"')) -RedirectStandardOutput $vbaLog -RedirectStandardError $vbaError -WindowStyle Hidden -Wait -PassThru
 $ready=$vp.ExitCode -eq 0
 $shell=New-Object -ComObject WScript.Shell
 $shortcut=$shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'SonMap+ V10.3.lnk'))
 $shortcut.TargetPath=Join-Path $root 'runtime\pythonw.exe';$shortcut.Arguments='"'+(Join-Path $root 'launch.py')+'"';$shortcut.WorkingDirectory=$root;$shortcut.IconLocation=(Join-Path $root 'sonmap.ico');$shortcut.Save()
 $profileOutput=& (Join-Path $root 'setup_fast_workspace.ps1') -Root $root
 $profileOutput|Out-File -LiteralPath (Join-Path $root 'data\fast-workspace-install.log') -Encoding UTF8
 if($LASTEXITCODE -eq 0){
  $fast=$shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'SonMap - V8i V7.lnk'))
  $fast.TargetPath=Join-Path $env:WINDIR 'SysWOW64\WindowsPowerShell\v1.0\powershell.exe'
  $fast.Arguments='-NoProfile -ExecutionPolicy Bypass -File "'+(Join-Path $root 'start_v8i.ps1')+'" -NewSession'
  $fast.WorkingDirectory=$root;$fast.IconLocation=Join-Path $root 'sonmap.ico';$fast.WindowStyle=7;$fast.Save()
 }
 [IO.File]::WriteAllText((Join-Path $root 'installed-by-setup.txt'),'ThanhTanApp 2026-10-23 - Automatic DGN workflow')
 Start-Process -FilePath (Join-Path $root 'runtime\pythonw.exe') -ArgumentList ('"'+(Join-Path $root 'launch.py')+'"') -WorkingDirectory $root -WindowStyle Hidden
 if(-not $ready){Write-Output 'Giao dien moi da cai va mo. Mo MicroStation V8i va DGN nguon; app se tu thu cap nhat VBA khi bam xuat. Khong can copy hay import file.';exit 0}
 Write-Output 'Cai xong giao dien va module VBA. Mo DGN nguon co MDB cung ten de su dung.'
}catch{$_|Out-File -LiteralPath (Join-Path $root 'setup-error.log') -Encoding UTF8;throw}
