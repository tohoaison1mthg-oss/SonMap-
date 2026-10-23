Private parcelRow As Variant
Private tableOffset As Double
Private allRows As Collection
Private labelParts As Collection
Private diagramRight As Double
Private diagramBottom As Double
Private frameExtraX As Double
Private frameExtraY As Double

Public Sub XuatThuaDangChon_V2()
    XuatThuaDaChon
End Sub

Public Sub XuatThuaDangChon_V3()
    XuatThuaDaChon
End Sub

Public Sub XuatThuaDangChon_V4()
    XuatThuaDaChon
End Sub

Public Sub XuatThuaDaChon()
    On Error GoTo Failed
    Dim scan As ElementEnumerator, selected As Element, count As Long
    Dim r As Range3d, point As Point3d, item As Variant, hits As Long, p() As Point3d
    Dim label As String, exactHits As Long, exactRow As Variant, isLabel As Boolean
    parcelRow = Empty
    If LCase$(ActiveDesignFile.FullName) <> LCase$(@SOURCE@) Then Err.Raise 5, , "Open the configured original DGN before selecting a parcel."
    Set scan = ActiveModelReference.GetSelectedElements
    Do While scan.MoveNext
        count = count + 1
        Set selected = scan.Current
    Loop
    If count <> 1 Then Err.Raise 5, , "Select exactly ONE parcel label or closed parcel outline."
    If Not selected.IsGraphical Then Err.Raise 5, , "Select a graphical parcel element."
    isLabel = selected.IsTextElement Or selected.IsTextNodeElement Or selected.IsCellElement
    If Not isLabel Then
        If Not selected.IsShapeElement And Not selected.IsComplexShapeElement Then Err.Raise 5, , "Select a TEXT label or closed SHAPE; an individual edge is ambiguous."
    End If
    LoadRows
    r = selected.Range
    If selected.IsTextElement Then
        point = selected.AsTextElement.Origin
        label = Trim$(selected.AsTextElement.Text)
    Else
        point = Point3dFromXYZ((r.Low.X + r.High.X) / 2, (r.Low.Y + r.High.Y) / 2, 0)
    End If
    For Each item In allRows
        ParsePoints CStr(item(6)), p
        If isLabel Then
            If InsidePolygon(point, p) Then
                hits = hits + 1: parcelRow = item
                If label = CStr(item(1)) Then exactHits = exactHits + 1: exactRow = item
            End If
        ElseIf BoundsMatch(r, p) Then
            hits = hits + 1: parcelRow = item
        End If
    Next item
    If selected.IsTextElement Then
        If Len(label) > 0 And IsNumeric(label) Then
            If exactHits <> 1 Then Err.Raise 5, , "Selected numeric label " & label & " does not uniquely match its MDB parcel. No file was exported."
        End If
    End If
    If exactHits = 1 Then parcelRow = exactRow: hits = 1
    If hits <> 1 Then Err.Raise 5, , "No unique MDB match. Select the parcel NUMBER label inside its boundary, or use XuatTuDanhSach."
    ExportParcel
    Exit Sub
Failed:
    MsgBox "Selection: " & Err.Description, vbExclamation
End Sub

Public Sub InGCN()
    XuatTuDanhSach True
End Sub

Public Sub XuatMau03()
    XuatTuDanhSach False, True
End Sub

Public Sub XuatTuDanhSach(Optional ByVal gcn As Boolean = False, Optional ByVal mau03 As Boolean = False)
    On Error GoTo Failed
    Dim fs As Object, stream As Object, key As String, item As Variant, hits As Long
    parcelRow = Empty
    Set fs = CreateObject("Scripting.FileSystemObject")
    If Not fs.FileExists(@REQUEST@) Then Err.Raise 5, , "Select a parcel in ThanhTanApp first."
    Set stream = fs.OpenTextFile(@REQUEST@, 1, False, -1)
    key = Trim$(stream.ReadAll): stream.Close
    LoadRows
    For Each item In allRows
        If CStr(item(0)) & "/" & CStr(item(1)) & "/" & CStr(item(9)) = key Then parcelRow = item: hits = hits + 1
    Next item
    If hits <> 1 Then Err.Raise 5, , "Parcel key is missing or duplicated in prepared data."
    If mau03 Then ExportMau03Parcel Else ExportParcel gcn
    Exit Sub
Failed:
    Dim listFailure As String
    listFailure = "List export: " & Err.Description
    PublishResult "ERROR", listFailure
    MsgBox listFailure, vbExclamation
End Sub

Private Sub LoadRows()
    Dim fs As Object, stream As Object, line As String, fields As Variant
    Set allRows = New Collection
    Set fs = CreateObject("Scripting.FileSystemObject")
    If Format$(FileDateTime(@MDB@), "yyyymmddhhnnss") <> @MDBDATE@ Then Err.Raise 5, , "MDB changed. Refresh data and regenerate the macro in ThanhTanApp."
    If Format$(FileDateTime(@SOURCE@), "yyyymmddhhnnss") <> @DGNDATE@ Then Err.Raise 5, , "Source DGN changed. Refresh data and regenerate the macro in ThanhTanApp."
    Set stream = fs.OpenTextFile(@DATA@, 1, False, -1)
    Do Until stream.AtEndOfStream
        line = stream.ReadLine
        If Len(line) > 0 Then
            fields = Split(line, vbTab)
            If UBound(fields) < 9 Then stream.Close: Err.Raise 5, , "Invalid prepared data row. Refresh MDB in app."
            allRows.Add fields
        End If
    Loop
    stream.Close
End Sub

Private Sub ParsePoints(ByVal value As String, ByRef p() As Point3d)
    Dim vertices As Variant, xy As Variant, i As Long
    vertices = Split(value, ";")
    If UBound(vertices) < 2 Then Err.Raise 5, , "Parcel needs at least 3 vertices."
    ReDim p(0 To UBound(vertices))
    For i = 0 To UBound(vertices)
        xy = Split(vertices(i), "|")
        If UBound(xy) <> 1 Then Err.Raise 5, , "Invalid vertex data."
        p(i) = Point3dFromXYZ(Val(xy(0)), Val(xy(1)), 0)
    Next i
