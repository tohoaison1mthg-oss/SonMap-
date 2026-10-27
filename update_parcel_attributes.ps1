param([Parameter(Mandatory=$true)][string]$MdbPath,[Parameter(Mandatory=$true)][string]$PlanPath)
$ErrorActionPreference='Stop'
$plan=Get-Content -LiteralPath $PlanPath -Raw -Encoding UTF8 | ConvertFrom-Json
if((Get-FileHash -LiteralPath $MdbPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $plan.sha256){throw 'MDB changed before update.'}
$builder=New-Object Data.OleDb.OleDbConnectionStringBuilder
$builder.Provider='Microsoft.Jet.OLEDB.4.0';$builder['Data Source']=$MdbPath
$connection=New-Object Data.OleDb.OleDbConnection($builder.ConnectionString)
$transaction=$null
try {
 $connection.Open()
 $command=$connection.CreateCommand();$command.CommandText='SELECT * FROM ThuaDat WHERE 1=0'
 $reader=$command.ExecuteReader();$schema=$reader.GetSchemaTable();$reader.Close();$command.Dispose()
 $columns=@{};foreach($column in $schema.Rows){$columns[[string]$column.ColumnName]=$column}
 $types=@{'System.String'=[Data.OleDb.OleDbType]::VarWChar;'System.Int16'=[Data.OleDb.OleDbType]::SmallInt;'System.Int32'=[Data.OleDb.OleDbType]::Integer;'System.Int64'=[Data.OleDb.OleDbType]::BigInt;'System.Byte'=[Data.OleDb.OleDbType]::UnsignedTinyInt;'System.Double'=[Data.OleDb.OleDbType]::Double;'System.Single'=[Data.OleDb.OleDbType]::Single;'System.Decimal'=[Data.OleDb.OleDbType]::Decimal;'System.Boolean'=[Data.OleDb.OleDbType]::Boolean}
 $fields=@($plan.changes.PSObject.Properties)
 if(-not $fields.Count){throw 'No fields selected.'}
 $transaction=$connection.BeginTransaction();$command=$connection.CreateCommand();$command.Transaction=$transaction
 $assignments=@()
 foreach($field in $fields) {
  $name=$field.Name
  if($name -in @('ID','Geometry','DienTich') -or -not $columns.ContainsKey($name)){throw 'Read-only or unknown column.'}
  $column=$columns[$name];$kind=[string]$column.DataType.FullName
  if(-not $types.ContainsKey($kind)){throw 'Unsupported column type.'}
  $assignments+=('['+$name.Replace(']',']]')+']=?')
  $parameter=$command.Parameters.Add('@p'+$command.Parameters.Count,$types[$kind])
  if($null -eq $field.Value) {
   if(-not $column.AllowDBNull){throw 'Column cannot be empty.'};$parameter.Value=[DBNull]::Value
  } elseif($kind -eq 'System.String') {
   $text=[string]$field.Value
   if($text.Length -gt [int]$column.ColumnSize -or $text.Contains([string][char]0)){throw 'Text is too long or contains NUL.'}
   $parameter.Size=[Math]::Max(1,$text.Length);$parameter.Value=$text
  } else {$parameter.Value=[Convert]::ChangeType($field.Value,$column.DataType,[Globalization.CultureInfo]::InvariantCulture)}
 }
 $command.CommandText='UPDATE ThuaDat SET '+($assignments -join ',')+' WHERE ID=?'
 $parameter=$command.Parameters.Add('@ID',[Data.OleDb.OleDbType]::Integer);$parameter.Value=[int]$plan.ID
 if($command.ExecuteNonQuery() -ne 1){throw 'Update must affect exactly one parcel.'}
 $command.Dispose();$transaction.Commit();$transaction=$null
 Write-Output 'ATTRIBUTES_UPDATED_ON_STAGED_COPY'
} catch {if($transaction){$transaction.Rollback()};throw}
finally {$connection.Dispose()}
