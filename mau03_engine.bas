Private Sub ExportMau03Parcel()
    On Error GoTo Failed
    Dim fs As Object, target As String, d As DesignFile, original() As Point3d, display() As Point3d
    Dim xmin As Double, xmax As Double, ymin As Double, ymax As Double, w As Double, h As Double
    Dim dx As Double, dy As Double, i As Long, n As Long, shape As ShapeElement
    Dim shapeFactor As Double
    tableOffset = 0: Set labelParts = Nothing
    ParsePoints CStr(parcelRow(6)), original
    n = UBound(original) + 1
    xmin = original(0).X: xmax = xmin: ymin = original(0).Y: ymax = ymin
    For i = 1 To n - 1
        If original(i).X < xmin Then xmin = original(i).X
        If original(i).X > xmax Then xmax = original(i).X
        If original(i).Y < ymin Then ymin = original(i).Y
        If original(i).Y > ymax Then ymax = original(i).Y
    Next i
    w = 107.797: h = 106.321
    If xmax - xmin < 0.001 Or ymax - ymin < 0.001 Then Err.Raise 5, , "Degenerate parcel bounds."
    shapeFactor = 1
    If (w - 40) / (xmax - xmin) < shapeFactor Then shapeFactor = (w - 40) / (xmax - xmin)
    If (h - 50) / (ymax - ymin) < shapeFactor Then shapeFactor = (h - 50) / (ymax - ymin)
    ' Uniform similarity transform: the same factor on X and Y preserves angles.
    ' Coordinates and edge lengths in the table always come from the original.
    dx = 0: dy = 0
    diagramRight = 1005.612 + w: diagramBottom = 1080.817 - h
    parcelLandCode = CStr(parcelRow(5)): parcelAddress = CStr(parcelRow(4))
    Set fs = CreateObject("Scripting.FileSystemObject")
    target = @OUTPUT@ & "\Mau03CLBD_To" & CStr(parcelRow(0)) & "_Thua" & CStr(parcelRow(1)) & "_ID" & CStr(parcelRow(9)) & "_" & Format$(Now, "yyyymmdd_hhnnss") & ".dgn"
    If fs.FileExists(target) Then Err.Raise 5, , "Output already exists."
    fs.CopyFile @MAU03@, target, False
    Set d = OpenDesignFile(fs.GetFile(target).ShortPath, False)
    If LCase$(fs.GetFile(ActiveDesignFile.FullName).ShortPath) <> LCase$(fs.GetFile(target).ShortPath) Then Err.Raise 5, , "New Mau03 output is not active."
    WhiteOnDarkBackground
    FindSolidStyle
    FindUnicodeTemplate
    Set unicodeTemplate = unicodeTemplate.Clone.AsTextElement
    RemoveEmptyMau03Tables n
    FillMau03Template original, dx, dy
    ReDim display(0 To n - 1)
    For i = 0 To n - 1
        display(i) = Point3dFromXYZ(1005.612 + w / 2 + (original(i).X - (xmin + xmax) / 2) * shapeFactor, 1080.817 - h / 2 + (original(i).Y - (ymin + ymax) / 2) * shapeFactor, 0)
    Next i
    Set shape = CreateShapeElement1(Nothing, display, msdFillModeNotFilled)
    Set shape.Level = CadLevel(10): Set shape.LineStyle = solidStyle
    shape.Color = 0: shape.LineWeight = 0
    ActiveModelReference.AddElement shape
    DrawAnnotations display
    RestoreWorldCoordinates original, display, shapeFactor
    DrawInteriorResults original, False
    AssertWorldParcel original
    ActiveDesignFile.Save
    PublishResult "OK", target
    Exit Sub
Failed:
    tableOffset = 0: Set labelParts = Nothing
    PublishResult "ERROR", "Mau03: " & Err.Description & vbCrLf & target
End Sub

