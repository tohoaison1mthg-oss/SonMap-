# External COM callers must supply Scan's ElementScanCriteria argument explicitly.
function NewSonMapScan($Application,$Model,[string]$Phase='scan') {
 $script:Stage=$Phase+'-create-criteria'
 $criteria=$Application.CreateObjectInMicroStation('MicroStationDGN.ElementScanCriteria')
 if($null -eq $criteria){throw 'MicroStation did not create ElementScanCriteria.'}
 $script:Stage=$Phase+'-start-with-criteria'
 $enumerator=$Model.Scan($criteria)
 if($null -eq $enumerator){throw 'MicroStation Scan returned no enumerator.'}
 return [pscustomobject]@{Criteria=$criteria;Enumerator=$enumerator;Phase=$Phase}
}
function MoveSonMapScan($Context) {
 $script:Stage=$Context.Phase+'-next-element'
 return [bool]$Context.Enumerator.MoveNext()
}
function ReadSonMapScanCurrent($Context) {
 $script:Stage=$Context.Phase+'-current-element'
 $element=$Context.Enumerator.Current
 if($null -eq $element){throw 'MicroStation returned an empty current element after MoveNext.'}
 return $element
}
