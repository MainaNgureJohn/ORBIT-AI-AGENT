$ErrorActionPreference = "Stop"

$apiKeySecure = Read-Host "Binance read-only API key" -AsSecureString
$apiSecretSecure = Read-Host "Binance API secret" -AsSecureString
$apiKey = [System.Net.NetworkCredential]::new("", $apiKeySecure).Password
$apiSecret = [System.Net.NetworkCredential]::new("", $apiSecretSecure).Password
$useGroq = Read-Host "Enable Groq portfolio guidance? (y/N)"
$groqKey = ""
if ($useGroq -match "^(y|yes)$") {
    $groqKeySecure = Read-Host "Groq API key" -AsSecureString
    $groqKey = [System.Net.NetworkCredential]::new("", $groqKeySecure).Password
    if ([string]::IsNullOrWhiteSpace($groqKey)) { throw "Groq was selected but no key was provided. Nothing was stored." }
}

if ([string]::IsNullOrWhiteSpace($apiKey) -or [string]::IsNullOrWhiteSpace($apiSecret)) {
    throw "Both credentials are required. Nothing was stored."
}

Push-Location $PSScriptRoot
try {
    $env:APP_MODE = "binance_account"
    $env:BINANCE_ACCOUNT_ACCESS = "read_only"
    $env:LLM_PROVIDER = "disabled"
    $env:BINANCE_API_KEY = $apiKey
    $env:BINANCE_API_SECRET = $apiSecret
    if ($groqKey) {
        $env:LLM_PROVIDER = "groq"
        $env:GROQ_API_KEY = $groqKey
    }
    Write-Host "Starting ORBIT in verified read-only account mode on http://localhost:8000"
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
    if ($LASTEXITCODE -ne 0) {
        throw "The ORBIT backend exited with code $LASTEXITCODE."
    }
}
catch {
    Write-Host "ORBIT could not stay running: $($_.Exception.Message)" -ForegroundColor Red
    Read-Host "Press Enter after noting this safe error"
}
finally {
    Remove-Item Env:BINANCE_API_KEY -ErrorAction SilentlyContinue
    Remove-Item Env:BINANCE_API_SECRET -ErrorAction SilentlyContinue
    Remove-Item Env:APP_MODE -ErrorAction SilentlyContinue
    Remove-Item Env:BINANCE_ACCOUNT_ACCESS -ErrorAction SilentlyContinue
    Remove-Item Env:LLM_PROVIDER -ErrorAction SilentlyContinue
    Remove-Item Env:GROQ_API_KEY -ErrorAction SilentlyContinue
    $apiKey = $null
    $apiSecret = $null
    $groqKey = $null
    Pop-Location
}