Private Sub RemoveEmptyMau03Tables(ByVal vertexCount As Long)
    Dim criteria As New ElementScanCriteria, ee As ElementEnumerator, e As Element, r As Range3d
    Dim regex As Object, matches As Object, match As Object, index As Long, group As Long, i As Long
    Dim left(0 To 3) As Double, right(0 To 3) As Double, bottom(0 To 3) As Double, top(0 To 3) As Double
    Dim found(0 To 3) As Boolean, used(0 To 3) As Boolean, pending As New Collection
    Set regex = CreateObject("VBScript.RegExp")
    regex.Pattern = "\[(ttt|tdX|tdY|tdKC)\.([0-9]+)\]"
    criteria.ExcludeNonGraphical
    Set ee = ActiveModelReference.Scan(criteria)
    Do While ee.MoveNext
        Set e = ee.Current
        If e.IsTextElement Then
            Set matches = regex.Execute(e.AsTextElement.Text)
            If matches.Count > 0 Then
                Set match = matches(0): index = CLng(match.SubMatches(1)): group = -1
                If index >= 17 And index <= 53 Then group = 0
                If index >= 54 And index <= 90 Then group = 1
                If index >= 91 And index <= 127 Then group = 2
                If index >= 128 And index <= 164 Then group = 3
                If group >= 0 Then
                    r = e.Range
                    If Not found(group) Then
                        left(group) = r.Low.X: right(group) = r.High.X
                        bottom(group) = r.Low.Y: top(group) = r.High.Y
                        found(group) = True
                    End If
                    If r.Low.X < left(group) Then left(group) = r.Low.X
                    If r.High.X > right(group) Then right(group) = r.High.X
                    If r.Low.Y < bottom(group) Then bottom(group) = r.Low.Y
                    If r.High.Y > top(group) Then top(group) = r.High.Y
                    If CStr(match.SubMatches(0)) = "tdKC" Then
                        If index <= vertexCount Then used(group) = True
                    Else
                        If index <= vertexCount + 1 Then used(group) = True
                    End If
                End If
            End If
        End If
    Loop
    Set ee = ActiveModelReference.Scan(criteria)
    Do While ee.MoveNext
        Set e = ee.Current: r = e.Range
        For i = 0 To 3
            If found(i) And Not used(i) Then
                If r.Low.X >= left(i) - 10 And r.High.X <= right(i) + 4 And r.Low.Y >= bottom(i) - 6 And r.High.Y <= top(i) + 15 Then
                    pending.Add e: Exit For
                End If
            End If
        Next i
    Loop
    For i = 1 To pending.Count
        Set e = pending(i): ActiveModelReference.RemoveElement e
    Next i
End Sub

