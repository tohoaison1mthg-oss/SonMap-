# Python discovery and signed, per-user dependency installation for SonMap.
$script:PythonProbeCache=@{}
function TestPython([string]$Executable,[string[]]$Prefix=@()) {
 if(-not $Executable -or $Executable -match '\\Microsoft\\WindowsApps\\'){return $false}
 $key=$Executable+'|'+($Prefix -join ' ')
 if($script:PythonProbeCache.ContainsKey($key)){return $script:PythonProbeCache[$key]}
 $ok=$false;$process=$null
 try {
  $info=New-Object Diagnostics.ProcessStartInfo
  $info.FileName=$Executable
  # Only fixed launcher switches and a .py path are passed; Windows paths cannot contain quotes.
  $arguments=@($Prefix)+@((Join-Path $PSScriptRoot 'python_probe.py'))
  $info.Arguments=($arguments | ForEach-Object {'"'+$_+'"'}) -join ' '
  $info.UseShellExecute=$false;$info.CreateNoWindow=$true
  $info.RedirectStandardOutput=$true;$info.RedirectStandardError=$true
  $process=New-Object Diagnostics.Process;$process.StartInfo=$info
  [void]$process.Start()
  $stdout=$process.StandardOutput.ReadToEndAsync();$stderr=$process.StandardError.ReadToEndAsync()
  if(-not $process.WaitForExit(15000)){$process.Kill();throw 'Python probe timed out after 15 seconds.'}
  $text=$stdout.Result.Trim()
  try {
   $report=$text | ConvertFrom-Json -ErrorAction Stop
   $ok=($process.ExitCode -eq 0 -and $report.compatible -eq $true)
   Write-Host ('Python check: '+$Executable+' -> '+$report.reason)
  } catch {
   $errorText=$stderr.Result.Trim()
   if($errorText.Length -gt 500){$errorText=$errorText.Substring(0,500)}
   Write-Host ('Python check failed: '+$Executable+' '+($Prefix -join ' ')+' '+$errorText)
  }
 } catch {Write-Host ('Python check failed: '+$Executable+' - '+$_.Exception.Message)}
 finally {if($process){$process.Dispose()}}
 $script:PythonProbeCache[$key]=$ok
 return $ok
}

function InstallSonMapPython([string]$TargetDirectory) {
 if(Test-Path -LiteralPath $TargetDirectory){throw ('Private Python directory already exists but is not usable: '+$TargetDirectory+'. See Python check output; no existing Python was replaced.')}
 foreach($base in @('HKCU:\Software\Python\PythonCore','HKLM:\Software\Python\PythonCore')) {
  foreach($name in @('3.12','3.12-64')) {
   if(Test-Path -LiteralPath ($base+'\'+$name+'\InstallPath')) {
    throw 'A registered Python 3.12 exists but failed the component check. Use its installer Modify/Repair to enable Tcl/Tk, pip and venv; no Python was replaced.'
   }
  }
 }
 $temporary=Join-Path ([IO.Path]::GetTempPath()) ('SonMapPython-'+[Guid]::NewGuid().ToString('N'))
 [void](New-Item -ItemType Directory -Path $temporary -Force)
 try {
  $installer=Join-Path $temporary 'python-3.12.10-amd64.exe'
  $url='https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe'
  Write-Host 'Preparing a separate Python 3.12 for SonMap. Your other Python versions remain installed.'
  $bundled=Join-Path $PSScriptRoot 'prerequisites\python-3.12.10-amd64.exe'
  if(Test-Path -LiteralPath $bundled){
   Write-Host 'Using bundled Python installer (offline).'
   Copy-Item -LiteralPath $bundled -Destination $installer
  } else {
   Write-Host ('Downloading from '+$url)
   [Net.ServicePointManager]::SecurityProtocol=[Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
   Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $installer
  }
  $signature=Get-AuthenticodeSignature -LiteralPath $installer
  if($signature.Status -ne 'Valid' -or $null -eq $signature.SignerCertificate -or $signature.SignerCertificate.Subject -notmatch '(^|,\s*)O=Python Software Foundation(,|$)') {
   throw 'Python installer signature is invalid or not from Python Software Foundation. Installation stopped.'
  }
  Write-Host ('Python installer SHA256: '+(Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash)
  $arguments='/quiet InstallAllUsers=0 Include_launcher=0 InstallLauncherAllUsers=0 AssociateFiles=0 Shortcuts=0 PrependPath=0 AppendPath=0 Include_doc=0 Include_test=0 Include_tools=0 Include_tcltk=1 Include_pip=1 TargetDir="'+$TargetDirectory+'" /log "'+(Join-Path $temporary 'install.log')+'"'
  $process=Start-Process -FilePath $installer -ArgumentList $arguments -WindowStyle Hidden -PassThru -Wait
  if($process.ExitCode -notin @(0,3010)) {
   $keep=Join-Path $logDirectory 'python-install.log'
   $logs=@(Get-ChildItem -LiteralPath $temporary -Filter '*.log' -File)
   foreach($file in $logs){Add-Content -LiteralPath $keep -Value ([IO.File]::ReadAllText($file.FullName)) -Encoding UTF8}
   throw ('Python installer failed with exit code '+$process.ExitCode+'. Log: '+$keep)
  }
  $executable=Join-Path $TargetDirectory 'python.exe'
  [void]$script:PythonProbeCache.Remove($executable+'|')
  if(-not (TestPython $executable)){throw 'Installed Python did not pass the component check.'}
  return $executable
 } finally {if(Test-Path -LiteralPath $temporary){Remove-Item -LiteralPath $temporary -Recurse -Force}}
}