End Sub

Private Function InsidePolygon(ByRef point As Point3d, ByRef p() As Point3d) As Boolean
    Dim i As Long, j As Long, crossing As Double
    j = UBound(p)
    For i = 0 To UBound(p)
        If (p(i).Y > point.Y) <> (p(j).Y > point.Y) Then
            crossing = p(i).X + (point.Y - p(i).Y) * (p(j).X - p(i).X) / (p(j).Y - p(i).Y)
            If point.X < crossing Then InsidePolygon = Not InsidePolygon
        End If
        j = i
    Next i
End Function

Private Function BoundsMatch(ByRef r As Range3d, ByRef p() As Point3d) As Boolean
    Dim xmin As Double, xmax As Double, ymin As Double, ymax As Double, i As Long
    xmin = p(0).X: xmax = xmin: ymin = p(0).Y: ymax = ymin
    For i = 1 To UBound(p)
        If p(i).X < xmin Then xmin = p(i).X
        If p(i).X > xmax Then xmax = p(i).X
        If p(i).Y < ymin Then ymin = p(i).Y
        If p(i).Y > ymax Then ymax = p(i).Y
    Next i
    BoundsMatch = Abs(r.Low.X - xmin) < 0.1 And Abs(r.High.X - xmax) < 0.1 And Abs(r.Low.Y - ymin) < 0.1 And Abs(r.High.Y - ymax) < 0.1
End Function

Private Sub ExportParcel(Optional ByVal gcn As Boolean = False)
    On Error GoTo Failed
    Dim fs As Object, target As String, d As DesignFile, original() As Point3d, display() As Point3d
    Dim lengths() As Double, n As Long, i As Long, j As Long, shape As ShapeElement
    Dim xmin As Double, xmax As Double, ymin As Double, ymax As Double, factor As Double
    Dim page As Long, first As Long, segmentCount As Long, pages As Long
    tableOffset = 0
    Set labelParts = Nothing
    ParsePoints CStr(parcelRow(6)), original
    CalculateDiagramFrame original
    n = UBound(original) + 1
    parcelLandCode = CStr(parcelRow(5)): parcelAddress = CStr(parcelRow(4))
    Set fs = CreateObject("Scripting.FileSystemObject")
    target = @OUTPUT@ & "\To" & CStr(parcelRow(0)) & "_Thua" & CStr(parcelRow(1)) & "_ID" & CStr(parcelRow(9)) & "_" & Format$(Now, "yyyymmdd_hhnnss") & ".dgn"
    If gcn Then target = @OUTPUT@ & "\GCN_To" & CStr(parcelRow(0)) & "_Thua" & CStr(parcelRow(1)) & "_ID" & CStr(parcelRow(9)) & "_" & Format$(Now, "yyyymmdd_hhnnss") & ".dgn"
    If fs.FileExists(target) Then Err.Raise 5, , "Output already exists. Retry after one second."
    detailStage = "Copy template to new file"
    fs.CopyFile @TEMPLATE@, target, False
    Set d = OpenDesignFile(fs.GetFile(target).ShortPath, False)
    If LCase$(fs.GetFile(ActiveDesignFile.FullName).ShortPath) <> LCase$(fs.GetFile(target).ShortPath) Then Err.Raise 5, , "New output did not become active."
    WhiteOnDarkBackground
    FindSolidStyle
    If gcn Then
        FindUnicodeTemplate
        Set unicodeTemplate = unicodeTemplate.Clone.AsTextElement
        ClearGCNTemplate
    Else
    ClearExtraPages
    ClearEmptyDiagramText
    FindUnicodeTemplate
    FillHeader
    ClearUnusedAddressText
    ClearTablePanel
    WidenDiagramFrame
    AlignHeaderText
    AlignDiagramTemplate
    ScaleTemplateText
    ResizeTemplatePage
    PutText U("0054 00F4 0020 0048 006F 00E0 0069 0020 0053 01A1 006E"), 1026, 908 - frameExtraY, 3.2, True, 63, 0, 68
    End If
    xmin = original(0).X: xmax = xmin: ymin = original(0).Y: ymax = ymin
    For i = 1 To n - 1
        If original(i).X < xmin Then xmin = original(i).X
        If original(i).X > xmax Then xmax = original(i).X
        If original(i).Y < ymin Then ymin = original(i).Y
        If original(i).Y > ymax Then ymax = original(i).Y
    Next i
    If xmax - xmin < 0.001 Or ymax - ymin < 0.001 Then Err.Raise 5, , "Degenerate parcel bounds."
    ' Keep survey geometry at its native size; translate it without scaling.
    factor = 1
    ReDim display(0 To n - 1): ReDim lengths(0 To n - 1)
    For i = 0 To n - 1
        display(i) = Point3dFromXYZ((990 + diagramRight) / 2 + original(i).X - (xmin + xmax) / 2, (diagramBottom + 1094) / 2 + original(i).Y - (ymin + ymax) / 2, 0)
        j = (i + 1) Mod n
        lengths(i) = Sqr((original(j).X - original(i).X) ^ 2 + (original(j).Y - original(i).Y) ^ 2)
    Next i
    detailStage = "Draw parcel"
    Set shape = CreateShapeElement1(Nothing, display, msdFillModeNotFilled)
    Set shape.Level = CadLevel(10): Set shape.LineStyle = solidStyle
    shape.Color = 0: shape.LineWeight = 0
    ActiveModelReference.AddElement shape
    DrawAnnotations display
    If gcn Then
        DrawGCNLengths display, lengths
        RestoreGCNCoordinates original, display
        AssertWorldParcel original
    ActiveDesignFile.Save
        PublishResult "OK", target
        Exit Sub
    End If
    pages = (n + 19) \ 20
    For page = 0 To pages - 1
        tableOffset = page * (250 + frameExtraX)
        If page > 0 Then
            DrawLine 979, 881 - frameExtraY, 1189 + frameExtraX, 881 - frameExtraY, 63
            DrawLine 1189 + frameExtraX, 881 - frameExtraY, 1189 + frameExtraX, 1172, 63
            DrawLine 1189 + frameExtraX, 1172, 979, 1172, 63
            DrawLine 979, 1172, 979, 881 - frameExtraY, 63
            PutText "TO " & CStr(parcelRow(0)) & " - THUA " & CStr(parcelRow(1)) & " - BANG BO SUNG " & CStr(page), 1005, 1145, 3
        End If
        first = page * 20: segmentCount = n - first
        If segmentCount > 20 Then segmentCount = 20
        DrawTables original, lengths, first, segmentCount
    Next page
    tableOffset = 0
    PutText "SO DO MINH HOA; TOA DO/CHIEU DAI LAY TU MDB; KHONG DO TREN HINH", 992, 953 - frameExtraY, 0.9, False, 0, 0, diagramRight - 994
    RestoreWorldCoordinates original, display, 1
    detailStage = "Save new output"
    AssertWorldParcel original
    ActiveDesignFile.Save
    PublishResult "OK", target
    MsgBox "SONMAP+ V10 - Sheet " & CStr(parcelRow(0)) & " / Parcel " & CStr(parcelRow(1)) & " / MDB ID " & CStr(parcelRow(9)) & vbCrLf & "Created: " & target & vbCrLf & "Coordinate table pages: " & CStr(pages) & vbCrLf & "Check attributes, labels and print scale before official use.", vbInformation
    Exit Sub
