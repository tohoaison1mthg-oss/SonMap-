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
 private static B.TransientElementContainer focusMarker;
 private static string focusSource,focusModel;
 public static void CheckFocusContext(object value) {
  if(focusMarker==null)return;
  var a=(B.Application)value;
  if(a.ActiveDesignFile.FullName!=focusSource || a.ActiveModelReference.Name!=focusModel){focusMarker.Reset();focusMarker=null;}
 }
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
  return json.Serialize(Row("version",1,"model",m.Name,"model_is_default",defaultModel,"unit",m.get_MasterUnit().Label,"uors_per_master_unit",m.UORsPerMasterUnit,"references_excluded",m.Attachments.Count,"elements",lines,"texts",texts));
 }
 public static void Focus(object value,double x,double y,double span) {
  B.Application a=(B.Application)value;
  span=Math.Max(span,100/a.ActiveModelReference.UORsPerMasterUnit);
  if(focusMarker!=null){focusMarker.Reset();focusMarker=null;}
  focusSource=a.ActiveDesignFile.FullName;focusModel=a.ActiveModelReference.Name;
  int openViews=0;
  foreach(B.View view in a.ActiveDesignFile.Views) {
   if(!view.IsOpen)continue;
   openViews++;
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
  if(openViews==0)throw new InvalidOperationException("Open a MicroStation view before locating an error.");
  // Detached temporary drawing: fixed proportion of the view, no DGN element added.
  double r=span*.045;
  {
   B.Point3d centre=new B.Point3d();centre.X=x;centre.Y=y;
   B.Matrix3d rotation=a.Matrix3dIdentity();
   var e=(B.Element)a.CreateEllipseElement2(null,ref centre,r,r,ref rotation);e.Color=3;e.LineWeight=2;
   foreach(B.LineStyle style in a.ActiveDesignFile.LineStyles)if(style.Name=="0"){e.LineStyle=style;break;}
   foreach(B.View view in a.ActiveDesignFile.Views) {
    if(!view.IsOpen)continue;
    foreach(B.Level level in a.ActiveDesignFile.Levels)if(view.IsLevelShown(level)){e.Level=level;break;}
    if(focusMarker==null)focusMarker=a.CreateTransientElementContainer1(e,B.MsdTransientFlags.Overlay|B.MsdTransientFlags.DontIncludeInFit,(B.MsdViewMask)255,B.MsdDrawingMode.Temporary);
    else focusMarker.AppendCopyOfElement(e);
    break;
   }
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
  B.Application app=(B.Application)application;
  var json=new System.Web.Script.Serialization.JavaScriptSerializer();json.MaxJsonLength=int.MaxValue;
  var parcels=(object[])json.DeserializeObject(parcelsJson);
  var m=(B.ModelReference)model;
  var criteria=(B.ElementScanCriteria)app.CreateObjectInMicroStation("MicroStationDGN.ElementScanCriteria");
  criteria.ExcludeAllTypes();criteria.IncludeType(B.MsdElementType.CellHeader);
  var scan=m.Scan(criteria);var existing=new List<B.CellElement>();var origins=new List<double[]>();B.Element template=null;
  int targetLevel=((B.Level)level).Number;
  while(scan.MoveNext()){
   var cell=scan.Current.AsCellElement();
   if(cell.Name!="CENTRD")continue;
   var children=cell.GetSubElements();bool matchingLevel=false;
   while(children.MoveNext()){var childLevel=children.Current.Level;if(childLevel!=null && childLevel.Number==targetLevel){matchingLevel=true;break;}}
   if(!matchingLevel)continue;
   existing.Add(cell);var origin=cell.Origin;origins.Add(new double[]{origin.X,origin.Y});if(template==null)template=cell.Clone();
  }
  var matches=CentreMatches(parcelsJson,origins.ToArray());int parcelIndex=0;
  var removed=new HashSet<int>();
  foreach(object value in parcels) {
   var row=(Dictionary<string,object>)value;
   var point=(object[])row["centre"];
   B.CellElement kept=null;
   foreach(int index in matches[parcelIndex++]){
    if(removed.Contains(index))continue;
    var old=existing[index];
    if(kept==null)kept=old;else {m.RemoveElement(old);removed.Add(index);}
   }
   if(kept!=null)continue;
   B.Point3d centre=new B.Point3d();centre.X=Convert.ToDouble(point[0]);centre.Y=Convert.ToDouble(point[1]);
   B.CellElement created;
   if(template!=null){
    created=template.Clone().AsCellElement();created.RemoveAllDatabaseLinks();
    var origin=created.Origin;created.ScaleUniform(ref origin,height);
    B.Point3d delta=new B.Point3d();delta.X=centre.X-origin.X;delta.Y=centre.Y-origin.Y;created.Move(ref delta);
   }else{
    // A standalone cadastral centre, never an internal ID disguised as a parcel number.
    double size=height*.3;var children=new List<B.Element>();
    var rotation=app.Matrix3dIdentity();
    children.Add(app.CreateEllipseElement2(null,ref centre,size*.2,size*.2,ref rotation));
    double[][] offsets=new double[][]{new double[]{-size,0,size,0},new double[]{0,-size,0,size},new double[]{0,size*.5,size*.5,0},new double[]{size*.5,0,0,-size*.5},new double[]{0,-size*.5,-size*.5,0},new double[]{-size*.5,0,0,size*.5}};
    foreach(var offset in offsets){B.Point3d a=centre,b=centre;a.X+=offset[0];a.Y+=offset[1];b.X+=offset[2];b.Y+=offset[3];children.Add(app.CreateLineElement2(null,ref a,ref b));}
    foreach(var child in children){child.Level=(B.Level)level;child.Color=color;}
    var parts=children.ToArray();created=app.CreateCellElement1("CENTRD",ref parts,ref centre,false);
   }
   m.AddElement(created);
  }
 }
 public static int[][] CentreMatches(string parcelsJson,double[][] origins){
  var json=new System.Web.Script.Serialization.JavaScriptSerializer();json.MaxJsonLength=int.MaxValue;
  var parcels=(object[])json.DeserializeObject(parcelsJson);var result=new int[parcels.Length][];
  for(int parcel=0;parcel<parcels.Length;parcel++){
   var row=(Dictionary<string,object>)parcels[parcel];var ring=(object[])row["points"];
   double minX=Double.PositiveInfinity,minY=minX,maxX=Double.NegativeInfinity,maxY=maxX;
   foreach(object value in ring){var point=(object[])value;double x=Convert.ToDouble(point[0]),y=Convert.ToDouble(point[1]);minX=Math.Min(minX,x);minY=Math.Min(minY,y);maxX=Math.Max(maxX,x);maxY=Math.Max(maxY,y);}
   var matches=new List<int>();
   for(int i=0;i<origins.Length;i++){
    double x=origins[i][0],y=origins[i][1];
    if(x<minX || x>maxX || y<minY || y>maxY)continue;
    if(InParcel(row,x,y))matches.Add(i);
   }
   result[parcel]=matches.ToArray();
  }return result;
 }
 private static bool InRing(object value,double x,double y){
  var ring=(object[])value;bool inside=false;
  for(int i=0,j=ring.Length-1;i<ring.Length;j=i++){
   var p=(object[])ring[i];var q=(object[])ring[j];double px=Convert.ToDouble(p[0]),py=Convert.ToDouble(p[1]),qx=Convert.ToDouble(q[0]),qy=Convert.ToDouble(q[1]);
   if((py>y)!=(qy>y) && x<(qx-px)*(y-py)/(qy-py)+px)inside=!inside;
  }return inside;
 }
 private static bool InParcel(Dictionary<string,object> row,double x,double y){
  if(!InRing(row["points"],x,y))return false;
  if(row.ContainsKey("holes"))foreach(object hole in (object[])row["holes"])if(InRing(hole,x,y))return false;
  return true;
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
