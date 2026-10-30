param([switch]$NewSession,[switch]$ProbeOnly)
$ErrorActionPreference='Stop'
try {
 if(-not $NewSession -and -not $ProbeOnly){try {$a=[Runtime.InteropServices.Marshal]::GetActiveObject('MicroStationDGN.Application');Write-Output 'CONNECTED';exit 0}catch{}}
 $exe=Join-Path ${env:ProgramFiles(x86)} 'Bentley\MicroStation V8i (SELECTseries)\MicroStation\ustation.exe'
 if(-not (Test-Path -LiteralPath $exe)) {
  foreach($key in @('HKLM:\SOFTWARE\WOW6432Node\Bentley\MicroStation\*','HKLM:\SOFTWARE\Bentley\MicroStation\*')) {
   foreach($item in @(Get-ItemProperty -Path $key -ErrorAction SilentlyContinue)) {
    $candidate=if($item.PathName){[string]$item.PathName}elseif($item.ProgramPath){Join-Path $item.ProgramPath 'ustation.exe'}else{''}
    if($candidate -and $candidate -match '(?i)V8i' -and (Test-Path -LiteralPath $candidate)){$exe=$candidate;break}
   }
  }
 }
 if(-not (Test-Path -LiteralPath $exe)){throw 'MicroStation V8i executable was not found.'}
 if($ProbeOnly){Write-Output $exe;exit 0}
 $project=(Join-Path $PSScriptRoot 'ThanhTanApp.mvba').Replace('\','/')
 if(-not (Test-Path -LiteralPath $project)){throw 'Missing SonMap VBA project. Run the full installer.'}
 # Session configuration, no VietMapXM workspace or global profile changes.
 $arguments=@('-wsMS_OPENV7=3',('-wsMS_VBASEARCHDIRECTORIES='+$PSScriptRoot.Replace('\','/')+'/'))
 $quoted=($arguments|ForEach-Object {'"'+$_+'"'}) -join ' '
 Start-Process -FilePath $exe -ArgumentList $quoted -WindowStyle Hidden
 Write-Output 'STARTING: select a DGN in MicroStation; SonMap will connect automatically.'
}catch{Write-Output $_.Exception.Message;exit 1}
