# Pure PowerShell fake-object regression. Does not connect to MicroStation.
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'dgn_scan.ps1')
$criteria=[pscustomobject]@{Kind='Criteria'}
$factory=[pscustomobject]@{Criteria=$criteria}
$factory | Add-Member ScriptMethod CreateObjectInMicroStation {
 param($name)
 if($name -ne 'MicroStationDGN.ElementScanCriteria'){throw 'Unexpected COM class.'}
 return $this.Criteria
}
$enumerator=[pscustomobject]@{Position=-1;Elements=@('first','second')}
$enumerator | Add-Member ScriptMethod MoveNext {$this.Position++;return $this.Position -lt $this.Elements.Count}
$enumerator | Add-Member ScriptProperty Current {if($this.Position -lt 0){throw 'Not positioned.'};return $this.Elements[$this.Position]}
$model=[pscustomobject]@{Expected=$criteria;Seen=$false;Enumerator=$enumerator}
$model | Add-Member ScriptMethod Scan {
 param($passed)
 if($null -eq $passed -or $passed -ne $this.Expected){throw 'Scan requires the explicit criteria object.'}
 $this.Seen=$true
 return $this.Enumerator
}
$context=NewSonMapScan $factory $model
if(-not $model.Seen -or $context.Criteria -ne $criteria){throw 'Criteria was not passed or retained.'}
if($script:Stage -ne 'scan-start-with-criteria'){throw 'Unexpected Scan stage.'}
$items=@()
while(MoveSonMapScan $context){$items+=ReadSonMapScanCurrent $context}
if(($items -join ',') -ne 'first,second'){throw 'Enumeration skipped or reordered elements.'}
$broken=[pscustomobject]@{Phase='probe';Enumerator=$null}
$bad=[pscustomobject]@{}
$bad | Add-Member ScriptMethod MoveNext {throw 'Simulated COM bounds error.'}
$broken.Enumerator=$bad
$failed=$false
try{MoveSonMapScan $broken}catch{$failed=$true}
if(-not $failed -or $script:Stage -ne 'probe-next-element'){throw 'MoveNext failure was swallowed or mislabeled.'}
Write-Output 'PASS: criteria passed/retained, elements enumerated, bounds failure preserved with stage.'
