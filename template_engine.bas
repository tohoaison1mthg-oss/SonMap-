Attribute VB_Name = "LH_GhepThanhTan"
Option Explicit
Private detailStage As String
Private unicodeTemplate As TextElement
Private solidStyle As LineStyle
Private parcelLandCode As String
Private parcelAddress As String

Public Sub GhepThanhTan()
    On Error GoTo Failed
    Dim template As String, target As String, stage As String
    Dim fs As Object, d As DesignFile
    Dim original(0 To 8) As Point3d, display(0 To 8) As Point3d
    Dim i As Long, dx As Double, dy As Double, shape As ShapeElement
    template = "D:\TX NGA NAM\MAU\TrichLucTT26 -ThanhTan.dgn"
    target = InputBox("Full path of NEW output DGN:", "Thanh Tan test", "D:\TX NGA NAM\MAU\To100_Thua1_ThanhTan_v20.dgn")
    If Len(target) = 0 Then Exit Sub
    Set fs = CreateObject("Scripting.FileSystemObject")
    If fs.FileExists(target) Then Err.Raise 5, , "Output exists. Choose another name."
    If LCase$(fs.GetExtensionName(target)) <> "dgn" Then Err.Raise 5, , "Use a .dgn filename."
    stage = "Copy template"
    fs.CopyFile template, target, False
    stage = "Open output"
    Set d = OpenDesignFile(target, False)
    If LCase$(ActiveDesignFile.FullName) <> LCase$(target) Then Err.Raise 5, , "Output not active."
    detailStage = "Find solid line style"
    FindSolidStyle
    FindUnicodeTemplate
    FillParcelHeader
    original(0) = Point3dFromXYZ(511195.734, 1059024.199, 0)
    original(1) = Point3dFromXYZ(511190.548, 1059016.713, 0)
    original(2) = Point3dFromXYZ(511178.867, 1058997.69, 0)
    original(3) = Point3dFromXYZ(511173.249, 1059001.037, 0)
    original(4) = Point3dFromXYZ(511096.747, 1059046.616, 0)
    original(5) = Point3dFromXYZ(511065.18, 1059063.72, 0)
    original(6) = Point3dFromXYZ(511078.74, 1059091.3, 0)
    original(7) = Point3dFromXYZ(511144.56, 1059058.17, 0)
    original(8) = Point3dFromXYZ(511190.303, 1059027.804, 0)
    ' Translate to first-page drawing box at 1:1 model scale.
    dx = 1069.1885384685 - (511055.18 + 511195.734) / 2
    dy = 1024.99516129005 - (1058998.376 + 1059091.3) / 2
    ' Fit diagram within 129.8 x 138.7 model-unit box, with margins.
    ' Scale diagram only; original coordinates remain untouched.
    For i = 0 To 8
        display(i) = Point3dFromXYZ(1069.1885384685 + (original(i).X - (511055.18 + 511195.734) / 2) * 0.8, 1024.99516129005 + (original(i).Y - (1058998.376 + 1059091.3) / 2) * 0.8, 0)
    Next i
    stage = "Add parcel diagram"
    detailStage = "Create parcel shape"
    Set shape = CreateShapeElement1(Nothing, display, msdFillModeNotFilled)
    Set shape.Level = CadLevel(10)
    shape.Color = 0
    Set shape.LineStyle = solidStyle
    shape.LineWeight = 0
    ActiveModelReference.AddElement shape
    DrawParcelAnnotations display
    stage = "Replace right-hand table on output copy"
    detailStage = "Scan old table"
    ClearTablePanel
    Dim edgeLength(0 To 8) As Double, nextVertex As Long
    For i = 0 To 8
        nextVertex = (i + 1) Mod 9
        edgeLength(i) = Sqr((original(nextVertex).X - original(i).X) ^ 2 + (original(nextVertex).Y - original(i).Y) ^ 2)
    Next i
    stage = "Draw coordinates and edge lengths"
    DrawCoordinateTable original, edgeLength
    stage = "Draw separate length table"
    DrawLengthTable edgeLength
    PutText "BAN THU - SO DO THU NHO 0.8; CHUA CHOT TY LE IN", 1006, 953, 1
    CadInputQueue.SendKeyin "FILEDESIGN"
    MsgBox "Created: " & target & vbCrLf & "Review layout and old template content before use.", vbInformation
    Exit Sub
