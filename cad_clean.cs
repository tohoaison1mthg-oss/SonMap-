using System;
using System.IO;
using System.Collections.Generic;
using System.Security.Cryptography;
using B = Bentley.Interop.MicroStationDGN;

internal static class SonMapClean {
    internal static string Stage="initialize";
    internal sealed class RestoreFailed : Exception {
        public RestoreFailed(string message) : base(message) {}
    }
    private static Dictionary<string,object> Map(object value) {return (Dictionary<string,object>)value;}
    private static object[] Rows(object value) {return value as object[] ?? new object[0];}
    private static bool Flag(Dictionary<string,object> row,string key) {return row.ContainsKey(key) && Convert.ToBoolean(row[key]);}
    private static double[][] Points(object value) {
        object[] rows=Rows(value);double[][] result=new double[rows.Length][];
        for(int i=0;i<rows.Length;i++) {
            object[] p=Rows(rows[i]);if(p.Length!=2)throw new InvalidOperationException("Invalid boundary coordinate.");
            result[i]=new double[]{Convert.ToDouble(p[0]),Convert.ToDouble(p[1])};
            foreach(double n in result[i])if(Double.IsNaN(n)||Double.IsInfinity(n))throw new InvalidOperationException("Non-finite boundary coordinate.");
        }
        return result;
    }
    private static string Digest(string path) {
        using(var stream=File.Open(path,FileMode.Open,FileAccess.Read,FileShare.ReadWrite))
        using(var hash=SHA256.Create())return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-","").ToLowerInvariant();
    }
    public static object Run(B.Application app,Dictionary<string,object> project) {
        Stage="validate-snapshot";
        var source=Map(project["source"]);string path=Convert.ToString(source["path"]);
        string backup=Convert.ToString(project["direct_backup"]),expected=Convert.ToString(source["sha256"]);
        if(String.Equals(Path.GetFullPath(path),Path.GetFullPath(backup),StringComparison.OrdinalIgnoreCase))throw new InvalidOperationException("Invalid recovery file.");
        if(Digest(path)!=expected || Digest(backup)!=expected)throw new InvalidOperationException("Source or recovery file changed before clean.");
        var model=app.ActiveModelReference;var design=app.ActiveDesignFile;var options=Map(project["options"]);
        if(Rows(project.ContainsKey("scope_rings")?project["scope_rings"]:null).Length>0)throw new InvalidOperationException("Scoped clean requires the checked legacy path.");
        var boundary=new HashSet<int>();
        foreach(string token in Convert.ToString(options["boundary_levels"]).Split(','))boundary.Add(Int32.Parse(token.Trim()));
        int errorLevel=Convert.ToInt32(options["error_level"]);
        if(boundary.Contains(errorLevel))throw new InvalidOperationException("Error and boundary levels must differ.");
        double radius=Convert.ToDouble(options["error_radius"])/Convert.ToDouble(options["metres_per_unit"]);
        if(radius<=0 || Double.IsNaN(radius)||Double.IsInfinity(radius))throw new InvalidOperationException("Invalid error radius.");
        foreach(object value in Rows(project["issues"]))if(Convert.ToString(Map(value)["code"])=="UNSUPPORTED")throw new InvalidOperationException("Unsupported boundary; clean cancelled.");
        bool rewrite=!project.ContainsKey("boundary_changed") || Flag(project,"boundary_changed");
        int[] levels=new int[boundary.Count];boundary.CopyTo(levels);
        var remove=new List<object>();var templates=new Dictionary<string,B.Element>();
        Stage="collect-boundaries";
        foreach(object value in SonMapInProcessRecords.OutputElements(app,model,levels,rewrite)) {
            var e=(B.Element)value;
            if(rewrite && e.Level!=null && boundary.Contains(e.Level.Number)){templates[e.ID.ToString()]=e;remove.Add(e);}
            else if((int)e.Type==2 && e.AsCellElement().Name=="SMERR")remove.Add(e);
        }
        var levelCache=new Dictionary<int,B.Level>();
        foreach(B.Level level in design.Levels)levelCache[level.Number]=level;
        Func<int,B.Level> findLevel=delegate(int number) {
            if(number<1 || number>63)throw new InvalidOperationException("Invalid output level.");
            B.Level found;
            if(!levelCache.TryGetValue(number,out found)) {found=design.AddNewLevel("SonMap_Level_"+number);found.Number=number;design.Levels.Rewrite();levelCache[number]=found;}
            return found;
        };
        var pending=new List<object>();var expectedLines=new List<double[][]>();
        Stage="construct-replacements";
        if(rewrite) {
            object[] lines=Rows(project["noded_lines"]);
            if(lines.Length==0)throw new InvalidOperationException("Missing noded boundaries; analyse again.");
            foreach(object value in lines) {
                var row=Map(value);double[][] points=Points(row["points"]);
                if(points.Length<2)throw new InvalidOperationException("Empty replacement boundary.");
                B.Element template;B.Element e;
                if(templates.TryGetValue(Convert.ToString(row["source_id"]),out template))e=(B.Element)SonMapInProcessRecords.StyledLine(app,points,template);
                else {
                    e=(B.Element)SonMapInProcessRecords.Line(app,points);e.Color=Convert.ToInt32(row["color"]);e.LineWeight=Convert.ToInt32(row["weight"]);
                    string style=Convert.ToString(row["line_style"]);bool found=false;
                    foreach(B.LineStyle candidate in design.LineStyles)if(candidate.Name==style){e.LineStyle=candidate;found=true;break;}
                    if(!found)throw new InvalidOperationException("Missing source line style.");
                }
                int level=Convert.ToInt32(row["level"]);if(!boundary.Contains(level))throw new InvalidOperationException("Replacement outside boundary levels.");
                e.Level=findLevel(level);pending.Add(e);expectedLines.Add(points);
            }
        }
        var markers=new List<object>();
        Stage="construct-error-markers";
        foreach(object value in Rows(project["issues"])) {
            var issue=Map(value);string code=Convert.ToString(issue["code"]);
            if(Flag(issue,"resolved_by_manual_edit") || code=="DUPLICATE_REMOVED" || code=="ZERO_LENGTH_REMOVED" || code=="SNAPPED_ENDPOINT" || code=="INTERSECTION_NODE")continue;
            object[] point=Rows(issue.ContainsKey("point")?issue["point"]:null);
            if(point.Length==0 && issue.ContainsKey("points")){object[] rows=Rows(issue["points"]);if(rows.Length>0)point=Rows(rows[0]);}
            if(point.Length==0 && issue.ContainsKey("parcel"))foreach(object parcelValue in Rows(project["parcels"])) {
                var parcel=Map(parcelValue);if(Convert.ToInt32(parcel["ID"])==Convert.ToInt32(issue["parcel"])){point=Rows(parcel["centre"]);break;}
            }
            if(point.Length!=2)continue;
            var marker=(B.Element)SonMapInProcessRecords.ErrorCell(app,Convert.ToDouble(point[0]),Convert.ToDouble(point[1]),radius,findLevel(errorLevel),Convert.ToInt32(options["error_color"]));
            marker.Level=findLevel(errorLevel);markers.Add(marker);
        }
        bool mutated=false;
        try {
            // Recheck after constructing detached replacements, before removing anything.
            if(Digest(path)!=expected || Digest(backup)!=expected)throw new InvalidOperationException("Source changed while preparing clean.");
            mutated=true;
            Stage="replace-boundaries";
            SonMapInProcessRecords.RemoveElements(model,remove.ToArray());
            SonMapInProcessRecords.AddElements(model,pending.ToArray());
            SonMapInProcessRecords.AddElements(model,markers.ToArray());
            Stage="save-dgn";design.Save();
            Stage="verify-written-coordinates";
            double tolerance=Math.Max(1e-8,1.1/model.UORsPerMasterUnit);
            for(int i=0;i<pending.Count;i++) {
                var e=(B.Element)pending[i];double[][] actual=SonMapInProcessRecords.Vertices(e,false,.001),wanted=expectedLines[i];
                if(actual.Length!=wanted.Length)throw new InvalidOperationException("Written boundary vertex count mismatch.");
                for(int j=0;j<actual.Length;j++)if(Math.Abs(actual[j][0]-wanted[j][0])>tolerance || Math.Abs(actual[j][1]-wanted[j][1])>tolerance)throw new InvalidOperationException("Written boundary coordinate mismatch.");
            }
            Stage="redraw";
            foreach(B.View view in design.Views)if(view.IsOpen){view.ShowLevel(findLevel(errorLevel));view.Redraw();}
            return new {boundaries=pending.Count,markers=markers.Count};
        } catch(Exception error) {
            if(mutated) {
                try {app.OpenDesignFile(backup,true,B.MsdV7Action.Workmode);File.Copy(backup,path,true);app.OpenDesignFile(path,false,B.MsdV7Action.Workmode);}
                catch(Exception restore) {throw new RestoreFailed(error.Message+" Recovery failed: "+restore.Message+" Recovery file: "+backup);}
            }
            throw;
        }
    }
}

