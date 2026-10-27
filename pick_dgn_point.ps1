param([Parameter(Mandatory=$true)][string]$SourcePath)
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
. (Join-Path $PSScriptRoot 'dgn_interop.ps1')
InitializeSonMapInterop
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('MicroStationDGN.Application')
function CheckSource {
 if([IO.Path]::GetFullPath($app.ActiveDesignFile.FullName) -ne [IO.Path]::GetFullPath($SourcePath)){throw 'Active DGN changed. Select the parcel again.'}
 if($app.ActiveModelReference.Is3D){throw 'Only 2D cadastral models are supported.'}
}
CheckSource
$model=[string]$app.ActiveModelReference.Name
try {
 $point=[SonMapV8iRecords]::PickPoint($app)
 CheckSource
 if([string]$app.ActiveModelReference.Name -ne $model){throw 'Active model changed. Select the parcel again.'}
 if($null -eq $point){Write-Output '{"cancelled":true}'}
 else {Write-Output (ConvertTo-Json -Compress -InputObject @{point=$point;source=$SourcePath;model=$model})}
} finally {$app.ShowPrompt('')}