Failed:
    MsgBox "Stage: " & stage & vbCrLf & "Detail: " & detailStage & vbCrLf & "Error " & CStr(Err.Number) & ": " & Err.Description, vbExclamation
End Sub

Private Sub PutText(ByVal value As String, ByVal x As Double, ByVal y As Double, ByVal h As Double, Optional ByVal centered As Boolean = False, Optional ByVal levelCode As Long = 0, Optional ByVal textColor As Long = 0, Optional ByVal maxWidth As Double = 0)
    Dim t As TextElement, font As Font, style As TextStyle
    detailStage = "Create text: " & value
    ' Preserve the native template font and Unicode text settings.
    Set t = CreateTextElement1(unicodeTemplate, value, Point3dFromXYZ(x, y, 0), Matrix3dIdentity)
    If t Is Nothing Then Err.Raise 91, , "MicroStation returned no TextElement."
    ' Font inherited from a native Vietnamese text element.
    Set t.LineStyle = solidStyle
    t.LineWeight = 0
    t.Color = textColor
    If levelCode > 0 Then Set t.Level = CadLevel(levelCode)
    Set style = t.TextStyle
    If IsAsciiText(value) Then
        Set font = ActiveDesignFile.Fonts("Arial")
        Set style.Font = font
    End If
    style.IsItalic = False
    style.IsBold = False
    If centered Then
        style.Justification = msdTextJustificationCenterCenter
    Else
        style.Justification = msdTextJustificationLeftBottom
    End If
    style.Height = h * 0.9
    style.Width = h * 0.95 * 0.9
    Set t.TextStyle = style
    If maxWidth > 0 Then
        If t.Range.High.X - t.Range.Low.X > maxWidth Then
            style.Width = style.Width * maxWidth / (t.Range.High.X - t.Range.Low.X)
            Set t.TextStyle = style
        End If
    End If
    ActiveModelReference.AddElement t
End Sub



Private Sub ClearTablePanel()
    Dim scan As ElementEnumerator, e As Element, r As Range3d
    Dim criteria As New ElementScanCriteria
    Dim pending As New Collection, i As Long
    criteria.ExcludeNonGraphical
    Set scan = ActiveModelReference.Scan(criteria)
    Do While scan.MoveNext
        Set e = scan.Current
        If Not e Is Nothing Then
        If e.IsGraphical Then
            r = e.Range
            ' Only objects wholly inside this first-page panel are removed.
            If r.Low.X >= 1137 And r.High.X <= 1184 And r.Low.Y >= 955 And r.High.Y <= 1111 Then
                pending.Add e
            End If
        End If
        End If
    Loop
    For i = 1 To pending.Count
        Set e = pending(i)
        detailStage = "Remove old table item " & CStr(i)
        If Not e Is Nothing Then ActiveModelReference.RemoveElement e
    Next i
End Sub

Private Sub DrawLine(ByVal x1 As Double, ByVal y1 As Double, ByVal x2 As Double, ByVal y2 As Double, Optional ByVal levelCode As Long = 0, Optional ByVal lineColor As Long = 0)
    Dim e As LineElement
    detailStage = "Create table line"
    Set e = CreateLineElement2(Nothing, Point3dFromXYZ(x1, y1, 0), Point3dFromXYZ(x2, y2, 0))
    e.Color = lineColor
    If levelCode > 0 Then Set e.Level = CadLevel(levelCode)
    Set e.LineStyle = solidStyle
    e.LineWeight = 0
    ActiveModelReference.AddElement e
End Sub