Failed:
    Dim exportFailure As String
    exportFailure = "Export failed at: " & detailStage & vbCrLf & "Error " & CStr(Err.Number) & ": " & Err.Description & vbCrLf & "Partial output: " & target
    tableOffset = 0
    Set labelParts = Nothing
    PublishResult "ERROR", exportFailure
    MsgBox exportFailure, vbExclamation
End Sub

Private Sub AlignDiagramTemplate()
    Dim criteria As New ElementScanCriteria, scan As ElementEnumerator, e As Element, r As Range3d
    Dim notes As New Collection, compass As New Collection, i As Long, noteLeft As Double
    Dim t As TextElement, dx As Double
    noteLeft = 1000000
    criteria.ExcludeNonGraphical
    Set scan = ActiveModelReference.Scan(criteria)
    Do While scan.MoveNext
        Set e = scan.Current
        If e.IsGraphical Then
            r = e.Range
            If e.Type = msdElementTypeText Then
                Set t = e.AsTextElement
                ' Match the title by its words, preserving its section number.
                If InStr(1, t.Text, U("0053 01A1 0020 0111 1ED3 0020 0074 0068 1EED 0061 0020 0111 1EA5 0074"), vbTextCompare) > 0 Then
                    t.Move Point3dFromXYZ(990 - r.Low.X, 0, 0)
                    t.Rewrite
                ElseIf r.Low.X >= 990 And r.High.X <= 1120 And r.Low.Y >= 955 And r.High.Y <= 973 Then
                    notes.Add e
                    If r.Low.X < noteLeft Then noteLeft = r.Low.X
                End If
            End If
            ' The supplied template compass sits between the old frame and table.
            ' Move all its components together; leave the new table/frame intact.
            If r.Low.X >= 1120 And r.High.X <= 1137 And r.Low.Y >= 1060 And r.High.Y <= 1085 Then compass.Add e
        End If
    Loop
    If notes.Count > 0 Then
        dx = 992 - noteLeft
        For i = 1 To notes.Count
            Set e = notes(i)
            e.Move Point3dFromXYZ(dx, 0, 0)
            e.Rewrite
        Next i
    End If
    For i = 1 To compass.Count
        Set e = compass(i)
        e.Move Point3dFromXYZ(-24, 0, 0)
        e.Rewrite
    Next i
End Sub

Private Sub ScaleTemplateText()
    Dim criteria As New ElementScanCriteria, scan As ElementEnumerator, e As Element
    criteria.ExcludeNonGraphical
    Set scan = ActiveModelReference.Scan(criteria)
    Do While scan.MoveNext
        Set e = scan.Current
        ReduceElementText e
    Loop
End Sub

Private Sub ReduceElementText(ByVal e As Element)
    Dim t As TextElement, style As TextStyle, children As ElementEnumerator, child As Element
    If e.Type = msdElementTypeText Then
        Set t = e.AsTextElement
        Set style = t.TextStyle
        style.Height = style.Height * 0.9
        style.Width = style.Width * 0.9
        Set t.TextStyle = style
        t.Rewrite
    ElseIf e.Type = msdElementTypeCellHeader Then
        Set children = e.AsCellElement.GetSubElements
        Do While children.MoveNext
            Set child = children.Current
            ReduceElementText child
        Loop
        e.Rewrite
    ElseIf e.Type = msdElementTypeTextNode Then
        Set children = e.AsTextNodeElement.GetSubElements
        Do While children.MoveNext
            Set child = children.Current
            ReduceElementText child
        Loop
        e.Rewrite
    End If
End Sub

Private Sub PublishResult(ByVal status As String, ByVal message As String)
    On Error Resume Next
    Dim fs As Object, stream As Object, key As String
    If IsArray(parcelRow) Then key = CStr(parcelRow(0)) & "/" & CStr(parcelRow(1)) & "/" & CStr(parcelRow(9))
    If Len(key) = 0 Or key = "//" Then
        Set fs = CreateObject("Scripting.FileSystemObject")
        Set stream = fs.OpenTextFile(@REQUEST@, 1, False, -1)
        key = Trim$(stream.ReadAll): stream.Close
    End If
    Set fs = CreateObject("Scripting.FileSystemObject")
    Set stream = fs.CreateTextFile(@RESULT@, True, True)
    stream.Write status & vbTab & key & vbTab & message
    stream.Close
End Sub

Private Sub ClearExtraPages()
    Dim criteria As New ElementScanCriteria, scan As ElementEnumerator, e As Element, r As Range3d
    Dim pending As New Collection, i As Long
    criteria.ExcludeNonGraphical
    Set scan = ActiveModelReference.Scan(criteria)
    Do While scan.MoveNext
        Set e = scan.Current
        If Not e Is Nothing Then
            If e.IsGraphical Then
                r = e.Range
                If r.Low.X > 1190 Or r.High.X < 978 Or r.Low.Y > 1173 Or r.High.Y < 880 Then pending.Add e
            End If
        End If
    Loop
    For i = 1 To pending.Count
        Set e = pending(i)
        ActiveModelReference.RemoveElement e
    Next i
