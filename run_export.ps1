param([switch]$Probe, [string]$Project = 'ThanhTanApp', [ValidateSet('TrichLuc','GCN','Mau03')][string]$Mode = 'TrichLuc')
$ErrorActionPreference='Stop'
try {
 $application=[Runtime.InteropServices.Marshal]::GetActiveObject('MicroStationDGN.Application')
 if($null -eq $application){throw 'MicroStation is not running.'}
 if($Probe){Write-Output 'CONNECTED';exit 0}
 if($Project -notmatch '^[A-Za-z0-9_ -]+$'){throw 'Invalid VBA project name.'}
 $macro=if($Mode -eq 'Mau03'){'XuatMau03'}elseif($Mode -eq 'GCN'){'InGCN'}else{'XuatTuDanhSach'}
 $keyin='vba run ['+$Project+']LH_ThanhTanApp.'+$macro
 $application.CadInputQueue.SendKeyin($keyin)
 Write-Output 'QUEUED'
} catch {
 Write-Error ('Open MicroStation and import LH_ThanhTanApp.bas first. '+$_.Exception.Message)
 exit 1
}
