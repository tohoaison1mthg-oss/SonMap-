$ErrorActionPreference='Stop'
try {
 try {$app=[Runtime.InteropServices.Marshal]::GetActiveObject('MicroStationDGN.Application')} catch {exit 2}
 $path=$app.ActiveDesignFile.FullName
 if($path -and [IO.File]::Exists($path)) {
  [Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
  [Console]::Write($path)
 } else {exit 3}
} catch {exit 1}