End Sub

Private Sub ClearEmptyDiagramText()
    Dim criteria As New ElementScanCriteria, scan As ElementEnumerator, e As Element, r As Range3d
    Dim pending As New Collection, i As Long, value As String
    criteria.ExcludeAllTypes: criteria.IncludeType msdElementTypeText
    Set scan = ActiveModelReference.Scan(criteria)
    Do While scan.MoveNext
        Set e = scan.Current
        r = e.Range
        If r.Low.X >= 990 And r.High.X <= 1120 And r.Low.Y >= 974 And r.High.Y <= 1094 Then
            value = Replace(e.AsTextElement.Text, ChrW(160), " ")
            If Len(Trim$(value)) = 0 And r.High.X - r.Low.X < 1 And r.High.Y - r.Low.Y < 1 Then pending.Add e
        End If
    Loop
    For i = 1 To pending.Count
        Set e = pending(i)
        ActiveModelReference.RemoveElement e
    Next i
End Sub


Private Sub RestoreGCNCoordinates(ByRef original() As Point3d, ByRef display() As Point3d)
    RestoreWorldCoordinates original, display, 1
End Sub

Private Sub RestoreWorldCoordinates(ByRef original() As Point3d, ByRef display() As Point3d, ByVal drawingScale As Double)
    Dim criteria As New ElementScanCriteria, scan As ElementEnumerator, e As Element
    Dim offset As Point3d, pending As New Collection, i As Long
    If drawingScale <= 0 Then Err.Raise 5, , "Invalid diagram scale."
    offset = Point3dFromXYZ(original(0).X - display(0).X, original(0).Y - display(0).Y, 0)
    criteria.ExcludeNonGraphical
    Set scan = ActiveModelReference.Scan(criteria)
    Do While scan.MoveNext
        pending.Add scan.Current
    Loop
    For i = 1 To pending.Count
        Set e = pending(i)
        If drawingScale <> 1 Then e.ScaleUniform display(0), 1 / drawingScale
        e.Move offset
        e.Rewrite
    Next i
End Sub

Private Sub ClearGCNTemplate()
    Dim criteria As New ElementScanCriteria, scan As ElementEnumerator, e As Element
    Dim pending As New Collection, i As Long
    criteria.ExcludeNonGraphical
    Set scan = ActiveModelReference.Scan(criteria)
    Do While scan.MoveNext
        pending.Add scan.Current
    Loop
    For i = 1 To pending.Count
        Set e = pending(i)
        ActiveModelReference.RemoveElement e
    Next i
End Sub

Private Function GCNTableFits(ByVal left As Double, ByVal top As Double, ByVal w As Double, ByVal h As Double, ByRef p() As Point3d) As Boolean
    Dim corner As Point3d, x As Variant, y As Variant, i As Long, j As Long
    Dim dx As Double, dy As Double, a As Double, b As Double, low As Double, high As Double, swap As Double
    Dim criteria As New ElementScanCriteria, scan As ElementEnumerator, e As Element, r As Range3d
    ' Reject polygon interior, vertices and every segment crossing the rectangle.
    For Each x In Array(left, left + w)
        For Each y In Array(top - h, top)
            corner = Point3dFromXYZ(CDbl(x), CDbl(y), 0)
            If InsidePolygon(corner, p) Then Exit Function
        Next y
    Next x
    For i = 0 To UBound(p)
        j = (i + 1) Mod (UBound(p) + 1)
        dx = p(j).X - p(i).X: dy = p(j).Y - p(i).Y
        low = 0: high = 1
        If Abs(dx) < 0.000001 Then
            If p(i).X < left Or p(i).X > left + w Then high = -1
        Else
            a = (left - p(i).X) / dx: b = (left + w - p(i).X) / dx
            If a > b Then swap = a: a = b: b = swap
            If a > low Then low = a
            If b < high Then high = b
        End If
        If Abs(dy) < 0.000001 Then
            If p(i).Y < top - h Or p(i).Y > top Then high = -1
        Else
            a = (top - h - p(i).Y) / dy: b = (top - p(i).Y) / dy
            If a > b Then swap = a: a = b: b = swap
            If a > low Then low = a
            If b < high Then high = b
        End If
        If low <= high Then Exit Function
    Next i
    ' Also reserve room around vertex numbers, parcel labels and neighbor rays.
    criteria.ExcludeNonGraphical
    Set scan = ActiveModelReference.Scan(criteria)
    Do While scan.MoveNext
        Set e = scan.Current
        If Not e.IsShapeElement Then
            r = e.Range
            If r.High.X + 2 >= left And r.Low.X - 2 <= left + w And r.High.Y + 2 >= top - h And r.Low.Y - 2 <= top Then Exit Function
        End If
    Loop
    GCNTableFits = True
End Function

