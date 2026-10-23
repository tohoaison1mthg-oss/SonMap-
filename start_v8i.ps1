param([switch]$NewSession)
$ErrorActionPreference='Stop'
try {
 if(-not $NewSession){try {$a=[Runtime.InteropServices.Marshal]::GetActiveObject('MicroStationDGN.Application');Write-Output 'CONNECTED';exit 0}catch{}}
 $exe=Join-Path ${env:ProgramFiles(x86)} 'Bentley\MicroStation V8i (SELECTseries)\MicroStation\ustation.exe'
 if(-not (Test-Path -LiteralPath $exe)){throw 'MicroStation V8i executable was not found.'}
 $profile=Join-Path $env:ProgramData 'Bentley\MicroStation V8i (SELECTseries)\WorkSpace\Users\SonMap.ucf'
 if(-not(Test-Path -LiteralPath $profile)){
  & (Join-Path $PSScriptRoot 'setup_fast_workspace.ps1') -Root $PSScriptRoot
  if($LASTEXITCODE -ne 0){exit 1}
 }
 # Independent User, same project resources and V7 workmode; no vendor init.
 Start-Process -FilePath $exe -ArgumentList @('-wuSonMap','-wpVietMapXM') -WindowStyle Hidden
 Write-Output 'STARTING: select a DGN in MicroStation; SonMap will connect automatically.'
}catch{Write-Output $_.Exception.Message;exit 1}