Private Sub DrawCoordinateTable(ByRef p() As Point3d, ByRef length() As Double)
    Dim i As Long, j As Long, k As Long, x As Variant, top As Double, bottom As Double
    x = Array(1138.1, 1143.1, 1158.1, 1173.1, 1182.6)
    top = 1089: bottom = 1017
    PutText U("0031 0030 002E 0020 0054 1ECD 0061 0020 0111 1ED9 0020 0076 00E0 0020 0063 0068 0069 1EC1 0075 0020 0064 00E0 0069 0020 0063 1EA1 006E 0068 0020 0074 0068 1EED 0061 003A"), 1138.1, 1101, 1.8
    PutText U("0110 1EC9 006E 0068"), 1140.6, 1083, 1.35, True
    PutText U("0054 1ECD 0061 0020 0111 1ED9 0020 0111 1EC9 006E 0068 0020 0074 0068 1EED 0061 0020 0028 002A 0029"), 1158.1, 1086, 1.275, True
    PutText "X (m)", 1150.6, 1080, 1.725, True
    PutText "Y (m)", 1165.6, 1080, 1.725, True
    PutText U("004B 00ED 0063 0068 0020 0074 0068 01B0 1EDB 0063"), 1177.85, 1085, 1.2, True
    PutText U("0063 1EA1 006E 0068 0028 006D 0029"), 1177.85, 1080, 1.275, True
    For j = 0 To 4
        If j = 2 Then
            DrawLine CDbl(x(j)), 1083, CDbl(x(j)), bottom
        Else
            DrawLine CDbl(x(j)), top, CDbl(x(j)), bottom
        End If
    Next j
    DrawLine 1138.1, top, 1182.6, top
    DrawLine 1143.1, 1083, 1173.1, 1083
    DrawLine 1138.1, 1077, 1182.6, 1077
    ' Coordinate rows have gridlines; edge-length column remains continuous.
    For j = 1 To 9
        DrawLine 1138.1, 1077 - j * 6, 1173.1, 1077 - j * 6
    Next j
    DrawLine 1138.1, bottom, 1182.6, bottom
    ' Repeat vertex 1 after vertex 9, as in the VietmapXM example.
    For i = 0 To 9
        k = i Mod 9
        PutText CStr(k + 1), 1140.6, 1074 - i * 6, 1.725, True
        ' Cadastral table convention in supplied example: X=northing, Y=easting.
        ' MDB uses X=easting, Y=northing; only table labels/columns are swapped.
        PutText DecimalComma(p(k).Y, "0.000"), 1150.6, 1074 - i * 6, 1.725, True
        PutText DecimalComma(p(k).X, "0.000"), 1165.6, 1074 - i * 6, 1.725, True
    Next i
    For i = 0 To 8
        ' Halfway between coordinate rows i and i+1.
        PutText DecimalComma(length(i), "0.00"), 1177.85, 1071 - i * 6, 1.725, True
    Next i
End Sub
Private Sub DrawLengthTable(ByRef length() As Double)
    Dim i As Long, j As Long, nextVertex As Long
    PutText U("0039 002E 0020 0043 0068 0069 1EC1 0075 0020 0064 00E0 0069 0020 0063 1EA1 006E 0068 0020 0074 0068 1EED 0061 003A"), 1138.1, 1009, 1.8
    DrawLine 1138.1, 1005, 1138.1, 959
    DrawLine 1151.1, 1005, 1151.1, 959
    DrawLine 1182.6, 1005, 1182.6, 959
    For j = 0 To 10
        DrawLine 1138.1, 1005 - j * 4.6, 1182.6, 1005 - j * 4.6
    Next j
    PutText U("0043 1EA1 006E 0068"), 1144.6, 1002.7, 1.65, True
    PutText U("0043 0068 0069 1EC1 0075 0020 0064 00E0 0069 0020 0028 006D 0029"), 1166.85, 1002.7, 1.65, True
    For i = 0 To 8
        nextVertex = ((i + 1) Mod 9) + 1
        PutText CStr(i + 1) & "-" & CStr(nextVertex), 1144.6, 998.1 - i * 4.6, 1.65, True
        PutText DecimalComma(length(i), "0.00"), 1166.85, 998.1 - i * 4.6, 1.65, True
    Next i
End Sub

Private Function U(ByVal hexCodes As String) As String
    Dim parts As Variant, i As Long
    parts = Split(hexCodes, " ")
    For i = 0 To UBound(parts)
        U = U & ChrW$(CLng("&H" & parts(i)))
    Next i
End Function




