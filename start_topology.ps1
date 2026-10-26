param([switch]$PrepareOnly,[string]$EnvironmentRoot)
# Detect a real Python installation without requiring the optional py launcher.
$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
if(-not $EnvironmentRoot){$EnvironmentRoot=$PSScriptRoot}
$EnvironmentRoot=[IO.Path]::GetFullPath($EnvironmentRoot)
function TestPython([string]$Executable, [string[]]$Prefix=@()) {
 if(-not $Executable -or $Executable -match '\\Microsoft\\WindowsApps\\'){return $false}
 try {
  $ErrorActionPreference='Continue'
  & $Executable @Prefix -c "import sys,struct,tkinter,venv; sys.exit(0 if sys.version_info[:2]==(3,12) and struct.calcsize('P')==8 else 1)" *> $null
  return $LASTEXITCODE -eq 0
 } catch {return $false}
}
# Windows PowerShell 5.1 can turn native stderr (including Python tracebacks
# and ordinary pip warnings) into a terminating NativeCommandError under Stop.
# Handle native exit codes explicitly and retain every output line in a log.
$logDirectory=Join-Path $PSScriptRoot 'data'
function InvokePython([string]$Executable, [string[]]$PythonArguments) {
 $ErrorActionPreference='Continue'
 & $Executable @PythonArguments 2>&1 | ForEach-Object {
  $line=[string]$_
  Write-Host $line
  Add-Content -LiteralPath (Join-Path $logDirectory 'topology-startup.log') -Value $line -Encoding UTF8
 }
 $script:PythonExitCode=$LASTEXITCODE
}
try {
 [void](New-Item -ItemType Directory -Path $logDirectory -Force)
 Set-Content -LiteralPath (Join-Path $logDirectory 'topology-startup.log') -Value ('SonMap startup: '+(Get-Date -Format s)) -Encoding UTF8
 $venvPython=Join-Path $EnvironmentRoot '.venv-topology\Scripts\python.exe'
 if(Test-Path -LiteralPath $venvPython) {
  if(-not (TestPython $venvPython)){throw 'Existing .venv-topology is incompatible. Rename that folder, then run again with Python 3.12 64-bit installed.'}
 } else {
  $found=$null;$prefix=@()
  $candidates=New-Object 'System.Collections.Generic.List[string]'
  if($env:SONMAP_PYTHON){$candidates.Add($env:SONMAP_PYTHON)}
  foreach($name in 'python','python3') {
   $command=Get-Command $name -CommandType Application -ErrorAction SilentlyContinue
   if($command){$candidates.Add($command.Source)}
  }
  foreach($base in 'HKCU:\Software\Python\PythonCore','HKLM:\Software\Python\PythonCore') {
   foreach($version in '3.12','3.12-64') {
    $key=Get-Item ($base+'\'+$version+'\InstallPath') -ErrorAction SilentlyContinue
    if($key) {
     $executable=$key.GetValue('ExecutablePath')
     if($executable){$candidates.Add($executable)}
     $directory=$key.GetValue('')
     if($directory){$candidates.Add((Join-Path $directory 'python.exe'))}
    }
   }
  }
  foreach($directory in @((Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312'),(Join-Path $env:ProgramFiles 'Python312'),(Join-Path $PSScriptRoot 'runtime'))) {
   $candidates.Add((Join-Path $directory 'python.exe'))
  }
  foreach($candidate in $candidates) {
   if(TestPython $candidate){$found=$candidate;break}
  }
  if(-not $found) {
   $launcher=Get-Command py -CommandType Application -ErrorAction SilentlyContinue
   if($launcher -and (TestPython $launcher.Source @('-3.12'))){$found=$launcher.Source;$prefix=@('-3.12')}
  }
  if(-not $found) {
   Write-Host ''
   Write-Host 'Khong tim thay Python 3.12 64-bit co Tkinter.'
   Write-Host 'Tai ban cai chinh thuc:'
   Write-Host 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe'
   Write-Host 'Cai voi tuy chon Tcl/Tk va pip; sau do chay lai start_topology.cmd.'
   Write-Host 'Khong bat buoc cai Python Launcher (lenh py).'
   Write-Host 'Neu da cai Python o noi khac, dat SONMAP_PYTHON thanh duong dan python.exe.'
   exit 2
  }
  Write-Host ('Python: '+$found)
  InvokePython $found ($prefix + @('-m','venv',(Join-Path $EnvironmentRoot '.venv-topology')))
  if($script:PythonExitCode -ne 0){throw 'Could not create Python virtual environment.'}
 }
 InvokePython $venvPython @('-c',"import importlib.metadata as m, sys; versions={d.metadata['Name'].lower():d.version for d in m.distributions()}; sys.exit(0 if versions.get('shapely')=='2.0.7' else 1)")
 if($script:PythonExitCode -ne 0) {
  InvokePython $venvPython @('-m','pip','install','-r',(Join-Path $PSScriptRoot 'requirements-topology.txt'))
  if($script:PythonExitCode -ne 0){throw 'Could not install topology dependencies. Check the pip error above.'}
 }
 if($PrepareOnly){Write-Host 'Python and topology dependencies are ready.';exit 0}
 InvokePython $venvPython @((Join-Path $PSScriptRoot 'launch.py'))
 if($script:PythonExitCode -ne 0){throw 'SonMap exited with an error; see data/startup-error.log if present.'}
 exit 0
} catch {
 Write-Host ('SonMap: '+$_.Exception.Message)
 Write-Host ('Startup log: '+(Join-Path $logDirectory 'topology-startup.log'))
 exit 1
}
