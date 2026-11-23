$ErrorActionPreference = "Stop"

$docxPath = Join-Path $PSScriptRoot "Laporan_Pengujian_Klasifikasi_Aktivitas_ESP32.docx"
$pdfPath = Join-Path $PSScriptRoot "Laporan_Pengujian_Klasifikasi_Aktivitas_ESP32.pdf"

Write-Host "Opening Word application..."
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$doc = $null

try {
    Write-Host "Opening document: $docxPath"
    $doc = $word.Documents.Open($docxPath)
    
    # 17 = wdFormatPDF
    Write-Host "Exporting to PDF: $pdfPath"
    $doc.ExportAsFixedFormat([string]$pdfPath, 17)
    
    Write-Host "PDF export successful: $pdfPath"
}
finally {
    if ($null -ne $doc) { $doc.Close(0) }
    $word.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
}