Private Sub FillMau03Template(ByRef p() As Point3d, ByVal dx As Double, ByVal dy As Double)
    Dim criteria As New ElementScanCriteria, ee As ElementEnumerator, e As Element, t As TextElement, r As Range3d
    Dim pending As New Collection, additions As New Collection, regex As Object, matches As Object, match As Object
    Dim fresh As TextElement
    Dim n As Long, index As Long, k As Long, j As Long, i As Long, maxIndex As Long
    Dim requiredX As Double, keepRight As Double, text As String, updated As String, prefix As String
    Dim remove As Boolean, style As TextStyle, available As Double
    n = UBound(p) + 1: requiredX = 1190
    Set regex = CreateObject("VBScript.RegExp")
    regex.Pattern = "\[(ttt|tdX|tdY|tdKC)\.([0-9]+)\]"
    regex.Global = False
    criteria.ExcludeNonGraphical
    Set ee = ActiveModelReference.Scan(criteria)
    Do While ee.MoveNext
        Set e = ee.Current
        If e.IsTextElement Then
            Set matches = regex.Execute(e.AsTextElement.Text)
            If matches.Count > 0 Then
                r = e.Range
                Set match = matches(0): index = CLng(match.SubMatches(1))
                If index > maxIndex Then maxIndex = index
                If index <= n + 1 Then
                    r = e.Range
                    If r.Low.X > requiredX Then requiredX = r.Low.X
                End If
            End If
        End If
    Loop
    If n + 1 > maxIndex Then Err.Raise 5, , "This VietMap template has only " & CStr(maxIndex) & " vertex slots."
    keepRight = 1203
    Set ee = ActiveModelReference.Scan(criteria)
    Do While ee.MoveNext
        Set e = ee.Current: r = e.Range: remove = False
        If r.Low.X < 990 Or r.High.X > keepRight Or r.Low.Y < 914 Or r.High.Y > 1207 Then
            ' Supplement tables that contain data must still be filled; other
            ' objects outside the main page remain exactly as in the template.
            If Not e.IsTextElement Then GoTo NextMau03Element
            Set matches = regex.Execute(e.AsTextElement.Text)
            If matches.Count = 0 Then GoTo NextMau03Element
        End If
        ' Replace only the first-page outer border and diagram border.
        If e.IsShapeElement Then
            If Abs(r.Low.X - 992.043) < 0.1 And Abs(r.High.X - 1201.714) < 0.1 Then remove = True
            If Abs(r.Low.X - 1005.612) < 0.1 And Abs(r.High.X - 1113.409) < 0.1 Then remove = True
        End If
        If Not remove And e.IsTextElement Then
            Set t = e.AsTextElement: text = Trim$(t.Text): updated = text
            If r.Low.Y >= 1175 And InStr(1, text, U("004E 0067 00E3 0020 004E 0103 006D"), vbTextCompare) > 0 Then
                t.Move Point3dFromXYZ(1196 - r.High.X, 0, 0)
                t.Rewrite
            End If
            Set matches = regex.Execute(text)
            If matches.Count > 0 Then
                Set match = matches(0): prefix = CStr(match.SubMatches(0)): index = CLng(match.SubMatches(1))
                updated = ""
                If index <= n + 1 Then
                    k = (index - 1) Mod n: j = (k + 1) Mod n
                    Select Case prefix
                        Case "ttt": updated = CStr(k + 1)
                        Case "tdX": updated = DecimalComma(p(k).Y, "0.000")
                        Case "tdY": updated = DecimalComma(p(k).X, "0.000")
                        Case "tdKC"
                            If index <= n Then updated = DecimalComma(Sqr((p(j).X - p(k).X) ^ 2 + (p(j).Y - p(k).Y) ^ 2), "0.00")
                    End Select
                End If
            Else
                Select Case text
                    Case "ShThua": updated = CStr(parcelRow(1))
                    Case "ToBd": updated = CStr(parcelRow(0))
                    Case "TenChu": updated = CStr(parcelRow(3))
                    Case "Mdsd": updated = parcelLandCode
                    Case "XuDong, PhuongXa, TinhThanh": updated = parcelAddress
                    Case "DiaChi, PhuongXa, TinhThanh"
                        updated = ""
                        If UBound(parcelRow) >= 10 Then updated = CStr(parcelRow(10))
                    Case "1:TyLe": updated = ""
                    Case "00.0": updated = ""
                End Select
                If InStr(1, text, "DienTich", vbBinaryCompare) > 0 Then updated = Replace(text, "DienTich", DecimalComma(Val(parcelRow(2)), "0.0"))
                ' These sample assertions are not facts about a newly selected parcel.
                If text = U("004B 0068 00F4 006E 0067 0020 0074 0068 0061 0079 0020 0111 1ED5 0069") Then updated = ""
                If InStr(1, text, U("002D 0020 0044 0069 1EC7 006E 0020 0074 00ED 0063 0068 0020 0067 0069 1EA3 006D 003A"), vbTextCompare) = 1 Then updated = ""
            End If
            If updated <> text Then
                ' Recreate fields: VietMap text may retain legacy data-entry
                ' regions when Text is overwritten in place.
                remove = True
                If Len(updated) > 0 Then
                    Set fresh = CreateTextElement1(unicodeTemplate, updated, t.Origin, Matrix3dIdentity)
                    Set style = t.TextStyle
                    If IsAsciiText(updated) Then Set style.Font = ActiveDesignFile.Fonts("Arial")
                    Set fresh.TextStyle = style
                    fresh.Color = t.Color: fresh.LineWeight = t.LineWeight
                    Set fresh.Level = t.Level: Set fresh.LineStyle = solidStyle
                    available = 1200 - r.Low.X
                    If r.Low.X < 1200 And available > 0 Then
                        If fresh.Range.High.X - fresh.Range.Low.X > available Then
                            style.Width = style.Width * available / (fresh.Range.High.X - fresh.Range.Low.X)
                            Set fresh.TextStyle = style
                        End If
                    End If
                    If r.High.Y < 989 And r.Low.X < 1203 Then fresh.Move Point3dFromXYZ(0, -dy, 0)
                    If r.Low.X >= 1119 And r.Low.X < 1203 And r.High.Y < 1095 Then fresh.Move Point3dFromXYZ(dx, 0, 0)
                    additions.Add fresh
                End If
            End If
        End If
        If remove Then
            pending.Add e
        Else
            If r.High.Y < 989 And r.Low.X < 1203 Then
                e.Move Point3dFromXYZ(0, -dy, 0): e.Rewrite
            End If
            If r.Low.X >= 1119 And r.Low.X < 1203 And r.High.Y < 1095 Then
                e.Move Point3dFromXYZ(dx, 0, 0): e.Rewrite
            End If
        End If
NextMau03Element:
    Loop
    For i = 1 To pending.Count
        Set e = pending(i): ActiveModelReference.RemoveElement e
    Next i
    For i = 1 To additions.Count
        Set e = additions(i): ActiveModelReference.AddElement e
    Next i
    DrawLine 1005.612, diagramBottom, diagramRight, diagramBottom, 63
    DrawLine diagramRight, diagramBottom, diagramRight, 1080.817, 63
    DrawLine diagramRight, 1080.817, 1005.612, 1080.817, 63
    DrawLine 1005.612, 1080.817, 1005.612, diagramBottom, 63
    DrawLine 992.043, 915.11 - dy, 1201.714 + dx, 915.11 - dy, 63
    DrawLine 1201.714 + dx, 915.11 - dy, 1201.714 + dx, 1205.11, 63
    DrawLine 1201.714 + dx, 1205.11, 992.043, 1205.11, 63
    DrawLine 992.043, 1205.11, 992.043, 915.11 - dy, 63
End Sub