Private Sub FindUnicodeTemplate()
    Dim scan As ElementEnumerator, e As Element, txt As TextElement
    Dim criteria As New ElementScanCriteria, i As Long, value As String
    Dim bounds As Range3d
    detailStage = "Find native Vietnamese text template"
    Set unicodeTemplate = Nothing
    criteria.ExcludeAllTypes
    criteria.IncludeType msdElementTypeText
    Set scan = ActiveModelReference.Scan(criteria)
    Do While scan.MoveNext
        Set e = scan.Current
        If Not e Is Nothing Then
            Set txt = e.AsTextElement
            bounds = txt.Range
            value = ""
            If Not (bounds.Low.X >= 1137 And bounds.High.X <= 1184 And bounds.Low.Y >= 955 And bounds.High.Y <= 1111) Then value = txt.Text
            For i = 1 To Len(value)
                If AscW(Mid$(value, i, 1)) > 255 Then
                    Set unicodeTemplate = txt
                    Exit Sub
                End If
            Next i
        End If
    Loop
    Err.Raise 5, , "No native Unicode Vietnamese text found. Stop to avoid corrupted labels."
End Sub



Private Sub FindSolidStyle()
    Dim i As Long, candidate As LineStyle
    Set solidStyle = Nothing
    Set solidStyle = ActiveDesignFile.LineStyles.Find("0", Nothing)
    If Not solidStyle Is Nothing Then Exit Sub
    For i = 1 To ActiveDesignFile.LineStyles.Count
        Set candidate = ActiveDesignFile.LineStyles(i)
        If candidate.Number = 0 Then
            Set solidStyle = candidate
            Exit Sub
        End If
    Next i
    Err.Raise 5, , "Solid line style 0 was not found in this design file."
End Sub

Private Function IsAsciiText(ByVal value As String) As Boolean
    Dim i As Long, code As Long
    IsAsciiText = True
    For i = 1 To Len(value)
        code = AscW(Mid$(value, i, 1))
        If code < 0 Or code > 127 Then
            IsAsciiText = False
            Exit Function
        End If
    Next i
End Function





Private Sub DrawParcelAnnotations(ByRef p() As Point3d)
    Dim i As Long, cx As Double, cy As Double, vx As Double, vy As Double, distance As Double
    Dim center As Point3d, rotation As Matrix3d, vertexRing As EllipseElement
    Dim labelX As Double, labelY As Double
    For i = 0 To 8
        cx = cx + p(i).X / 9
        cy = cy + p(i).Y / 9
    Next i
    rotation = Matrix3dIdentity
    For i = 0 To 8
        vx = p(i).X - cx: vy = p(i).Y - cy
        distance = Sqr(vx * vx + vy * vy)
        If distance < 0.000001 Then distance = 1
        vx = vx / distance: vy = vy / distance
        center = p(i)
        Set vertexRing = CreateEllipseElement2(Nothing, center, 0.55, 0.55, rotation, msdFillModeFilled)
        vertexRing.Color = 0
        Set vertexRing.LineStyle = solidStyle
        vertexRing.LineWeight = 0
        ActiveModelReference.AddElement vertexRing
        labelX = center.X + vx * 3.5
        labelY = center.Y + vy * 3.5
        If i = 0 Then
            labelX = center.X + 4.2
            labelY = center.Y + 1.8
        ElseIf i = 1 Then
            labelX = center.X + 5
            labelY = center.Y - 3
        End If
        PutText CStr(i + 1), labelX, labelY, 2.2, True
    Next i
    ' Neighbor boundary stubs from MDB geometry, scaled direction only.
    DrawLine p(2).X, p(2).Y, p(2).X + (-0.522911884309) * 7, p(2).Y + (-0.852386743942) * 7, 10
    DrawLine p(4).X, p(4).Y, p(4).X + (-0.556031990465) * 7, p(4).Y + (-0.831160890309) * 7, 10
    DrawLine p(0).X, p(0).Y, p(0).X + (0.707202783734) * 7, p(0).Y + (-0.707010765603) * 7, 10
    ' Colored display requested by user; levels follow Appendix 21.
    Dim landCode As String, yellow As Long, green As Long, red As Long
    Dim cadColors As ColorTable
    Set cadColors = ActiveDesignFile.ExtractColorTable
    yellow = cadColors.FindClosestColor(RGB(255, 255, 0))
    green = cadColors.FindClosestColor(RGB(0, 255, 0))
    red = cadColors.FindClosestColor(RGB(255, 0, 0))
    landCode = parcelLandCode
    PutText "1", cx, cy + 2.5, 2.5, True, 13, yellow
    DrawLine cx - 7, cy, cx + 7, cy, 13, green
    PutText "4326,8", cx, cy - 2.5, 2.5, True, 4, red
    If Len(landCode) > 0 Then PutText landCode, cx - 13, cy, 2.5, True, 2, green
    ' Confirmed shared boundaries in MDB: 3-4/4-5 with parcel 3;
    ' 1-2/2-3 with parcel 2002. Unmatched boundaries are left unlabeled.
    PutNeighborLabel p(3), p(4), cx, cy, "3"
    PutNeighborLabel p(1), p(2), cx, cy, "2002"
