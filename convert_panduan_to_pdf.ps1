$ErrorActionPreference = "Stop"

$docxPath = [System.IO.Path]::GetFullPath("TUGAS BESAR\PANDUAN_STEP_BY_STEP_PERCOBAAN.docx")
$pdfPath = [System.IO.Path]::GetFullPath("TUGAS BESAR\PANDUAN_STEP_BY_STEP_PERCOBAAN.pdf")

Write-Host "Opening Word application..."
$word = New-Object -ComObject Word.Application
$word.Visible = $false

try {
    Write-Host "Opening document: $docxPath"
    $doc = $word.Documents.Open($docxPath)
    
    # 17 = wdFormatPDF
    Write-Host "Exporting to PDF: $pdfPath"
    $doc.SaveAs([ref]$pdfPath, [ref]17)
    
    $doc.Close()
    Write-Host "PDF export successful: $pdfPath"
}
finally {
    $word.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
}