Private Sub DrawGCNLengths(ByRef p() As Point3d, ByRef lengths() As Double)
    Dim n As Long, i As Long, j As Long, left As Double, top As Double, w As Double, h As Double
    Dim x As Double, y As Double, found As Boolean, rowHeight As Double, bottom As Double, attempts As Long
    n = UBound(p) + 1: rowHeight = 4.2: w = 26: h = 10 + (n + 1) * rowHeight
    ' Prefer empty space inside the existing frame; never scale the parcel.
    y = 1090
    Do While y - h >= diagramBottom + 4 And Not found And attempts < 200
        x = 994
        Do While x + w <= diagramRight - 4 And Not found And attempts < 200
            attempts = attempts + 1
            If GCNTableFits(x, y, w, h, p) Then left = x: top = y: found = True
            x = x + (diagramRight - 990) / 12
        Loop
        y = y - (1094 - diagramBottom) / 12
    Loop
    If Not found Then
        ' Add an empty band on the right if every candidate is occupied.
        left = diagramRight + 4: top = 1090
        diagramRight = left + w + 4
        If top - h - 4 < diagramBottom Then diagramBottom = top - h - 4
    End If
    bottom = top - h
    DrawLine 990, diagramBottom, diagramRight, diagramBottom, 63
    DrawLine diagramRight, diagramBottom, diagramRight, 1094, 63
    DrawLine diagramRight, 1094, 990, 1094, 63
    DrawLine 990, 1094, 990, diagramBottom, 63
    Set labelParts = New Collection
    PutText U("0053 1ED1 0020 0068 0069 1EC7 0075"), left + 7, top - 3, 1.9, True, 63, 0, 12
    PutText U("0111 1EC9 006E 0068 0020 0074 0068 1EED 0061"), left + 7, top - 7, 1.9, True, 63, 0, 12
    PutText U("0043 0068 0069 1EC1 0075"), left + 20, top - 3, 1.9, True, 63, 0, 10
    PutText U("0064 00E0 0069 0028 006D 0029"), left + 20, top - 7, 1.9, True, 63, 0, 10
    DrawLine left, top, left + w, top, 63
    DrawLine left, top - 10, left + w, top - 10, 63
    DrawLine left, bottom, left + w, bottom, 63
    DrawLine left, top, left, bottom, 63
    DrawLine left + w, top, left + w, bottom, 63
    DrawLine left + 14, top, left + 14, bottom, 63
    For i = 0 To n
        y = top - 10 - (i + 0.5) * rowHeight
        PutText CStr((i Mod n) + 1), left + 7, y, 1.9, True, 63, 0, 12
        If i < n Then
            PutText DecimalComma(lengths(i), "0.00"), left + 20, top - 10 - (i + 1) * rowHeight, 1.9, True, 63, 0, 10
            DrawLine left, top - 10 - (i + 1) * rowHeight, left + 14, top - 10 - (i + 1) * rowHeight, 63
        End If
    Next i
    CommitParcelLabel "BANG_CHIEU_DAI"
End Sub

Private Sub ClearUnusedAddressText()
    Dim criteria As New ElementScanCriteria, scan As ElementEnumerator, e As Element, r As Range3d
    Dim pending As New Collection, i As Long, value As String, addressLabel As String
    Dim t As TextElement
    addressLabel = U("0110 1ECB 0061 0020 0063 0068 1EC9 0020 0074 0068 1EED 0061 0020 0111 1EA5 0074")
    criteria.ExcludeAllTypes: criteria.IncludeType msdElementTypeText
    Set scan = ActiveModelReference.Scan(criteria)
    Do While scan.MoveNext
        Set e = scan.Current: Set t = e.AsTextElement
        r = e.Range: value = Trim$(t.Text)
        If Left$(value, 2) = "4." And InStr(1, value, U("0047 0069 1EA5 0079 0020 0063 0068 1EE9 006E 0067 0020 006E 0068 1EAD 006E"), vbTextCompare) > 0 Then
            t.Text = U("0034 002E 0020 0047 0069 1EA5 0079 0020 0063 0068 1EE9 006E 0067 0020 006E 0068 1EAD 006E 003A") & " ........................................................................................"
            t.Rewrite
        ElseIf InStr(1, value, addressLabel, vbTextCompare) > 0 Then
            ' Keep the address near the first row; remove the certificate overlap
            ' and the unused duplicate under the signature area.
            If r.High.Y < 955 Or (r.Low.Y >= 1107 And r.Low.Y <= 1120) Then pending.Add e
        End If
    Loop
    For i = 1 To pending.Count
        Set e = pending(i)
        ActiveModelReference.RemoveElement e
    Next i
End Sub

Private Sub CalculateDiagramFrame(ByRef p() As Point3d)
    Dim xmin As Double, xmax As Double, ymin As Double, ymax As Double, i As Long, frameScale As Double
    xmin = p(0).X: xmax = xmin: ymin = p(0).Y: ymax = ymin
    For i = 1 To UBound(p)
        If p(i).X < xmin Then xmin = p(i).X
        If p(i).X > xmax Then xmax = p(i).X
        If p(i).Y < ymin Then ymin = p(i).Y
        If p(i).Y > ymax Then ymax = p(i).Y
    Next i
    frameScale = 1
    If (xmax - xmin + 40) / 130 > frameScale Then frameScale = (xmax - xmin + 40) / 130
    If (ymax - ymin + 60) / 139 > frameScale Then frameScale = (ymax - ymin + 60) / 139
    frameExtraX = 130 * (frameScale - 1)
    frameExtraY = 139 * (frameScale - 1)
    diagramRight = 1120 + frameExtraX
    diagramBottom = 955 - frameExtraY
End Sub

Private Sub ResizeTemplatePage()
    Dim criteria As New ElementScanCriteria, scan As ElementEnumerator, e As Element, r As Range3d
    Dim pending As New Collection, i As Long, border As Boolean, dx As Double, dy As Double
    criteria.ExcludeNonGraphical
    Set scan = ActiveModelReference.Scan(criteria)
    Do While scan.MoveNext
        Set e = scan.Current
        r = e.Range: border = False
        If Abs(r.Low.X - 979) < 2 And Abs(r.High.X - 1189) < 2 Then
            If Abs(r.Low.Y - 881) < 2 And Abs(r.High.Y - 881) < 2 Then border = True
            If Abs(r.Low.Y - 1172) < 2 And Abs(r.High.Y - 1172) < 2 Then border = True
            If Abs(r.Low.Y - 881) < 2 And Abs(r.High.Y - 1172) < 2 Then border = True
        End If
        If r.High.Y - r.Low.Y > 285 Then
            If Abs(r.Low.X - 979) < 2 And Abs(r.High.X - 979) < 2 Then border = True
            If Abs(r.Low.X - 1189) < 2 And Abs(r.High.X - 1189) < 2 Then border = True
        End If
        If border Then
            pending.Add e
        ElseIf e.IsTextElement Or e.IsTextNodeElement Or e.IsCellElement Then
            dx = 0: dy = 0
            If r.High.Y <= 974 Then
                dy = -frameExtraY
                If r.Low.X >= 1070 Then dx = frameExtraX
            ElseIf r.Low.X >= 1090 And r.High.X <= 1115 And r.Low.Y >= 1060 And r.High.Y <= 1085 Then
                dx = frameExtraX
            ElseIf r.Low.Y >= 1148 Then
                If r.Low.Y >= 1165 Then dx = frameExtraX Else dx = frameExtraX / 2
            End If
            If dx <> 0 Or dy <> 0 Then
                e.Move Point3dFromXYZ(dx, dy, 0)
                e.Rewrite
            End If
        ElseIf r.Low.X >= 1090 And r.High.X <= 1115 And r.Low.Y >= 1060 And r.High.Y <= 1085 Then
            e.Move Point3dFromXYZ(frameExtraX, 0, 0)
            e.Rewrite
        End If
    Loop
    For i = 1 To pending.Count
        Set e = pending(i)
        ActiveModelReference.RemoveElement e
    Next i
    DrawLine 979, 881 - frameExtraY, 1189 + frameExtraX, 881 - frameExtraY, 63
    DrawLine 1189 + frameExtraX, 881 - frameExtraY, 1189 + frameExtraX, 1172, 63
    DrawLine 1189 + frameExtraX, 1172, 979, 1172, 63
    DrawLine 979, 1172, 979, 881 - frameExtraY, 63