internal static class SonMapView {
    private static object[] Rows(object value) {return value as object[] ?? new object[0];}
    private static void Apply(B.Application app,object[] saved) {
        var views=new Dictionary<int,B.View>();var levels=new Dictionary<int,B.Level>();
        foreach(B.View view in app.ActiveDesignFile.Views)views[view.Index]=view;
        foreach(B.Level level in app.ActiveDesignFile.Levels)levels[level.Number]=level;
        foreach(object value in saved) {
            var row=(Dictionary<string,object>)value;B.View view;B.Level level;
            if(views.TryGetValue(Convert.ToInt32(row["view"]),out view) && levels.TryGetValue(Convert.ToInt32(row["level"]),out level)) {
                if(Convert.ToBoolean(row["shown"]))view.ShowLevel(level);else view.HideLevel(level);
            }
        }
        foreach(B.View view in views.Values)if(view.IsOpen)view.Redraw();
    }
    public static string Run(B.Application app,Dictionary<string,object> request,bool restore) {
        var json=new System.Web.Script.Serialization.JavaScriptSerializer();json.MaxJsonLength=int.MaxValue;
        string state=Convert.ToString(request["state"]);var design=app.ActiveDesignFile;
        Dictionary<string,object> prior=null;
        if(File.Exists(state)) {
            prior=(Dictionary<string,object>)json.DeserializeObject(File.ReadAllText(state));
            if(!String.Equals(Path.GetFullPath(Convert.ToString(prior["source"])),Path.GetFullPath(design.FullName),StringComparison.OrdinalIgnoreCase) || Convert.ToString(prior["model"])!=app.ActiveModelReference.Name)
                throw new InvalidOperationException("Restore the same DGN/model view before hiding another model.");
        }
        if(restore) {
            if(prior==null)throw new InvalidOperationException("Missing saved level display state.");
            Apply(app,Rows(prior["levels"]));return "LEVEL_DISPLAY_RESTORED";
        }
        var saved=new List<object>();var selected=new HashSet<int>();
        foreach(object number in Rows(request["levels"]))selected.Add(Convert.ToInt32(number));
        foreach(B.View view in design.Views)if(view.IsOpen)foreach(B.Level level in design.Levels)
            saved.Add(new Dictionary<string,object>{{"view",view.Index},{"level",level.Number},{"shown",view.IsLevelShown(level)}});
        if(prior==null) {
            string temporary=state+".tmp";
            File.WriteAllText(temporary,json.Serialize(new {source=design.FullName,model=app.ActiveModelReference.Name,levels=saved}));
            File.Move(temporary,state);
        }
        try {
            foreach(B.View view in design.Views)if(view.IsOpen) {
                foreach(B.Level level in design.Levels)if(selected.Contains(level.Number))view.ShowLevel(level);else view.HideLevel(level);
                view.Redraw();
            }
        } catch {Apply(app,saved.ToArray());throw;}
        return "LEVELS_HIDDEN_ONLY";
    }
}
