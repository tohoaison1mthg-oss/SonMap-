param([string]$Target)
$ErrorActionPreference='Stop'
if(-not $Target){$Target=Join-Path $env:USERPROFILE 'SonMap-Dev'}
$git=Get-Command git -CommandType Application -ErrorAction SilentlyContinue
if(-not $git){Write-Host 'Install Git for Windows: winget install --id Git.Git -e --source winget';exit 1}
try {
 $bundle=Join-Path $PSScriptRoot 'SonMap-source.bundle'
 $expected=([IO.File]::ReadAllText((Join-Path $PSScriptRoot 'bundle.sha256'))).Trim()
 if((Get-FileHash -LiteralPath $bundle -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected){throw 'Workspace bundle checksum mismatch.'}
 if(Test-Path -LiteralPath $Target){throw ('Workspace already exists: '+$Target+'. Nothing overwritten. Use its existing sync scripts or choose another target with -Target.')}
 $previous=$ErrorActionPreference
 try {
  $ErrorActionPreference='Continue'
  & $git.Source clone -b codex/sonmap-topology-ui $bundle $Target
  $code=$LASTEXITCODE
 } finally {$ErrorActionPreference=$previous}
 if($code -ne 0){throw 'Could not clone bundled source.'}
 Push-Location -LiteralPath $Target
 try {
  $ErrorActionPreference='Continue'
  & $git.Source remote set-url origin https://github.com/tohoaison1mthg-oss/SonMap-.git
  if($LASTEXITCODE -ne 0){throw 'Could not set the GitHub origin.'}
 } finally {Pop-Location;$ErrorActionPreference='Stop'}
 $legacy=Join-Path $env:LOCALAPPDATA 'SonMapPlus\App'
 foreach($relative in @('assets','ThanhTanApp.mvba')) {
  $source=Join-Path $legacy $relative;$dest=Join-Path $Target $relative
  if((Test-Path -LiteralPath $source) -and -not (Test-Path -LiteralPath $dest)){Copy-Item -LiteralPath $source -Destination $dest -Recurse}
 }
 $shell=New-Object -ComObject WScript.Shell
 $shortcut=$shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'SonMap+ - Phat trien.lnk'))
 $shortcut.TargetPath=Join-Path $Target 'Lam_viec_laptop.cmd';$shortcut.WorkingDirectory=$Target;$shortcut.IconLocation=Join-Path $Target 'sonmap.ico';$shortcut.Save()
 Write-Host ('Source workspace: '+$Target)
 Write-Host 'Run Lam_viec_laptop.cmd to work locally. When finished, run Gui_len_GitHub.cmd and sign in with your own GitHub account.'
 Start-Process -FilePath (Join-Path $Target 'Lam_viec_laptop.cmd') -WorkingDirectory $Target
} catch {Write-Host $_.Exception.Message;exit 1}