End Sub

Private Sub FillHeader()
    Dim criteria As New ElementScanCriteria, scan As ElementEnumerator, e As Element, t As TextElement
    Dim value As String, updated As String, textBounds As Range3d, style As TextStyle, available As Double
    criteria.ExcludeAllTypes: criteria.IncludeType msdElementTypeText
    Set scan = ActiveModelReference.Scan(criteria)
    Do While scan.MoveNext
        Set e = scan.Current
        Set t = e.AsTextElement
        value = t.Text: updated = value
        Select Case Trim$(value)
            Case "ShThua": updated = CStr(parcelRow(1))
            Case "ToBd": updated = CStr(parcelRow(0))
            Case "TenChu": updated = CStr(parcelRow(3))
            Case "DienTich": updated = DecimalComma(Val(parcelRow(2)), "0.0")
            Case "Mdsd": updated = parcelLandCode
            Case "PhuongXa", "BB 908397": updated = ""
            Case U("0043 1ED5 0020 0054 0068 00E0 006E 0068 0020 0043 1EE5 0069 0020 0045 006D"): updated = ""
        End Select
        If InStr(1, value, U("0110 1ECB 0061 0020 0063 0068 1EC9 0020 0074 0068 1EED 0061 0020 0111 1EA5 0074 003A"), vbBinaryCompare) = 1 Then updated = U("0110 1ECB 0061 0020 0063 0068 1EC9 0020 0074 0068 1EED 0061 0020 0111 1EA5 0074 003A") & " " & parcelAddress
        If updated <> value Then
            t.Text = updated
            t.Rewrite
            textBounds = t.Range
            If textBounds.High.X > 1183 Then
                available = 1183 - textBounds.Low.X
                If available > 0 And textBounds.High.X > textBounds.Low.X Then
                    Set style = t.TextStyle
                    style.Width = style.Width * available / (textBounds.High.X - textBounds.Low.X)
                    Set t.TextStyle = style
                    t.Rewrite
                End If
            End If
        End If
    Loop
End Sub

Private Sub DrawAnnotations(ByRef p() As Point3d)
    Dim n As Long, i As Long, cx As Double, cy As Double, vx As Double, vy As Double, distance As Double
    Dim center As Point3d, rotation As Matrix3d, mark As EllipseElement, labelX As Double, labelY As Double
    Dim placed() As Point3d, candidate As Point3d, attempt As Long, angle As Double, radius As Double, safe As Boolean, previous As Long
    Dim cadColors As ColorTable, yellow As Long, green As Long, red As Long
    Dim items As Variant, values As Variant, item As Variant, fraction As Double, mx As Double, my As Double, j As Long
    n = UBound(p) + 1
    For i = 0 To n - 1
        cx = cx + p(i).X / n: cy = cy + p(i).Y / n
    Next i
    ' A vertex-average label position may lie outside a concave parcel.
    center = Point3dFromXYZ(cx, cy, 0)
    If Not InsidePolygon(center, p) Then
        For i = 0 To n - 1
            j = (i + 1) Mod n
            mx = (p(i).X + p(j).X) / 2: my = (p(i).Y + p(j).Y) / 2
            vx = -(p(j).Y - p(i).Y): vy = p(j).X - p(i).X
            distance = Sqr(vx * vx + vy * vy)
            If distance > 0.001 Then
                center = Point3dFromXYZ(mx + vx / distance * 3, my + vy / distance * 3, 0)
                If InsidePolygon(center, p) Then cx = center.X: cy = center.Y: Exit For
                center = Point3dFromXYZ(mx - vx / distance * 3, my - vy / distance * 3, 0)
                If InsidePolygon(center, p) Then cx = center.X: cy = center.Y: Exit For
            End If
        Next i
    End If
    rotation = Matrix3dIdentity
    ReDim placed(0 To n - 1)
    For i = 0 To n - 1
        vx = p(i).X - cx: vy = p(i).Y - cy
        distance = Sqr(vx * vx + vy * vy)
        If distance < 0.001 Then distance = 1
        center = p(i)
        Set mark = CreateEllipseElement2(Nothing, center, 0.66, 0.66, rotation, msdFillModeFilled)
        mark.Color = 0: Set mark.LineStyle = solidStyle
        Set mark.Level = CadLevel(63)
        ActiveModelReference.AddElement mark
        labelX = center.X + vx / distance * 3.5: labelY = center.Y + vy / distance * 3.5
        If i = 0 Then labelX = center.X + 4.2: labelY = center.Y + 1.8
        If i = 1 Then labelX = center.X + 5: labelY = center.Y - 3
        For attempt = 0 To 48
            candidate = Point3dFromXYZ(labelX, labelY, 0)
            safe = candidate.X >= 993 And candidate.X <= diagramRight - 3 And candidate.Y >= diagramBottom + 24 And candidate.Y <= 1091
            For previous = 0 To i - 1
                If Sqr((candidate.X - placed(previous).X) ^ 2 + (candidate.Y - placed(previous).Y) ^ 2) < 4.2 Then safe = False
            Next previous
            If safe Then Exit For
            angle = (attempt Mod 12) * 6.28318530717959 / 12
            radius = 4 + (attempt \ 12) * 1.5
            labelX = center.X + Cos(angle) * radius
            labelY = center.Y + Sin(angle) * radius
        Next attempt
        placed(i) = Point3dFromXYZ(labelX, labelY, 0)
        PutText CStr(i + 1), labelX, labelY, 2.64, True, 63
    Next i
    If @COLORS@ Then
        Set cadColors = ActiveDesignFile.ExtractColorTable
        yellow = cadColors.FindClosestColor(RGB(255, 255, 0))
        green = cadColors.FindClosestColor(RGB(0, 255, 0))
        red = cadColors.FindClosestColor(RGB(255, 0, 0))
    End If
    center = Point3dFromXYZ(cx, cy, 0)
    Set labelParts = New Collection
    PutText CStr(parcelRow(1)), cx, cy + 3.6, 3.6, True, 13, yellow
    DrawLine cx - 8.4, cy, cx + 8.4, cy, 13, green
    PutText DecimalComma(Val(parcelRow(2)), "0.0"), cx, cy - 3.6, 3.6, True, 4, red
    If Len(parcelLandCode) > 0 Then PutText parcelLandCode, cx - 17, cy, 3.6, True, 2, green
    CommitParcelLabel
    cx = center.X: cy = center.Y
    If Len(CStr(parcelRow(7))) > 0 Then
        items = Split(parcelRow(7), ";")
        For Each item In items
            values = Split(item, "|"): i = CLng(values(0)): fraction = Val(values(1)): j = (i + 1) Mod n
            mx = p(i).X + (p(j).X - p(i).X) * fraction
            my = p(i).Y + (p(j).Y - p(i).Y) * fraction
            vx = -(p(j).Y - p(i).Y): vy = p(j).X - p(i).X: distance = Sqr(vx * vx + vy * vy)
            If distance > 0.001 Then
                vx = vx / distance: vy = vy / distance
                If vx * (mx - cx) + vy * (my - cy) < 0 Then vx = -vx: vy = -vy
                PutText CStr(values(2)), mx + vx * 9, my + vy * 9, 3.3, True, 13
            End If
        Next item
    End If
    If Len(CStr(parcelRow(8))) > 0 Then
        items = Split(parcelRow(8), ";")
        For Each item In items
            values = Split(item, "|"): i = CLng(values(0))
            DrawLine p(i).X, p(i).Y, p(i).X + Val(values(1)) * 7, p(i).Y + Val(values(2)) * 7, 10
        Next item
    End If
