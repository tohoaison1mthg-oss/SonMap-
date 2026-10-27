# Real V8i COM record test. Constructs detached elements only; never adds them to a DGN.
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'dgn_interop.ps1')
InitializeSonMapInterop
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('MicroStationDGN.Application')
if(-not $app.ActiveDesignFile.FullName){throw 'Open a DGN in V8i first.'}
$level=$app.ActiveSettings.Level
$line=[SonMapV8iRecords]::Line($app,[double[][]]@(@(600000,1000000),@(600010,1000010)))
$points=[SonMapV8iRecords]::Vertices($line,$false,.001)
if($points.Count -ne 2 -or $points[0][0] -ne 600000 -or $points[1][1] -ne 1000010){throw 'Line record roundtrip mismatch.'}
$cell=[SonMapV8iRecords]::TextCell($app,'test',600005,1000005,$level,3,1)
$children=$cell.AsComplexElement.GetSubElements()
if(-not $children.MoveNext()){throw 'Missing text child.'}
$point=[SonMapV8iRecords]::TextOrigin($children.Current)
if($point[0] -ne 600005 -or $point[1] -ne 1000005){throw 'Text origin record mismatch.'}
$marker=[SonMapV8iRecords]::ErrorCell($app,600005,1000005,.01,$level,3)
if($marker.Name -ne 'SMERR'){throw 'Error cell constructor failed.'}
Write-Output 'PASS: real V8i line vertices, text origin and marker records; no elements added or files saved.'
