param([string]$Root,[switch]$ProbeOnly)
$ErrorActionPreference='Stop'
try{
 try {$a=[Runtime.InteropServices.Marshal]::GetActiveObject('MicroStationDGN.Application')} catch {Write-Output 'MICROSTATION_NOT_RUNNING: Open MicroStation V8i and a source DGN; the app will retry VBA automatically when exporting.';exit 2}
 if($ProbeOnly){Write-Output 'CONNECTED';exit 0}
 $p=$null
 for($i=1;$i -le $a.VBE.VBProjects.Count;$i++){if($a.VBE.VBProjects.Item($i).Name -eq 'ThanhTanApp'){$p=$a.VBE.VBProjects.Item($i);break}}
 if(-not $p){$a.CadInputQueue.SendKeyin('vba load "'+(Join-Path $Root 'ThanhTanApp.mvba')+'"');$p=$a.VBE.VBProjects.Item('ThanhTanApp')}
 $stamp=Get-Date -Format 'yyyyMMdd-HHmmss'
 Copy-Item -LiteralPath $p.FileName -Destination (Join-Path $Root ('data\project-before-'+$stamp+'.mvba'))
 foreach($name in 'LH_ThanhTanApp','LH_KhoiDong','LH_DgnMonitor'){
  $ext=if($name -eq 'LH_DgnMonitor'){'.cls'}else{'.bas'}
  $module=$null;try{$module=$p.VBComponents.Item($name)}catch{}
  if(-not $module){$null=$p.VBComponents.Import((Join-Path $Root ($name+$ext)));continue}
  $null=$module.Export((Join-Path $Root ('data\'+$name+'-before-'+$stamp+$ext)))
  $text=[IO.File]::ReadAllText((Join-Path $Root ($name+$ext)))
  $start=$text.IndexOf('Option Explicit');if($start -lt 0){throw 'Invalid VBA source'}
  if($module.CodeModule.CountOfLines -gt 0){$module.CodeModule.DeleteLines(1,$module.CodeModule.CountOfLines)}
  $module.CodeModule.AddFromString($text.Substring($start))
 }
 $a.CadInputQueue.SendKeyin('vba saveall')
 Write-Output 'VBA sources updated and saved; runtime export not tested by installer.'
}catch{Write-Output ('VBA_UPDATE_FAILED: '+$_.Exception.Message);exit 1}