End Sub

Private Sub CommitParcelLabel(Optional ByVal cellName As String = "NHAN_THUA")
    Dim parts() As Element, i As Long, block As CellElement, origin As Point3d
    If labelParts Is Nothing Then Exit Sub
    If labelParts.Count < 3 Then Err.Raise 5, , "Parcel label components are incomplete."
    ReDim parts(0 To labelParts.Count - 1)
    For i = 0 To labelParts.Count - 1
        Set parts(i) = labelParts(i + 1)
    Next i
    origin = Point3dZero
    Set block = CreateCellElement1(cellName, parts, origin, False)
    If block Is Nothing Then Err.Raise 5, , "Could not create parcel label cell."
    ActiveModelReference.AddElement block
    Set labelParts = Nothing
End Sub

Private Function ParcelLabelFits(ByRef center As Point3d, ByRef p() As Point3d) As Boolean
    Dim left As Double, corner As Point3d, dx As Variant, dy As Variant
    left = -8.4
    If Len(parcelLandCode) > 0 Then left = -15.6 - Len(parcelLandCode) * 3 * 0.75 / 2
    ParcelLabelFits = True
    For Each dx In Array(left, 8.4)
        For Each dy In Array(-6, 6)
            corner = Point3dFromXYZ(center.X + CDbl(dx), center.Y + CDbl(dy), 0)
            If Not InsidePolygon(corner, p) Then ParcelLabelFits = False
        Next dy
    Next dx
End Function

Private Sub DrawTables(ByRef p() As Point3d, ByRef lengths() As Double, ByVal first As Long, ByVal count As Long)
    Dim i As Long, j As Long, k As Long, n As Long, y As Double, bottom As Double, top As Double, rowHeight As Double, xShift As Double
    n = UBound(p) + 1
    top = 1094: bottom = diagramBottom
    rowHeight = (top - 12 - bottom) / 21
    xShift = frameExtraX
    If first > 0 Then xShift = -134
    PutText U("0038 002E 0020 0054 1ECD 0061 0020 0111 1ED9 0020 0076 00E0 0020 0063 0068 0069 1EC1 0075 0020 0064 00E0 0069 0020 0063 1EA1 006E 0068 0020 0074 0068 1EED 0061 003A"), 1124 + xShift, top + 5, 2.5, False, 0, 0, 54
    PutText U("0110 1EC9 006E 0068"), 1127.5 + xShift, top - 6, 2.1, True, 63, 0, 6.5
    PutText U("0054 1ECD 0061 0020 0111 1ED9 0020 0111 1EC9 006E 0068 0020 0074 0068 1EED 0061 0020 0028 002A 0029"), 1150.5 + xShift, top - 3, 2.1, True, 63, 0, 38
    PutText "X (m)", 1140.75 + xShift, top - 9, 2.1, True
    PutText "Y (m)", 1160.25 + xShift, top - 9, 2.1, True
    PutText U("004B 00ED 0063 0068"), 1174 + xShift, top - 2, 2.1, True, 63, 0, 7.5
    PutText U("0074 0068 01B0 1EDB 0063"), 1174 + xShift, top - 5, 2.1, True, 63, 0, 7.5
    PutText U("0063 1EA1 006E 0068 0020 0028 006D 0029"), 1174 + xShift, top - 9, 1.9, True, 63, 0, 7.5
    DrawLine 1124 + xShift, top, 1178 + xShift, top
    DrawLine 1131 + xShift, top - 6, 1170 + xShift, top - 6
    DrawLine 1124 + xShift, top - 12, 1178 + xShift, top - 12
    DrawLine 1124 + xShift, bottom, 1178 + xShift, bottom
    DrawLine 1124 + xShift, top, 1124 + xShift, bottom
    DrawLine 1131 + xShift, top, 1131 + xShift, bottom
    DrawLine 1150.5 + xShift, top - 6, 1150.5 + xShift, bottom
    DrawLine 1170 + xShift, top, 1170 + xShift, bottom
    DrawLine 1178 + xShift, top, 1178 + xShift, bottom
    For i = 1 To 20
        DrawLine 1124 + xShift, top - 12 - i * rowHeight, 1170 + xShift, top - 12 - i * rowHeight
    Next i
    For i = 0 To count
        k = (first + i) Mod n: y = top - 12 - (i + 0.5) * rowHeight
        PutText CStr(k + 1), 1127.5 + xShift, y, 2.1, True
        PutText DecimalComma(p(k).Y, "0.000"), 1140.75 + xShift, y, 2.1, True
        PutText DecimalComma(p(k).X, "0.000"), 1160.25 + xShift, y, 2.1, True
        If i < count Then
            PutText DecimalComma(lengths(k), "0.00"), 1174 + xShift, top - 12 - (i + 1) * rowHeight, 2.1, True
        End If
    Next i
