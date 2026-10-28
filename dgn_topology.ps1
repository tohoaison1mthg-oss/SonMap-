param(
 [Parameter(Mandatory=$true)][ValidateSet('Extract','WriteDrawing','WritePreview','WriteMdb','CleanDrawing','TopologyDrawing','SaveActive','ApplyDrawing','ApplyClean','ApplyPreview','RestoreActive')][string]$Action,
 [Parameter(Mandatory=$true)][string]$InputPath,
 [Parameter(Mandatory=$true)][string]$OutputPath,
 [string]$ModelName,
 [string]$SourcePath,
 [double]$ChordTolerance=0.001,
 [switch]$BreakArcs,
 [switch]$AllowEmpty,
 [switch]$KeepComplex,
 [switch]$DefaultModel,
 [string]$BoundaryLevels,
 [switch]$SkipSaveBackup,
 [string]$TextLevels='*'
)
$ErrorActionPreference='Stop'
[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)

$script:Stage='initialize'
trap {
 $failure=[ordered]@{stage=$script:Stage;message=$_.Exception.Message;line=$_.InvocationInfo.ScriptLineNumber;detail=$_.ScriptStackTrace}
 [Console]::Error.WriteLine((ConvertTo-Json -InputObject $failure -Compress))
 exit 1
}
. (Join-Path $PSScriptRoot 'dgn_models.ps1')
. (Join-Path $PSScriptRoot 'dgn_scan.ps1')
. (Join-Path $PSScriptRoot 'dgn_interop.ps1')
function FindLevel($design,[int]$number) {
 if(-not $script:LevelCache){$script:LevelCache=@{}}
 if($script:LevelCache.ContainsKey($number)){return $script:LevelCache[$number]}
 foreach($level in $design.Levels){if([int]$level.Number -eq $number){$script:LevelCache[$number]=$level;return $level}}
 $level=$design.Levels.Add('SonMap_Level_'+$number)
 $level.Number=$number
 $design.Levels.Rewrite()
 $script:LevelCache[$number]=$level
 return $level
}

