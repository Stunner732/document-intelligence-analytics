[CmdletBinding()]
param(
    [string]$OutputPath = (Join-Path $PSScriptRoot '..\data\raw\BPI_Challenge_2017.xes.gz')
)

$sourceUrl = 'https://ndownloader.figshare.com/files/24044117'
$expectedMd5 = '10b37a2f78e870d78406198403ff13d2'

if (Test-Path -LiteralPath $OutputPath) {
    throw "Refusing to overwrite existing file: $OutputPath"
}

$destinationDirectory = Split-Path -Parent $OutputPath
New-Item -ItemType Directory -Force -Path $destinationDirectory | Out-Null
Invoke-WebRequest -Uri $sourceUrl -OutFile $OutputPath

$actualMd5 = (Get-FileHash -LiteralPath $OutputPath -Algorithm MD5).Hash.ToLowerInvariant()
if ($actualMd5 -ne $expectedMd5) {
    Remove-Item -LiteralPath $OutputPath -Force
    throw "Checksum verification failed. Expected $expectedMd5; received $actualMd5."
}

Write-Output "Downloaded and verified: $OutputPath"
