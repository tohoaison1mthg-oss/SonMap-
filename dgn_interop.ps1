# Point3d/Matrix3d/ID are COM records. Late-bound PowerShell cannot marshal them.
# Use the interop assembly belonging to the installed V8i; never ship Bentley DLLs.
function InitializeSonMapInterop {
 if ('SonMapV8iRecords' -as [type]) { return }
 $path=Join-Path ${env:ProgramFiles(x86)} 'Bentley\MicroStation V8i (SELECTseries)\MicroStation\assemblies\bentley.interop.microstationdgn.dll'
 if(-not (Test-Path -LiteralPath $path)){throw 'Installed V8i interop assembly not found: '+$path}
 Add-Type -Path $path
 Add-Type -ReferencedAssemblies $path -TypeDefinition @'
using System;
using B = Bentley.Interop.MicroStationDGN;
public static class SonMapV8iRecords {
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
 public static object ErrorCell(object app,double x,double y,double radius,object level,int color) {
  B.Application a=(B.Application)app;
  B.Point3d p=new B.Point3d();p.X=x;p.Y=y;
  B.Matrix3d rotation=a.Matrix3dIdentity();
  B.EllipseElement circle=a.CreateEllipseElement2(null,ref p,radius,radius,ref rotation);
  circle.Level=(B.Level)level;circle.Color=color;
  B.Element[] children=new B.Element[]{circle};
  return a.CreateCellElement1("SMERR",ref children,ref p,false);
 }
}
'@
}