End Sub

Private Sub PutNeighborLabel(ByRef a As Point3d, ByRef b As Point3d, ByVal cx As Double, ByVal cy As Double, ByVal number As String)
    Dim mx As Double, my As Double, nx As Double, ny As Double, distance As Double
    mx = (a.X + b.X) / 2: my = (a.Y + b.Y) / 2
    nx = -(b.Y - a.Y): ny = b.X - a.X
    distance = Sqr(nx * nx + ny * ny)
    If distance < 0.000001 Then Exit Sub
    nx = nx / distance: ny = ny / distance
    If nx * (mx - cx) + ny * (my - cy) < 0 Then
        nx = -nx: ny = -ny
    End If
    PutText number, mx + nx * 9, my + ny * 9, 1.8, True, 13
End Sub


Private Function DecimalComma(ByVal value As Double, ByVal pattern As String) As String
    DecimalComma = Replace$(Format$(value, pattern), ".", ",")
End Function

Private Function CadLevel(ByVal code As Long) As Level
    Dim result As Level
    Set result = ActiveDesignFile.Levels.FindByCode(code)
    If result Is Nothing Then
        Set result = ActiveDesignFile.AddNewLevel("DC_" & CStr(code))
        result.Code = code
        ActiveDesignFile.RewriteLevels
    End If
    Set CadLevel = result
End Function



Private Sub FillParcelHeader()
    Dim criteria As New ElementScanCriteria, scan As ElementEnumerator
    Dim e As Element, t As TextElement, r As Range3d, value As String, updated As String
    detailStage = "Fill parcel attributes on output copy"
    parcelLandCode = Trim$(InputBox("Land-use code (MDB field is blank). Leave blank if unknown:", "Parcel 1 / sheet 100"))
    ' VBA InputBox cannot reliably round-trip Vietnamese Unicode.
    parcelAddress = U("006B 0068 00F3 006D 0020 0035 002C 0020 0070 0068 01B0 1EDD 006E 0067 0020 004E 0067 00E3 0020 004E 0061 006D 002C 0020 0074 0068 00E0 006E 0068 0020 0070 0068 1ED1 0020 0043 1EA7 006E 0020 0054 0068 01A1")
    If Len(Trim$(parcelAddress)) = 0 Then parcelAddress = U("006B 0068 00F3 006D 0020 0035")
    criteria.ExcludeAllTypes
    criteria.IncludeType msdElementTypeText
    Set scan = ActiveModelReference.Scan(criteria)
    Do While scan.MoveNext
        Set e = scan.Current
        If Not e Is Nothing Then
            Set t = e.AsTextElement
            r = t.Range
            If r.Low.X >= 979 And r.High.X <= 1189 And r.Low.Y >= 881 And r.High.Y <= 1172 Then
                value = t.Text: updated = value
                Select Case Trim$(value)
                    Case "ShThua": updated = "1"
                    Case "ToBd": updated = "100"
                    Case "TenChu": updated = U("004E 0067 0075 0079 1EC5 006E 0020 0056 0103 006E 0020 0054 006F 00E0 006E")
                    Case "DienTich": updated = "4326,8"
                    Case "Mdsd": updated = parcelLandCode
                    Case "PhuongXa": updated = ""
                    Case "BB 908397": updated = ""
                    Case U("0043 1ED5 0020 0054 0068 00E0 006E 0068 0020 0043 1EE5 0069 0020 0045 006D"): updated = ""
                End Select
                If InStr(1, value, U("0110 1ECB 0061 0020 0063 0068 1EC9 0020 0074 0068 1EED 0061 0020 0111 1EA5 0074 003A"), vbBinaryCompare) = 1 Then updated = U("0110 1ECB 0061 0020 0063 0068 1EC9 0020 0074 0068 1EED 0061 0020 0111 1EA5 0074 003A") & " " & parcelAddress
                If updated <> value Then
                    t.Text = updated
                    t.Rewrite
                End If
            End If
        End If
    Loop
End Sub
