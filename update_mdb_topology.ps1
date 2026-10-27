# Apply a parcel delta to an existing MDB COPY; all other tables/columns are retained.
param([Parameter(Mandatory=$true)][string]$PlanPath,[Parameter(Mandatory=$true)][string]$MdbPath)
$ErrorActionPreference='Stop'
$plan=Get-Content -LiteralPath $PlanPath -Raw -Encoding UTF8 | ConvertFrom-Json
$builder=New-Object Data.OleDb.OleDbConnectionStringBuilder
$builder.Provider='Microsoft.Jet.OLEDB.4.0';$builder['Data Source']=$MdbPath
$connection=New-Object Data.OleDb.OleDbConnection($builder.ConnectionString)
$transaction=$null
function AddParameters($command,$row,[bool]$insert) {
 if($insert){$p=$command.Parameters.Add('@ID',[Data.OleDb.OleDbType]::Integer);$p.Value=[int]$row.ID}
 foreach($field in @('ToBD','TCT')) {
  $p=$command.Parameters.Add('@'+$field,[Data.OleDb.OleDbType]::Integer)
  if($null -eq $row.$field){$p.Value=[DBNull]::Value}else{$p.Value=[int]$row.$field}
 }
 $p=$command.Parameters.Add('@Area',[Data.OleDb.OleDbType]::Double);$p.Value=[double]$row.DienTich
 foreach($field in @('TenChu','DiaChi','DiaChiThuaDatChiTiet','Xudong','LRD','MaLD')) {
  $p=$command.Parameters.Add('@'+$field,[Data.OleDb.OleDbType]::VarWChar,255);$p.Value=[string]$row.$field
 }
 $bytes=[Convert]::FromBase64String($row.Geometry)
 $p=$command.Parameters.Add('@Geometry',[Data.OleDb.OleDbType]::LongVarBinary,$bytes.Length);$p.Value=$bytes
 if(-not $insert){$p=$command.Parameters.Add('@ID',[Data.OleDb.OleDbType]::Integer);$p.Value=[int]$row.ID}
}
function UpdateRow($row) {
 $cmd=$connection.CreateCommand();$cmd.Transaction=$transaction
 try {
  $cmd.CommandText='UPDATE ThuaDat SET ToBD=?,TCT=?,DienTich=?,TenChu=?,DiaChi=?,DiaChiThuaDatChiTiet=?,Xudong=?,LRD=?,MaLD=?,Geometry=? WHERE ID=?'
  AddParameters $cmd $row $false
  if($cmd.ExecuteNonQuery() -ne 1){throw 'Could not update exactly one parcel.'}
 } finally {$cmd.Dispose()}
}
function QuoteColumn([string]$name) {return '['+$name.Replace(']',']]')+']'}
try {
 $connection.Open();$transaction=$connection.BeginTransaction()
 foreach($row in $plan.insert_rows) {
  $cmd=$connection.CreateCommand();$cmd.Transaction=$transaction
  if($null -ne $row._parent_id) {
   # Clone all writable parent columns, including attributes unknown to SonMap.
   # Parent rows must remain available until every child has been copied.
   $cmd.CommandText='SELECT * FROM ThuaDat WHERE 1=0'
   $reader=$cmd.ExecuteReader([Data.CommandBehavior]::SchemaOnly)
   $schema=$reader.GetSchemaTable();$reader.Close();$cmd.Dispose()
   $columns=@($schema.Rows | Where-Object {$_.ColumnName -ne 'ID' -and $_.IsAutoIncrement -ne $true -and $_.IsReadOnly -ne $true} | ForEach-Object {QuoteColumn $_.ColumnName})
   $cmd=$connection.CreateCommand();$cmd.Transaction=$transaction
   $cmd.CommandText='INSERT INTO ThuaDat ([ID],'+($columns -join ',')+') SELECT ?,'+($columns -join ',')+' FROM ThuaDat WHERE [ID]=?'
   $p=$cmd.Parameters.Add('@ID',[Data.OleDb.OleDbType]::Integer);$p.Value=[int]$row.ID
   $p=$cmd.Parameters.Add('@Parent',[Data.OleDb.OleDbType]::Integer);$p.Value=[int]$row._parent_id
   if($cmd.ExecuteNonQuery() -ne 1){throw 'Could not copy exactly one parent parcel.'};$cmd.Dispose()
   UpdateRow $row
  } else {
   $cmd.CommandText='INSERT INTO ThuaDat (ID,ToBD,TCT,DienTich,TenChu,DiaChi,DiaChiThuaDatChiTiet,Xudong,LRD,MaLD,Geometry) VALUES (?,?,?,?,?,?,?,?,?,?,?)'
   AddParameters $cmd $row $true
   if($cmd.ExecuteNonQuery() -ne 1){throw 'Could not insert exactly one parcel.'};$cmd.Dispose()
  }
 }
 foreach($row in $plan.update_rows){UpdateRow $row}
 foreach($id in $plan.delete_ids) {
  $cmd=$connection.CreateCommand();$cmd.Transaction=$transaction
  $cmd.CommandText='DELETE FROM ThuaDat WHERE ID=?'
  $p=$cmd.Parameters.Add('@ID',[Data.OleDb.OleDbType]::Integer);$p.Value=[int]$id
  if($cmd.ExecuteNonQuery() -ne 1){throw 'The source parcel no longer exists.'};$cmd.Dispose()
 }
 $transaction.Commit();$transaction=$null
 Write-Output 'MDB_COPY_UPDATED: other tables/columns preserved.'
} catch {if($transaction){$transaction.Rollback()};throw} finally {$connection.Dispose()}