End Sub

Private Function RuntimeSetting(ByVal index As Long) As String
    Dim fs As Object, stream As Object, lines As Variant
    Set fs = CreateObject("Scripting.FileSystemObject")
    Set stream = fs.OpenTextFile(@RUNTIME@, 1, False, -1)
    lines = Split(Replace(stream.ReadAll, vbCr, ""), vbLf): stream.Close
    RuntimeSetting = CStr(lines(index))
End Function

Private Sub WidenDiagramFrame()
    Dim criteria As New ElementScanCriteria, scan As ElementEnumerator, e As Element, r As Range3d
    Dim pending As New Collection, i As Long, border As Boolean
    criteria.ExcludeNonGraphical
    Set scan = ActiveModelReference.Scan(criteria)
    Do While scan.MoveNext
        Set e = scan.Current
        If e.IsGraphical Then
            r = e.Range
            border = False
            If Abs(r.Low.X - 1004) < 2 And Abs(r.High.X - 1004) < 2 And r.High.Y - r.Low.Y > 130 Then border = True
            If Abs(r.Low.X - 1134) < 2 And Abs(r.High.X - 1134) < 2 And r.High.Y - r.Low.Y > 130 Then border = True
            If Abs(r.Low.X - 1004) < 2 And Abs(r.High.X - 1134) < 2 Then
                If Abs(r.Low.Y - 955) < 2 And Abs(r.High.Y - 955) < 2 Then border = True
                If Abs(r.Low.Y - 1094) < 2 And Abs(r.High.Y - 1094) < 2 Then border = True
                If Abs(r.Low.Y - 955) < 2 And Abs(r.High.Y - 1094) < 2 Then border = True
            End If
            If border Then pending.Add e
        End If
    Loop
    For i = 1 To pending.Count
        Set e = pending(i)
        ActiveModelReference.RemoveElement e
    Next i
    DrawLine 990, diagramBottom, 990, 1094, 63
    DrawLine 990, 1094, diagramRight, 1094, 63
    DrawLine 990, diagramBottom, diagramRight, diagramBottom, 63
    ' Retain the original right edge; add it if the original was a closed shape.
    DrawLine diagramRight, diagramBottom, diagramRight, 1094, 63
End Sub

Private Sub AlignHeaderText()
    Dim criteria As New ElementScanCriteria, scan As ElementEnumerator, e As Element
    Dim t As TextElement, r As Range3d, style As TextStyle, available As Double
    criteria.ExcludeAllTypes: criteria.IncludeType msdElementTypeText
    Set scan = ActiveModelReference.Scan(criteria)
    Do While scan.MoveNext
        Set e = scan.Current
        r = e.Range
        If r.Low.X >= 1000 And r.Low.Y >= 1095 And r.High.Y <= 1148 Then
            Set t = e.AsTextElement
            t.Move Point3dFromXYZ(-14, 0, 0)
            If Left$(Trim$(t.Text), 2) = "1." Then
                r = t.Range
                t.Move Point3dFromXYZ(990 - r.Low.X, 0, 0)
            End If
            Set style = t.TextStyle
            style.Width = style.Height * 0.95
            Set t.TextStyle = style
            r = t.Range: available = 1178 - r.Low.X
            If available > 0 And r.High.X > 1178 Then
                style.Width = style.Width * available / (r.High.X - r.Low.X)
                Set t.TextStyle = style
            End If
            t.Rewrite
        End If
    Loop
End Sub


Private Sub WhiteOnDarkBackground()
    Dim colors As ColorTable, index As Long
    Set colors = ActiveDesignFile.ExtractColorTable
    For index = 0 To 254
        If index = 0 Or colors.GetColorAtIndex(index) = RGB(0, 0, 0) Then
            colors.SetColorAtIndex index, RGB(255, 255, 255)
        End If
    Next index
    ActiveDesignFile.AttachColorTable colors
End Sub


Private Sub AssertWorldParcel(ByRef original() As Point3d)
    Dim criteria As New ElementScanCriteria, scan As ElementEnumerator, e As Element
    Dim vertices() As Point3d, i As Long, j As Long, found As Boolean, matched As Boolean
    criteria.ExcludeNonGraphical
    Set scan = ActiveModelReference.Scan(criteria)
    Do While scan.MoveNext
        Set e = scan.Current
        If e.IsShapeElement Then
            vertices = e.AsShapeElement.GetVertices
            If UBound(vertices) >= UBound(original) Then
                matched = True
                For i = LBound(original) To UBound(original)
                    found = False
                    For j = LBound(vertices) To UBound(vertices)
                        If Abs(vertices(j).X - original(i).X) < 0.00001 And Abs(vertices(j).Y - original(i).Y) < 0.00001 Then found = True: Exit For
                    Next j
                    If Not found Then matched = False: Exit For
                Next i
                If matched Then Exit Sub
            End If
        End If
    Loop
    Err.Raise 5, , "Output parcel does not match MDB world coordinates. No success receipt was issued."
End Sub
