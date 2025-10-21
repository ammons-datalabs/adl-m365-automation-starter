# Invoice Processing PowerShell Script
# Processes invoices from a folder and logs results

param(
    [Parameter(Mandatory=$true)]
    [string]$InvoiceFolder,

    [Parameter(Mandatory=$false)]
    [string]$ApiBaseUrl = "https://asp-adl-m365-us-baaydcahbudkeef8.westus3-01.azurewebsites.net",

    [Parameter(Mandatory=$false)]
    [double]$ConfidenceThreshold = 0.85,

    [Parameter(Mandatory=$false)]
    [string]$LogFile = "invoice-processing-log.csv"
)

# Initialize log file
if (!(Test-Path $LogFile)) {
    "Timestamp,FileName,Status,Vendor,InvoiceNumber,Total,Currency,Confidence,ApprovalType" | Out-File $LogFile
}

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "Invoice Processing Script" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "Folder: $InvoiceFolder"
Write-Host "API: $ApiBaseUrl"
Write-Host "Confidence Threshold: $ConfidenceThreshold"
Write-Host ""

# Get all PDF files
$invoices = Get-ChildItem -Path $InvoiceFolder -Filter "*.pdf"

if ($invoices.Count -eq 0) {
    Write-Host "No PDF files found in $InvoiceFolder" -ForegroundColor Yellow
    exit
}

Write-Host "Found $($invoices.Count) invoice(s) to process" -ForegroundColor Green
Write-Host ""

$processed = 0
$autoApproved = 0
$manualReview = 0
$errors = 0

foreach ($invoice in $invoices) {
    Write-Host "Processing: $($invoice.Name)" -ForegroundColor White

    try {
        # Read file content
        $fileBytes = [System.IO.File]::ReadAllBytes($invoice.FullName)
        $fileContent = [System.Convert]::ToBase64String($fileBytes)

        # Create multipart form data
        $boundary = [System.Guid]::NewGuid().ToString()
        $LF = "`r`n"

        $bodyLines = (
            "--$boundary",
            "Content-Disposition: form-data; name=`"file`"; filename=`"$($invoice.Name)`"",
            "Content-Type: application/pdf",
            "",
            [System.Text.Encoding]::GetEncoding("ISO-8859-1").GetString([System.Convert]::FromBase64String($fileContent)),
            "--$boundary--"
        ) -join $LF

        # Call API
        $uri = "$ApiBaseUrl/invoices/process?confidence_threshold=$ConfidenceThreshold"
        $response = Invoke-RestMethod -Uri $uri `
            -Method Post `
            -ContentType "multipart/form-data; boundary=$boundary" `
            -Body $bodyLines `
            -TimeoutSec 120

        # Parse response
        $status = $response.status
        $invoiceData = $response.invoice_data

        if ($status -eq "auto_approved") {
            Write-Host "  ✅ AUTO-APPROVED" -ForegroundColor Green
            $autoApproved++
            $approvalType = "AI Auto-Approved"
        } else {
            Write-Host "  📧 SENT TO TEAMS" -ForegroundColor Yellow
            $manualReview++
            $approvalType = "Manual Review"
        }

        Write-Host "  Vendor: $($invoiceData.vendor)"
        Write-Host "  Invoice #: $($invoiceData.invoice_number)"
        Write-Host "  Total: $($invoiceData.currency) $($invoiceData.total)"
        Write-Host "  Confidence: $([math]::Round($invoiceData.confidence * 100, 2))%"
        Write-Host ""

        # Log to CSV
        $logEntry = @(
            (Get-Date -Format "yyyy-MM-dd HH:mm:ss"),
            $invoice.Name,
            $status,
            $invoiceData.vendor,
            $invoiceData.invoice_number,
            $invoiceData.total,
            $invoiceData.currency,
            $invoiceData.confidence,
            $approvalType
        ) -join ","

        $logEntry | Out-File $LogFile -Append

        $processed++

    } catch {
        Write-Host "  ❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host ""
        $errors++

        # Log error
        $errorEntry = @(
            (Get-Date -Format "yyyy-MM-dd HH:mm:ss"),
            $invoice.Name,
            "ERROR",
            "",
            "",
            "",
            "",
            "",
            $_.Exception.Message
        ) -join ","

        $errorEntry | Out-File $LogFile -Append
    }
}

# Summary
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "Processing Complete!" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "Total Processed: $processed" -ForegroundColor White
Write-Host "Auto-Approved: $autoApproved" -ForegroundColor Green
Write-Host "Manual Review: $manualReview" -ForegroundColor Yellow
Write-Host "Errors: $errors" -ForegroundColor Red
Write-Host ""
Write-Host "Log file: $LogFile" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan
