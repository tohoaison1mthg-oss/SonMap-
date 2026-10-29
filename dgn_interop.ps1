# Point3d/Matrix3d/ID are COM records. Late-bound PowerShell cannot marshal them.
# Use the interop assembly belonging to the installed V8i; never ship Bentley DLLs.
function InitializeSonMapInterop {
 if ('SonMapV8iRecords' -as [type]) { return }
 $path=Join-Path ${env:ProgramFiles(x86)} 'Bentley\MicroStation V8i (SELECTseries)\MicroStation\assemblies\bentley.interop.microstationdgn.dll'
 if(-not (Test-Path -LiteralPath $path)){throw 'Installed V8i interop assembly not found: '+$path}
 Add-Type -Path $path
 Add-Type -AssemblyName System.Web.Extensions
 Add-Type -ReferencedAssemblies @($path,[System.Web.Script.Serialization.JavaScriptSerializer].Assembly.Location) -TypeDefinition @'
using System;
using System.Collections.Generic;
using B = Bentley.Interop.MicroStationDGN;
public static class SonMapV8iRecords {
 private static Dictionary<string,object> Row(params object[] pairs) {
  var row=new Dictionary<string,object>();
  for(int i=0;i<pairs.Length;i+=2)row[(string)pairs[i]]=pairs[i+1];
  return row;
 }
 private static void Collect(B.Element e,int depth,int forced,bool inside,int[] wanted,bool arcs,bool keep,double tolerance,List<object> lines,List<object> texts) {
  if(depth>32)throw new InvalidOperationException("Complex element nesting exceeds 32.");
  if(e==null)throw new InvalidOperationException("Scan returned an empty element.");
  if(!e.IsGraphical)return;
  int type=(int)e.Type;
  var ownLevel=e.Level;
  int level=forced>0?forced:(ownLevel==null?0:ownLevel.Number);
  bool selected=Array.IndexOf(wanted,level)>=0;
  // Traverse containers even when their own level is not a boundary level.
  if(type==7 || type==2 || type==12 || type==14) {
   if(selected && (type==12 || type==14) && keep) {
    lines.Add(Row("kind","unsupported-complex-kept","level",level,"id",e.ID.ToString()));return;
   }
   if(type==2 && selected)lines.Add(Row("kind","unsupported-cell-on-boundary-level","level",level,"id",e.ID.ToString()));
   B.ElementEnumerator children=type==7?e.AsTextNodeElement().GetSubElements():e.AsComplexElement().GetSubElements();
   int childLevel=type==7?forced:((type==12 || type==14)?level:0);
   while(children.MoveNext())Collect(children.Current,depth+1,childLevel,inside || type==2,wanted,arcs,keep,tolerance,lines,texts);
   return;
  }
  if(type==17) {
   var t=e.AsTextElement();var p=t.get_Origin();
   texts.Add(Row("level",level,"id",e.ID.ToString(),"text",t.Text,"point",new double[]{p.X,p.Y}));return;
  }
  if(!selected)return;
  string id=e.ID.ToString();
  if(inside) {lines.Add(Row("kind","unsupported-boundary-in-cell","level",level,"id",id));return;}
  try {
   double[][] xy=Vertices(e,arcs,tolerance);
   if(xy.Length<2)throw new InvalidOperationException("Too few vertices.");
   if(type==6) {var closed=new double[xy.Length+1][];Array.Copy(xy,closed,xy.Length);closed[xy.Length]=xy[0];xy=closed;}
   lines.Add(Row("kind","line","level",level,"id",id,"points",xy,"approximate",type==15 || type==16,"color",e.Color,"weight",e.LineWeight,"line_style",e.LineStyle.Name));
  } catch(Exception error) {lines.Add(Row("kind","unsupported-type-"+type,"level",level,"id",id,"reason",error.Message));}
 }
 public static string ExtractJson(object application,object value,int[] wanted,bool arcs,bool keep,double tolerance,bool defaultModel,int[] textLevels) {
  var a=(B.Application)application;var m=(B.ModelReference)value;
  var lines=new List<object>();var texts=new List<object>();
  var criteria=(B.ElementScanCriteria)a.CreateObjectInMicroStation("MicroStationDGN.ElementScanCriteria");
  if(textLevels!=null) {
   criteria.ExcludeAllLevels();
   foreach(B.Level level in m.Levels)if(Array.IndexOf(wanted,level.Number)>=0 || Array.IndexOf(textLevels,level.Number)>=0)criteria.IncludeLevel(level);
  }
  var scan=m.Scan(criteria);
  while(scan.MoveNext())Collect(scan.Current,0,0,false,wanted,arcs,keep,tolerance,lines,texts);
  var json=new System.Web.Script.Serialization.JavaScriptSerializer();json.MaxJsonLength=int.MaxValue;
  return json.Serialize(Row("version",1,"model",m.Name,"model_is_default",defaultModel,"unit",m.get_MasterUnit().Label,"references_excluded",m.Attachments.Count,"elements",lines,"texts",texts));
 }
 public static void Focus(object value,double x,double y,double span) {
  B.Application a=(B.Application)value;
  foreach(B.View view in a.ActiveDesignFile.Views) {
   if(!view.IsOpen)continue;
   B.Point3d p=new B.Point3d();p.X=x;p.Y=y;
   B.Point3d ext=view.get_Extents();
   double smallest=Math.Min(Math.Abs(ext.X),Math.Abs(ext.Y));
   if(smallest<=0)throw new InvalidOperationException("Invalid view extents.");
   ext.X=Math.Abs(ext.X)*span/smallest;ext.Y=Math.Abs(ext.Y)*span/smallest;
   view.set_Extents(ref ext);view.set_Center(ref p);view.Redraw();
   B.Point3d check=view.get_Center();
   if(Math.Abs(check.X-x)>0.00001 || Math.Abs(check.Y-y)>0.00001)
    throw new InvalidOperationException("View did not centre on the requested location.");
  }
 }
 public static object[] OutputElements(object application,object value,int[] boundary,bool rewrite) {
  var a=(B.Application)application;var m=(B.ModelReference)value;
  var result=new List<object>();var seen=new HashSet<string>();
  if(rewrite) {
   var criteria=(B.ElementScanCriteria)a.CreateObjectInMicroStation("MicroStationDGN.ElementScanCriteria");
   criteria.ExcludeAllLevels();
   foreach(B.Level level in m.Levels)if(Array.IndexOf(boundary,level.Number)>=0)criteria.IncludeLevel(level);
   var scan=m.Scan(criteria);
   while(scan.MoveNext()) {var e=scan.Current;if(seen.Add(e.ID.ToString()))result.Add(e);}
  }
  var cells=(B.ElementScanCriteria)a.CreateObjectInMicroStation("MicroStationDGN.ElementScanCriteria");
  cells.ExcludeAllTypes();cells.IncludeType(B.MsdElementType.CellHeader);
  var markers=m.Scan(cells);
  while(markers.MoveNext()) {
   var e=markers.Current;string name=e.AsCellElement().Name;
   if((name=="SMERR" || name=="SMPARC") && seen.Add(e.ID.ToString()))result.Add(e);
  }
  return result.ToArray();
 }
 public static double[] PickPoint(object value) {
  B.Application a=(B.Application)value;
  a.CommandState.StartDefaultCommand();
  a.ShowPrompt("SonMap: Click inside a parcel; right-click to cancel.");
  B.CadInputMessage m=a.CadInputQueue.GetInput(B.MsdCadInputType.DataPoint,B.MsdCadInputType.Reset,B.MsdCadInputType.Keyin,B.MsdCadInputType.Command);
  if(m.InputType!=B.MsdCadInputType.DataPoint)return null;
  B.Point3d p=m.Point;
  return new double[]{p.X,p.Y};
 }
 public static bool CellInScope(object value,double[][][] rings) {
  B.Point3d p=((B.Element)value).AsCellElement().Origin;
  foreach(double[][] ring in rings) {
   bool inside=false;
   for(int i=0,j=ring.Length-1;i<ring.Length;j=i++) {
    double xi=ring[i][0],yi=ring[i][1],xj=ring[j][0],yj=ring[j][1];
    if((yi>p.Y)!=(yj>p.Y) && p.X<(xj-xi)*(p.Y-yi)/(yj-yi)+xi) inside=!inside;
   }
   if(inside)return true;
  }
  return false;
 }
 public static string Id(object value) {
  return ((B.Element)value).ID.ToString();
 }
 public static double[][] Vertices(object value, bool arcs, double tolerance) {
  B.Element e=(B.Element)value;
  B.Point3d[] points;
  int type=(int)e.Type;
  if(type==3 || type==4 || type==6) points=e.AsVertexList().GetVertices();
  else if(arcs && type==15) points=e.AsEllipseElement().ConstructVertexList(tolerance);
  else if(arcs && type==16) points=e.AsArcElement().ConstructVertexList(tolerance);
  else throw new InvalidOperationException("Unsupported boundary element.");
  double[][] result=new double[points.Length][];
  for(int i=0;i<points.Length;i++) result[i]=new double[]{points[i].X,points[i].Y};
  return result;
 }
 public static double[] TextOrigin(object value) {
  B.Point3d p=((B.Element)value).AsTextElement().get_Origin();
  return new double[]{p.X,p.Y};
 }
 public static object Line(object app, double[][] xy) {
  B.Point3d[] p=new B.Point3d[xy.Length];
  for(int i=0;i<p.Length;i++) {p[i].X=xy[i][0];p[i].Y=xy[i][1];}
  return ((B.Application)app).CreateLineElement1(null,ref p);
 }
 public static object StyledLine(object app,double[][] xy,object template) {
  B.Point3d[] p=new B.Point3d[xy.Length];
  for(int i=0;i<p.Length;i++){p[i].X=xy[i][0];p[i].Y=xy[i][1];}
  return ((B.Application)app).CreateLineElement1((B.Element)template,ref p);
 }
 public static object TextCell(object app,string label,double x,double y,object level,int color,double height) {
  B.Application a=(B.Application)app;
  B.Point3d p=new B.Point3d();p.X=x;p.Y=y;
  B.Matrix3d rotation=a.Matrix3dIdentity();
  B.TextElement text=a.CreateTextElement1(null,label,ref p,ref rotation);
  text.Level=(B.Level)level;text.Color=color;
  text.TextStyle.Height=height;text.TextStyle.Width=height;
  B.Element[] children=new B.Element[]{text};
  return a.CreateCellElement1("SMPARC",ref children,ref p,false);
 }
 public static void RemoveElements(object model,object[] elements) {
  var m=(B.ModelReference)model;
  foreach(object value in elements) {
   var e=(B.Element)value;int type=(int)e.Type;
   if(type!=7 && type!=17)m.RemoveElement(e);
  }
 }
 public static void AddElements(object model,object[] elements) {
  var m=(B.ModelReference)model;
  foreach(object value in elements)m.AddElement((B.Element)value);
 }
 public static void AddCentres(object application,object model,string parcelsJson,object level,int color,double height) {
  var json=new System.Web.Script.Serialization.JavaScriptSerializer();json.MaxJsonLength=int.MaxValue;
  var parcels=(object[])json.DeserializeObject(parcelsJson);
  var m=(B.ModelReference)model;
  foreach(object value in parcels) {
   var row=(Dictionary<string,object>)value;
   var point=(object[])row["centre"];
   string label=row["TCT"]==null?"ID:"+Convert.ToString(row["ID"],System.Globalization.CultureInfo.InvariantCulture):Convert.ToString(row["TCT"],System.Globalization.CultureInfo.InvariantCulture);
   var cell=(B.CellElement)TextCell(application,label,Convert.ToDouble(point[0]),Convert.ToDouble(point[1]),level,color,height);
   cell.Level=(B.Level)level;m.AddElement(cell);
  }
 }
 public static object ErrorCell(object app,double x,double y,double radius,object level,int color) {
  B.Application a=(B.Application)app;
  B.Point3d p=new B.Point3d();p.X=x;p.Y=y;
  B.Matrix3d rotation=a.Matrix3dIdentity();
  B.EllipseElement circle=a.CreateEllipseElement2(null,ref p,radius,radius,ref rotation);
  circle.Level=(B.Level)level;circle.Color=color;
  B.Element[] children=new B.Element[]{circle};
  return a.CreateCellElement1("SMERR",ref children,ref p,false);
 }
 public static bool MarkerAt(object value,double x,double y) {
  var e=(B.Element)value;
  if((int)e.Type!=2 || e.AsCellElement().Name!="SMERR")return false;
  var p=e.AsCellElement().Origin;
  return Math.Abs(p.X-x)<=1e-7 && Math.Abs(p.Y-y)<=1e-7;
 }
}
'@
}
