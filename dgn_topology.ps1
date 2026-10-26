param(
 [Parameter(Mandatory=$true)][ValidateSet('Extract','WriteDrawing','WritePreview','WriteMdb','CleanDrawing','TopologyDrawing')][string]$Action,
 [Parameter(Mandatory=$true)][string]$InputPath,
 [Parameter(Mandatory=$true)][string]$OutputPath,
 [string]$ModelName,
 [string]$SourcePath,
 [double]$ChordTolerance=0.001,
 [switch]$BreakArcs,
 [switch]$AllowEmpty,
 [switch]$KeepComplex,
 [switch]$DefaultModel
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
function FindLevel($design,[int]$number) {
 foreach($level in $design.Levels){if([int]$level.Number -eq $number){return $level}}
 $level=$design.Levels.Add('SonMap_Level_'+$number)
 $level.Number=$number
 $design.Levels.Rewrite()
 return $level
}

function WriteJson($path,$value) {
 [IO.File]::WriteAllText($path,(ConvertTo-Json -InputObject $value -Depth 30),(New-Object Text.UTF8Encoding($false)))
}
function XY($p) { return ,@([double]$p.X,[double]$p.Y) }
if(Test-Path -LiteralPath $OutputPath){throw 'Output already exists; refusing to overwrite.'}
if($Action -eq 'WriteMdb') {
 $rows=@(Get-Content -LiteralPath $InputPath -Raw -Encoding UTF8 | ConvertFrom-Json)
 if($rows.Count -eq 0 -and -not $AllowEmpty){throw 'No parcels.'}
 $catalog=$null;$connection=$null;$transaction=$null
 try {
  $script:Stage='create-mdb'
  $catalog=New-Object -ComObject ADOX.Catalog
  $catalog.Create('Provider=Microsoft.Jet.OLEDB.4.0;Data Source='+$OutputPath+';Jet OLEDB:Engine Type=5;')
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
if($Action -eq 'Extract') {
 if($SourcePath) {
  if([IO.Path]::GetFullPath($app.ActiveDesignFile.FullName) -ne [IO.Path]::GetFullPath($SourcePath)){throw 'Open the selected source DGN in MicroStation first.'}
  $ModelName=[string]$app.ActiveModelReference.Name
  $DefaultModel=TestSonMapDefaultModel $app.ActiveDesignFile $app.ActiveModelReference
 }
 if(-not $ModelName -and -not $DefaultModel){throw 'Missing model name.'}
 # Read the on-disk snapshot through a program-only DesignFile, not the active editable file.
 $script:Stage='open-dgn-snapshot'
 $design=$app.OpenDesignFileForProgram($InputPath,$true)
 try {
  $script:Stage='select-model: '+$ModelName
  $model=ResolveSonMapModel $design $ModelName ([bool]$DefaultModel)
  if($model.Is3D){throw 'Only 2D cadastral models are supported.'}
  $elements=New-Object 'System.Collections.Generic.List[object]'
  $texts=New-Object 'System.Collections.Generic.List[object]'
  function CollectElement($element,$depth,$forcedLevel,$insideCell) {
   if($depth -gt 32){throw 'Complex element nesting exceeds 32.'}
   $script:Stage='read-element type='+$element.Type
   $level=if($forcedLevel -gt 0){$forcedLevel}else{[int]$element.Level.Number}
   $id=[string]$element.ID.Low
   if([int]$element.Type -eq 17) {
    $text=$element.AsTextElement
    $texts.Add(@{level=$level;id=$id;text=[string]$text.Text;point=(XY $text.Origin)})
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
     $vertices=@($element.AsVertexList.GetVertices())
    } elseif(([int]$element.Type -in @(15,16)) -and $BreakArcs) {
     if($ChordTolerance -le 0){throw 'Chord tolerance must be positive.'}
     if([int]$element.Type -eq 15){$vertices=@($element.AsEllipseElement.ConstructVertexList($ChordTolerance))}else{$vertices=@($element.AsArcElement.ConstructVertexList($ChordTolerance))};$approximate=$true
    }
    if($null -eq $vertices -or $vertices.Count -lt 2){throw 'Unsupported boundary element.'}
    $points=New-Object 'System.Collections.Generic.List[object]'
    foreach($vertex in $vertices){$points.Add((XY $vertex))}
    if([int]$element.Type -eq 6){$points.Add((XY $vertices[0]))}
    $elements.Add(@{kind='line';level=$level;id=$id;points=@($points.ToArray());approximate=$approximate})
   } catch {
    $elements.Add(@{kind=('unsupported-type-'+$element.Type);level=$level;id=$id;reason=$_.Exception.Message})
   }
  }
  $script:Stage='scan-model'
  $scan=$model.Scan()
  while($scan.MoveNext()){CollectElement $scan.Current 0 0 $false}
  $script:Stage='write-snapshot-json'
  WriteJson $OutputPath @{version=1;model=$ModelName;model_is_default=[bool]$DefaultModel;unit=[string]$model.MasterUnit.Label;references_excluded=[int]$model.Attachments.Count;elements=@($elements.ToArray());texts=@($texts.ToArray())}
 } finally {$design.Close()}
 Write-Output 'EXTRACTED';exit 0
}
# Only a freshly copied workspace DGN may be edited. The Python coordinator supplies it.
$project=Get-Content -LiteralPath $InputPath -Raw -Encoding UTF8 | ConvertFrom-Json
if(-not $project.working_dgn){throw 'Missing working-copy path.'}
if([IO.Path]::GetFullPath($project.working_dgn) -eq [IO.Path]::GetFullPath($project.source.path)){throw 'Refusing to edit source.'}
Copy-Item -LiteralPath $project.working_dgn -Destination $OutputPath -ErrorAction Stop
$design=$null
try {
 $design=$app.OpenDesignFileForProgram($OutputPath,$false)
 $script:Stage='select-output-model: '+$project.model
 $model=ResolveSonMapModel $design $project.model ([bool]$project.model_is_default)
 if($model.Is3D){throw 'Only 2D cadastral models are supported.'}
 if($Action -in @('WriteDrawing','CleanDrawing','TopologyDrawing')) {
 $boundary=@(([string]$project.options.boundary_levels).Split(',') | ForEach-Object {[int]$_.Trim()})
 $centreLevel=[int]$project.options.centre_level
 if($boundary -contains $centreLevel){throw 'Centre and boundary levels must differ.'}
 $scan=$model.Scan();$remove=New-Object 'System.Collections.Generic.List[object]'
 while($scan.MoveNext()) {
  $element=$scan.Current
  if($boundary -contains [int]$element.Level.Number){$remove.Add($element)}
 }
 # Retain text and unsupported elements: export validation has already rejected unsupported boundaries.
 foreach($element in $remove){if([int]$element.Type -notin @(7,17)){$model.RemoveElement($element)}}
 foreach($line in $project.cleaned_lines) {
  if($project.options.join_lines) {
   $vertices=New-Object 'System.Collections.Generic.List[object]'
   foreach($coordinate in $line){$vertices.Add($app.Point3dFromXYZ([double]$coordinate[0],[double]$coordinate[1],0))}
   $element=$app.CreateLineElement1($null,$vertices.ToArray())
   $element.Level=(FindLevel $design $boundary[0]);$model.AddElement($element)
   continue
  }
  for($i=1;$i -lt $line.Count;$i++) {
   $p=$app.Point3dFromXYZ([double]$line[$i-1][0],[double]$line[$i-1][1],0)
   $q=$app.Point3dFromXYZ([double]$line[$i][0],[double]$line[$i][1],0)
   $element=$app.CreateLineElement2($null,$p,$q)
   $element.Level=(FindLevel $design $boundary[0]);$model.AddElement($element)
  }
 }
 if($Action -ne 'CleanDrawing') {
 foreach($parcel in $project.parcels) {
  $origin=$app.Point3dFromXYZ([double]$parcel.centre[0],[double]$parcel.centre[1],0)
  $label=if($null -ne $parcel.TCT){[string]$parcel.TCT}else{'ID:'+ $parcel.ID}
  $text=$app.CreateTextElement1($null,$label,$origin,$app.Matrix3dIdentity())
  $text.Level=(FindLevel $design $centreLevel);$text.Color=[int]$project.options.centre_color
  $text.TextStyle.Height=[double]$project.options.centre_height
  $text.TextStyle.Width=[double]$project.options.centre_height
  # A named cell keeps the parcel number and representative point together.
  $cell=$app.CreateCellElement1('SMPARC',@($text),$origin,$false)
  $cell.Level=(FindLevel $design $centreLevel);$model.AddElement($cell)
 }
 }
 }
 # Error markers live only on the generated copy, on a level separate from boundaries and labels.
 foreach($issue in $project.issues) {
  if($issue.resolved_by_manual_edit){continue}
  if($issue.code -in @('DUPLICATE_REMOVED','ZERO_LENGTH_REMOVED','SNAPPED_ENDPOINT')){continue}
  $point=$null
  if($issue.point){$point=$issue.point}
  elseif($issue.points){$point=$issue.points[0]}
  elseif($issue.parcel){$point=$project.parcels[[int]$issue.parcel-1].centre}
  if(-not $point){continue}
  $origin=$app.Point3dFromXYZ([double]$point[0],[double]$point[1],0)
  $radius=[double]$project.options.error_radius / [double]$project.options.metres_per_unit
  $circle=$app.CreateEllipseElement2($null,$origin,$radius,$radius,$app.Matrix3dIdentity())
  $circle.Level=(FindLevel $design ([int]$project.options.error_level));$circle.Color=[int]$project.options.error_color
  $marker=$app.CreateCellElement1('SMERR',@($circle),$origin,$false)
  $marker.Level=$circle.Level;$marker.Color=$circle.Color;$model.AddElement($marker)
 }
 $design.Save()
} catch {
 if($design){$design.Close();$design=$null}
 if(Test-Path -LiteralPath $OutputPath){Remove-Item -LiteralPath $OutputPath}
 throw
} finally {if($design){$design.Close()}}
Write-Output 'DRAWING_CREATED'