function WriteJson($path,$value) {
 [IO.File]::WriteAllText($path,(ConvertTo-Json -InputObject $value -Depth 30),(New-Object Text.UTF8Encoding($false)))
}
function FileDigest([string]$path) {
 $stream=[IO.File]::Open($path,[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite)
 $hash=[Security.Cryptography.SHA256]::Create()
 try {return ([BitConverter]::ToString($hash.ComputeHash($stream))).Replace('-','').ToLowerInvariant()}
 finally {$hash.Dispose();$stream.Dispose()}
}
function XY($p) { return ,@([double]$p.X,[double]$p.Y) }
if((Test-Path -LiteralPath $OutputPath) -and $Action -notin @('ApplyDrawing','ApplyClean','ApplyPreview','RestoreActive')){throw 'Output already exists; refusing to overwrite.'}
if($Action -eq 'WriteMdb') {
 $rows=Get-Content -LiteralPath $InputPath -Raw -Encoding UTF8 | ConvertFrom-Json
 if($rows.Count -eq 0 -and -not $AllowEmpty){throw 'No parcels.'}
 $catalog=$null;$connection=$null;$transaction=$null
 try {
  $script:Stage='create-mdb'
  $catalog=New-Object -ComObject ADOX.Catalog
  [void]$catalog.Create('Provider=Microsoft.Jet.OLEDB.4.0;Data Source='+$OutputPath+';Jet OLEDB:Engine Type=5;')
  $catalog.ActiveConnection.Close()
  [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($catalog);$catalog=$null
  $connection=New-Object System.Data.OleDb.OleDbConnection('Provider=Microsoft.Jet.OLEDB.4.0;Data Source='+$OutputPath+';')
  $connection.Open()
  $cmd=$connection.CreateCommand()
  $cmd.CommandText='CREATE TABLE ThuaDat (ID INTEGER NOT NULL PRIMARY KEY, ToBD INTEGER, TCT INTEGER, DienTich DOUBLE, TenChu TEXT(255), DiaChi TEXT(255), DiaChiThuaDatChiTiet TEXT(255), Xudong TEXT(255), LRD TEXT(255), MaLD TEXT(255), Geometry LONGBINARY)'
  [void]$cmd.ExecuteNonQuery();$cmd.Dispose()
  $transaction=$connection.BeginTransaction()
  foreach($row in $rows) {
   $cmd=$connection.CreateCommand();$cmd.Transaction=$transaction
   $cmd.CommandText='INSERT INTO ThuaDat (ID,ToBD,TCT,DienTich,TenChu,DiaChi,DiaChiThuaDatChiTiet,Xudong,LRD,MaLD,Geometry) VALUES (?,?,?,?,?,?,?,?,?,?,?)'
   foreach($field in 'ID','ToBD','TCT'){$p=$cmd.Parameters.Add('@'+$field,[Data.OleDb.OleDbType]::Integer);$p.Value=[int]$row.$field}
   $p=$cmd.Parameters.Add('@DienTich',[Data.OleDb.OleDbType]::Double);$p.Value=[double]$row.DienTich
   foreach($field in 'TenChu','DiaChi','DiaChiThuaDatChiTiet','Xudong','LRD','MaLD') {
    $p=$cmd.Parameters.Add('@'+$field,[Data.OleDb.OleDbType]::VarWChar,255);$p.Value=[string]$row.$field
   }
   $bytes=[Convert]::FromBase64String($row.Geometry)
   $p=$cmd.Parameters.Add('@Geometry',[Data.OleDb.OleDbType]::LongVarBinary,$bytes.Length);$p.Value=$bytes
   [void]$cmd.ExecuteNonQuery();$cmd.Dispose()
  }
  $transaction.Commit();$transaction=$null
  $cmd=$connection.CreateCommand();$cmd.CommandText='SELECT COUNT(*) FROM ThuaDat'
  if([int]$cmd.ExecuteScalar() -ne $rows.Count){throw 'MDB row count mismatch.'};$cmd.Dispose()
 } catch {
  if($transaction){$transaction.Rollback()}
  if($connection){$connection.Dispose();$connection=$null}
  if(Test-Path -LiteralPath $OutputPath){Remove-Item -LiteralPath $OutputPath}
  throw
 } finally {
  if($connection){$connection.Dispose()}
  if($catalog){[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($catalog)}
 }
 Write-Output ('MDB_CREATED: '+$rows.Count);exit 0
}
$script:Stage='connect-microstation'
$app=[Runtime.InteropServices.Marshal]::GetActiveObject('MicroStationDGN.Application')
InitializeSonMapInterop
if($Action -eq 'SaveActive') {
 $script:Stage='save-active-source'
 if([IO.Path]::GetFullPath($app.ActiveDesignFile.FullName) -ne [IO.Path]::GetFullPath($SourcePath)){throw 'Open the selected source DGN first.'}
 if(-not $SkipSaveBackup){Copy-Item -LiteralPath $SourcePath -Destination $OutputPath}
 $app.ActiveDesignFile.Save()
 Write-Output 'ACTIVE_SOURCE_SAVED';exit 0
}
if($Action -eq 'RestoreActive') {
 $script:Stage='restore-active-source'
 if([IO.Path]::GetFullPath($app.ActiveDesignFile.FullName) -ne [IO.Path]::GetFullPath($OutputPath)){throw 'Active DGN changed; restore cancelled. Use the saved backup manually.'}
 $temporary=$app.OpenDesignFile($InputPath,$true,3)
 Copy-Item -LiteralPath $InputPath -Destination $OutputPath -Force
 $restored=$app.OpenDesignFile($OutputPath,$false,3)
 Write-Output 'ACTIVE_SOURCE_RESTORED';exit 0
}
if($Action -eq 'Extract') {
 if($SourcePath) {
  if([IO.Path]::GetFullPath($app.ActiveDesignFile.FullName) -ne [IO.Path]::GetFullPath($SourcePath)){throw 'Open the selected source DGN in MicroStation first.'}
  $ModelName=[string]$app.ActiveModelReference.Name
  $DefaultModel=TestSonMapDefaultModel $app.ActiveDesignFile $app.ActiveModelReference
 }
 if(-not $ModelName -and -not $DefaultModel){throw 'Missing model name.'}
 # Read the on-disk snapshot through a program-only DesignFile, not the active editable file.
 $script:Stage='open-dgn-snapshot'
 $liveExtract=$SourcePath -and ([IO.Path]::GetFullPath($InputPath) -eq [IO.Path]::GetFullPath($SourcePath))
 $design=if($liveExtract){$app.ActiveDesignFile}else{$app.OpenDesignFileForProgram($InputPath,$true)}
 try {
  $script:Stage='select-model: '+$ModelName
  $model=ResolveSonMapModel $design $ModelName ([bool]$DefaultModel)
  if($model.Is3D){throw 'Only 2D cadastral models are supported.'}
  if($BoundaryLevels) {
   $wanted=[int[]]@($BoundaryLevels.Split(',') | ForEach-Object {[int]$_.Trim()})
   $textWanted=if($TextLevels -eq '*'){$null}elseif($TextLevels -eq 'none'){[int[]]@()}else{[int[]]@($TextLevels.Split(',') | ForEach-Object {[int]$_.Trim()})}
   if($TextLevels -eq 'none'){$textWanted=[int[]]@()}
   $json=[SonMapV8iRecords]::ExtractJson($app,$model,$wanted,[bool]$BreakArcs,[bool]$KeepComplex,$ChordTolerance,[bool]$DefaultModel,$textWanted)
   [IO.File]::WriteAllText($OutputPath,$json,(New-Object Text.UTF8Encoding($false)))
   Write-Output 'EXTRACTED_FAST';exit 0
  }
  $elements=New-Object 'System.Collections.Generic.List[object]'
  $texts=New-Object 'System.Collections.Generic.List[object]'
  function CollectElement($element,$depth,$forcedLevel,$insideCell) {
   if($depth -gt 32){throw 'Complex element nesting exceeds 32.'}
   $script:Stage='read-element type='+$element.Type
   $level=if($forcedLevel -gt 0){$forcedLevel}else{[int]$element.Level.Number}
   $id=[SonMapV8iRecords]::Id($element)
   if([int]$element.Type -eq 17) {
    $text=$element.AsTextElement
    $texts.Add(@{level=$level;id=$id;text=[string]$text.Text;point=([SonMapV8iRecords]::TextOrigin($element))})
    return
   }
   if([int]$element.Type -eq 7) {
    $children=$element.AsTextNodeElement.GetSubElements()
    while($children.MoveNext()){CollectElement $children.Current ($depth+1) $forcedLevel $insideCell}
    return
   }
   if([int]$element.Type -in @(12,14) -and $KeepComplex) {
    $elements.Add(@{kind='unsupported-complex-kept';level=$level;id=$id;reason='Enable breaking complex boundaries to process this element.'});return
   }
   if([int]$element.Type -in @(2,12,14)) {
    if([int]$element.Type -eq 2){$elements.Add(@{kind='unsupported-cell-on-boundary-level';level=$level;id=$id;reason='Drop boundary cells on a copy before topology.'})}
    $children=$element.AsComplexElement.GetSubElements()
    $childLevel=if([int]$element.Type -eq 2){0}else{$level}
    while($children.MoveNext()){CollectElement $children.Current ($depth+1) $childLevel ($insideCell -or [int]$element.Type -eq 2)}
    return
   }
   if($insideCell) {
    $elements.Add(@{kind='unsupported-boundary-in-cell';level=$level;id=$id;reason='Drop boundary cells manually on a copy before topology.'})
    return
   }
   try {
    $vertices=$null;$approximate=$false
    if([int]$element.Type -in @(3,4,6)) {
     $vertices=[SonMapV8iRecords]::Vertices($element,$false,$ChordTolerance)
    } elseif(([int]$element.Type -in @(15,16)) -and $BreakArcs) {
     if($ChordTolerance -le 0){throw 'Chord tolerance must be positive.'}
     $vertices=[SonMapV8iRecords]::Vertices($element,$true,$ChordTolerance);$approximate=$true
    }
    if($null -eq $vertices -or $vertices.Count -lt 2){throw 'Unsupported boundary element.'}
    $points=New-Object 'System.Collections.Generic.List[object]'
    foreach($vertex in $vertices){$points.Add($vertex)}
    if([int]$element.Type -eq 6){$points.Add($vertices[0])}
    $elements.Add(@{kind='line';level=$level;id=$id;points=@($points.ToArray());approximate=$approximate;color=[int]$element.Color;weight=[int]$element.LineWeight;line_style=[string]$element.LineStyle.Name})
   } catch {
    $elements.Add(@{kind=('unsupported-type-'+$element.Type);level=$level;id=$id;reason=$_.Exception.Message})
   }
  }
  $scanContext=NewSonMapScan $app $model
  while(MoveSonMapScan $scanContext){
   $element=ReadSonMapScanCurrent $scanContext
   CollectElement $element 0 0 $false
  }
  $script:Stage='write-snapshot-json'
  WriteJson $OutputPath @{version=1;model=$ModelName;model_is_default=[bool]$DefaultModel;unit=[string]$model.MasterUnit.Label;references_excluded=[int]$model.Attachments.Count;elements=@($elements.ToArray());texts=@($texts.ToArray())}
 } finally {if(-not $liveExtract){$design.Close()}}
 Write-Output 'EXTRACTED';exit 0
}
# Only a freshly copied workspace DGN may be edited. The Python coordinator supplies it.
$project=Get-Content -LiteralPath $InputPath -Raw -Encoding UTF8 | ConvertFrom-Json
if(-not $project.working_dgn){throw 'Missing working-copy path.'}
$direct=$Action -in @('ApplyDrawing','ApplyClean','ApplyPreview')
if(-not $direct -and [IO.Path]::GetFullPath($OutputPath) -eq [IO.Path]::GetFullPath($project.source.path)){throw 'Refusing to overwrite source in copy mode.'}
$mutationStarted=$false
if($direct) {
 if([string]$app.ActiveModelReference.Name -ne [string]$project.model){throw 'Active model changed; analyse the drawing again.'}
 if([IO.Path]::GetFullPath($OutputPath) -ne [IO.Path]::GetFullPath($project.source.path) -or [IO.Path]::GetFullPath($app.ActiveDesignFile.FullName) -ne [IO.Path]::GetFullPath($OutputPath)){throw 'Direct write requires the original DGN to remain active.'}
 if(-not $project.direct_backup -or -not (Test-Path -LiteralPath $project.direct_backup)){throw 'A verified DGN backup is required before direct write.'}
 if((FileDigest $project.direct_backup) -ne $project.source.sha256 -or (FileDigest $OutputPath) -ne $project.source.sha256){throw 'Source or backup changed before direct write.'}
} else {Copy-Item -LiteralPath $project.working_dgn -Destination $OutputPath -ErrorAction Stop}
$design=$null
try {
 if($direct){$design=$app.ActiveDesignFile}else{$design=$app.OpenDesignFileForProgram($OutputPath,$false)}
 # V8i cannot AddElement to a program-only V7 design. Reject before removing ranh.
 if(-not $direct -and [int]$design.Format -eq 1){
  throw 'V7 DGN output requires the active design file. Use the backed-up update-current mode; program-only V7 output is not supported.'
 }
 $script:Stage='select-output-model: '+$project.model
 $model=ResolveSonMapModel $design $project.model ([bool]$project.model_is_default)
 if($model.Is3D){throw 'Only 2D cadastral models are supported.'}
 if($Action -eq 'ApplyPreview') {
  $scanContext=NewSonMapScan $app $model 'marker-scan'
  $oldMarkers=New-Object 'System.Collections.Generic.List[object]'
  while(MoveSonMapScan $scanContext){$element=ReadSonMapScanCurrent $scanContext;if([int]$element.Type -eq 2 -and [string]$element.AsCellElement.Name -eq 'SMERR'){$oldMarkers.Add($element)}}
  $mutationStarted=$true
  foreach($element in $oldMarkers){$model.RemoveElement($element)}
 }
 if($Action -in @('WriteDrawing','CleanDrawing','TopologyDrawing','ApplyDrawing','ApplyClean')) {
 $boundary=@(([string]$project.options.boundary_levels).Split(',') | ForEach-Object {[int]$_.Trim()})
 $centreLevel=[int]$project.options.centre_level
 if($boundary -contains $centreLevel){throw 'Centre and boundary levels must differ.'}
 $rewriteBoundary=-not ($project.PSObject.Properties.Name -contains 'boundary_changed' -and $project.boundary_changed -eq $false)
 $scanContext=if($rewriteBoundary){NewSonMapScan $app $model 'output-scan'}else{NewSonMapScan $app $model 'centre-scan' ([int[]]@(2))}
 $remove=New-Object 'System.Collections.Generic.List[object]'
 $templates=@{}
 while(MoveSonMapScan $scanContext) {
  $element=ReadSonMapScanCurrent $scanContext
  if($rewriteBoundary -and $boundary -contains [int]$element.Level.Number){$templates[[SonMapV8iRecords]::Id($element)]=$element}
  $generated=$false
  if([int]$element.Type -eq 2){
   $name=[string]$element.AsCellElement.Name
   $generated=($name -eq 'SMERR' -or ($name -eq 'SMPARC' -and $Action -notin @('CleanDrawing','ApplyClean')))
  }
  if($project.scope_rings) {
   if($generated -and [SonMapV8iRecords]::CellInScope($element,[double[][][]]$project.scope_rings)){$remove.Add($element)}
  } elseif(($rewriteBoundary -and $boundary -contains [int]$element.Level.Number) -or $generated){$remove.Add($element)}
 }
 # Construct replacement elements while original templates are still valid.
 $pending=New-Object 'System.Collections.Generic.List[object]'
 if($rewriteBoundary -and -not $project.scope_rings -and $project.noded_lines) {
  foreach($line in $project.noded_lines) {
   $template=$templates[[string]$line.source_id]
   if($template){$element=[SonMapV8iRecords]::StyledLine($app,[double[][]]$line.points,$template)}
   else {
    $element=[SonMapV8iRecords]::Line($app,[double[][]]$line.points)
    $element.Color=[int]$line.color;$element.LineWeight=[int]$line.weight
    $element.LineStyle=$design.LineStyles.Item([string]$line.line_style)
   }
   $element.Level=(FindLevel $design ([int]$line.level));$pending.Add($element)
  }
 }
 # Retain text and unsupported elements: export validation has already rejected unsupported boundaries.
 $mutationStarted=$true
 $script:Stage='replace-boundary-elements'
 foreach($element in $remove){if([int]$element.Type -notin @(7,17)){$model.RemoveElement($element)}}
 $script:Stage='create-boundary-lines'
 if($rewriteBoundary -and -not $project.scope_rings) {
 if($project.noded_lines) {
 foreach($element in $pending){$model.AddElement($element)}
 } else {
 foreach($line in $project.cleaned_lines) {
  if($project.options.join_lines) {
   $element=[SonMapV8iRecords]::Line($app,[double[][]]$line)
   $element.Level=(FindLevel $design $boundary[0]);$model.AddElement($element)
   continue
  }
  for($i=1;$i -lt $line.Count;$i++) {
   $element=[SonMapV8iRecords]::Line($app,[double[][]]@($line[$i-1],$line[$i]))
   $element.Level=(FindLevel $design $boundary[0]);$model.AddElement($element)
  }
 }
 }
 }
 if($Action -notin @('CleanDrawing','ApplyClean')) {
 $script:Stage='create-parcel-centres'
 foreach($parcel in $project.parcels) {
  $label=if($null -ne $parcel.TCT){[string]$parcel.TCT}else{'ID:'+ $parcel.ID}
  # A named cell keeps the parcel number and representative point together.
  $cell=[SonMapV8iRecords]::TextCell($app,$label,[double]$parcel.centre[0],[double]$parcel.centre[1],(FindLevel $design $centreLevel),[int]$project.options.centre_color,[double]$project.options.centre_height)
  $cell.Level=(FindLevel $design $centreLevel);$model.AddElement($cell)
 }
 }
 }
 # Error markers live only on the generated copy, on a level separate from boundaries and labels.
 $script:Stage='create-error-markers'
 foreach($issue in $project.issues) {
  if($issue.resolved_by_manual_edit){continue}
  if($issue.code -in @('DUPLICATE_REMOVED','ZERO_LENGTH_REMOVED','SNAPPED_ENDPOINT','INTERSECTION_NODE')){continue}
  $point=$null
  if($issue.point){$point=$issue.point}
  elseif($issue.points){$point=$issue.points[0]}
  elseif($issue.parcel){$parcel=@($project.parcels | Where-Object {$_.ID -eq $issue.parcel} | Select-Object -First 1);if($parcel.Count){$point=$parcel[0].centre}}
  if(-not $point){continue}
  $radius=[double]$project.options.error_radius / [double]$project.options.metres_per_unit
  $marker=[SonMapV8iRecords]::ErrorCell($app,[double]$point[0],[double]$point[1],$radius,(FindLevel $design ([int]$project.options.error_level)),[int]$project.options.error_color)
  $marker.Level=(FindLevel $design ([int]$project.options.error_level));$marker.Color=[int]$project.options.error_color;$model.AddElement($marker)
 }
 $script:Stage='save-output-dgn'
 if($direct){foreach($view in $design.Views){if($view.IsOpen){$view.ShowLevel((FindLevel $design ([int]$project.options.error_level)));$view.Redraw()}}}
 $design.Save()
} catch {
 $failure=$_
 if($direct) {
  if($mutationStarted) {
   try {
    $temporary=$app.OpenDesignFile($project.direct_backup,$true,3)
    Copy-Item -LiteralPath $project.direct_backup -Destination $OutputPath -Force
    $restored=$app.OpenDesignFile($OutputPath,$false,3)
   } catch {throw ('Direct write failed; automatic DGN restore also failed. Backup: '+$project.direct_backup+'. Original error: '+$failure.Exception.Message+'. Restore error: '+$_.Exception.Message)}
  }
 } else {
  # Preserve the original COM failure even when V8i still holds the output open.
  try {if($design){$design.Close();$design=$null}} catch {}
  try {if(Test-Path -LiteralPath $OutputPath){Remove-Item -LiteralPath $OutputPath}} catch {}
 }
 throw $failure
} finally {if($design -and -not $direct){$design.Close()}}
Write-Output 'DRAWING_CREATED'
