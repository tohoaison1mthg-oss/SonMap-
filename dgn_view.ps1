param([ValidateSet('Hide','Restore','Focus','Check')][string]$Action,[string]$PlanPath)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot 'dgn_interop.ps1')
InitializeSonMapInterop
$plan=Get-Content -LiteralPath $PlanPath -Raw -Encoding UTF8 | ConvertFrom-Json
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('MicroStationDGN.Application')
$design=$app.ActiveDesignFile
if([IO.Path]::GetFullPath($design.FullName) -ne [IO.Path]::GetFullPath($plan.source)){throw 'Active DGN changed; view operation cancelled.'}
if($plan.model -and [string]$app.ActiveModelReference.Name -ne [string]$plan.model){throw 'Active model changed; view operation cancelled.'}
if($Action -eq 'Check'){Write-Output 'CONTEXT_VERIFIED';exit 0}
if($Action -eq 'Focus') {
 if($app.ActiveModelReference.Is3D){throw 'Only 2D parcel views are supported.'}
 if([double]$plan.span -le 0){throw 'Invalid view span.'}
 [SonMapV8iRecords]::Focus($app,[double]$plan.x,[double]$plan.y,[double]$plan.span)
 Write-Output 'FOCUSED';exit 0
}
if($Action -eq 'Hide') {
 if(Test-Path -LiteralPath $plan.state){throw 'A view state already exists. Restore it first.'}
 $saved=New-Object 'System.Collections.Generic.List[object]'
 foreach($view in $design.Views) {
  if(-not $view.IsOpen){continue}
  foreach($level in $design.Levels){$saved.Add(@{view=[int]$view.Index;level=[int]$level.Number;shown=[bool]$view.IsLevelShown($level)})}
 }
 $state=@{source=[string]$design.FullName;model=[string]$app.ActiveModelReference.Name;levels=@($saved.ToArray())}
 [IO.File]::WriteAllText($plan.state,(ConvertTo-Json -InputObject $state -Depth 6),(New-Object Text.UTF8Encoding($false)))
 try {
  foreach($item in $saved) {
   $view=$design.Views.Item([int]$item.view)
   foreach($level in $design.Levels) {
    if([int]$level.Number -ne [int]$item.level){continue}
    if(@($plan.levels) -contains [int]$level.Number){$view.ShowLevel($level)}else{$view.HideLevel($level)}
   }
  }
  foreach($view in $design.Views){if($view.IsOpen){$view.Redraw()}}
 } catch {
  foreach($item in $saved){$view=$design.Views.Item([int]$item.view);foreach($level in $design.Levels){if([int]$level.Number -eq [int]$item.level){if($item.shown){$view.ShowLevel($level)}else{$view.HideLevel($level)}}}}
  throw
 }
 Write-Output 'LEVELS_HIDDEN_ONLY';exit 0
}
$state=Get-Content -LiteralPath $plan.state -Raw -Encoding UTF8 | ConvertFrom-Json
if([IO.Path]::GetFullPath($state.source) -ne [IO.Path]::GetFullPath($design.FullName) -or [string]$state.model -ne [string]$app.ActiveModelReference.Name){throw 'Restore the view in the same DGN and model.'}
foreach($item in $state.levels) {
 $view=$design.Views.Item([int]$item.view)
 foreach($level in $design.Levels) {
  if([int]$level.Number -ne [int]$item.level){continue}
  if($item.shown){$view.ShowLevel($level)}else{$view.HideLevel($level)}
 }
}
foreach($view in $design.Views){if($view.IsOpen){$view.Redraw()}}
Write-Output 'LEVEL_DISPLAY_RESTORED'
