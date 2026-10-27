# Real V8i scan smoke test. Reads the active model and a temporary disk snapshot only.
param([string]$Levels='10,23,32')
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'dgn_models.ps1')
. (Join-Path $PSScriptRoot 'dgn_scan.ps1')
. (Join-Path $PSScriptRoot 'dgn_interop.ps1')
$report=[ordered]@{version=([IO.File]::ReadAllText((Join-Path $PSScriptRoot 'VERSION'))).Trim();status='not_run';levels=$Levels;source_unchanged=$false}
$folder=Join-Path $PSScriptRoot 'data'
[void](New-Item -ItemType Directory -Path $folder -Force)
$path=Join-Path $folder ('v8i-scan-'+(Get-Date -Format 'yyyyMMdd-HHmmss')+'.json')
$temp=$null;$design=$null;$code=1
function CountScan($application,$model,$wanted,[string]$phase) {
 $scan=NewSonMapScan $application $model $phase
 $total=0;$selected=0;$geometry=0;$timer=[Diagnostics.Stopwatch]::StartNew()
 while(MoveSonMapScan $scan) {
  if($timer.Elapsed.TotalSeconds -gt 120){throw 'Scan exceeded 120 seconds; this test is incomplete.'}
  $element=ReadSonMapScanCurrent $scan
  $total++
  if($wanted -contains [int]$element.Level.Number){
   $selected++
   if([int]$element.Type -in @(3,4,6)) {
    $points=[SonMapV8iRecords]::Vertices($element,$false,.001)
    if($points.Count -lt 2){throw 'Selected boundary has fewer than two vertices.'}
    $geometry++
   }
  }
 }
 return @{total=$total;selected=$selected;geometry_lines=$geometry}
}
try {
 $wanted=@($Levels.Split(',') | ForEach-Object {[int]$_.Trim()})
 if($wanted.Count -eq 0 -or @($wanted | Where-Object {$_ -lt 1 -or $_ -gt 63}).Count){throw 'Levels must be numbers 1 through 63.'}
 $script:Stage='connect-v8i'
 $app=[Runtime.InteropServices.Marshal]::GetActiveObject('MicroStationDGN.Application')
 InitializeSonMapInterop
 $source=[string]$app.ActiveDesignFile.FullName
 if(-not (Test-Path -LiteralPath $source)){throw 'Open and save a DGN in V8i first.'}
 $report.source=$source;$report.model=[string]$app.ActiveModelReference.Name
 $default=TestSonMapDefaultModel $app.ActiveDesignFile $app.ActiveModelReference
 $before=(Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
 $temp=Join-Path ([IO.Path]::GetTempPath()) ('SonMapScan-'+[Guid]::NewGuid().ToString('N'))
 [void](New-Item -ItemType Directory -Path $temp)
 $copy=Join-Path $temp ([IO.Path]::GetFileName($source))
 Copy-Item -LiteralPath $source -Destination $copy
 if((Get-FileHash -LiteralPath $copy -Algorithm SHA256).Hash -ne $before){throw 'Source changed during snapshot copy.'}
 $report.live=CountScan $app $app.ActiveModelReference $wanted 'live-scan'
 $script:Stage='open-readonly-snapshot'
 $design=$app.OpenDesignFileForProgram($copy,$true)
 $model=ResolveSonMapModel $design $report.model $default
 $report.snapshot=CountScan $app $model $wanted 'snapshot-scan'
 $report.source_unchanged=((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -eq $before)
 if(-not $report.source_unchanged){throw 'Source changed during the test; results are not validated.'}
 if($report.live.total -ne $report.snapshot.total -or $report.live.selected -ne $report.snapshot.selected) {
  $report.status='counts_differ_save_dgn_and_retry';$code=3
 } elseif($report.snapshot.selected -eq 0 -or $report.snapshot.geometry_lines -eq 0) {
  $report.status='no_elements_on_selected_levels';$code=3
 } else {$report.status='scan_passed';$code=0}
} catch {$report.status='failed';$report.stage=$script:Stage;$report.error=$_.Exception.Message;$report.line=$_.InvocationInfo.ScriptLineNumber}
finally {
 if($design){try{$design.Close()}catch{$report.close_error=$_.Exception.Message;$report.status='failed';$code=1}}
 if($temp -and (Test-Path -LiteralPath $temp)){Remove-Item -LiteralPath $temp -Recurse -Force}
 [IO.File]::WriteAllText($path,(ConvertTo-Json -InputObject $report -Depth 8),(New-Object Text.UTF8Encoding($false)))
}
Write-Host ('V8i scan result: '+$report.status)
Write-Host ('Report: '+$path)
if($report.error){Write-Host ('Step: '+$report.stage+'; '+$report.error)}
Write-Host 'No original DGN/MDB or MicroStation configuration was modified by this test.'
exit $code
