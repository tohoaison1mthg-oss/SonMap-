param([Parameter(Mandatory=$true)][string]$Directory)
$ErrorActionPreference='Stop'
$ready=Join-Path $Directory 'ready.json'
if(Test-Path -LiteralPath $ready) {
 $prior=Get-Content -LiteralPath $ready -Raw -Encoding UTF8 | ConvertFrom-Json
 $process=Get-Process -Id ([int]$prior.pid) -ErrorAction SilentlyContinue
 if($process -and $process.ProcessName -eq 'ustation' -and $process.StartTime.ToUniversalTime().Ticks -eq [long]$prior.start){Write-Output 'BRIDGE_ALREADY_READY';exit 0}
 Remove-Item -LiteralPath $ready
}
$assemblies=Join-Path ${env:ProgramFiles(x86)} 'Bentley\MicroStation V8i (SELECTseries)\MicroStation\assemblies'
$interop=Join-Path $assemblies 'bentley.interop.microstationdgn.dll'
$microstation=Join-Path $assemblies 'bentley.microstation.dll'
$hostAssembly=Join-Path (Split-Path $assemblies -Parent) 'ustation.dll'
if(-not (Test-Path -LiteralPath $hostAssembly)){$hostAssembly=Join-Path $assemblies 'ustation.dll'}
$inline=[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'dgn_interop.ps1'))
$start=$inline.IndexOf("using System;")
$end=$inline.LastIndexOf("'@")
if($start -lt 0 -or $end -le $start){throw 'Missing bridge interop source.'}
$records=$inline.Substring($start,$end-$start).Replace('SonMapV8iRecords','SonMapInProcessRecords')
$wrapper=[IO.File]::ReadAllText((Join-Path $PSScriptRoot 'cad_bridge.cs'))
$identity=Split-Path $Directory -Leaf
$taskId=('SMF'+$identity.Substring(0,8)).ToUpperInvariant()
$target=Join-Path $Directory ($taskId+'.dll')
[void](New-Item -ItemType Directory -Path $Directory -Force)
$wrapper=$wrapper.Replace('SONMAPFAST',$taskId)
$source="namespace SonMapFast$identity {`n"+$records+"`n}`nnamespace SonMapFast$identity {`n"+$wrapper+"`n}"
if(-not (Test-Path -LiteralPath $target)) {
 Add-Type -TypeDefinition $source -ReferencedAssemblies @($interop,$microstation,$hostAssembly,(Join-Path $assemblies 'ECFramework/Bentley.General.1.0.dll'),(Join-Path $assemblies 'bentley.microstation.interfaces.1.0.dll'),'System.Windows.Forms','System.Web.Extensions') -OutputAssembly $target -OutputType Library
}
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('MicroStationDGN.Application')
$search=[string]$app.ActiveWorkspace.ConfigurationVariableValue('MS_ADDINPATH')
if(($search -split ';') -notcontains ($Directory+'\')) {
 $app.ActiveWorkspace.AddConfigurationVariable('MS_ADDINPATH',($search.TrimEnd(';')+';'+$Directory+'\'))
}
$app.CadInputQueue.SendKeyin('MDL LOAD "'+$target+'",'+$taskId)
Write-Output 'BRIDGE_LOAD_REQUESTED'
