$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\transcription_worker")
Set-Location $root

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

if (-not $env:PORT) { $env:PORT = "8081" }
if (-not $env:WHISPER_MODEL_SIZE) { $env:WHISPER_MODEL_SIZE = "medium" }
if (-not $env:WHISPER_DEVICE) { $env:WHISPER_DEVICE = "cpu" }
if (-not $env:WHISPER_COMPUTE_TYPE) { $env:WHISPER_COMPUTE_TYPE = "int8" }

& .\.venv\Scripts\python.exe app.py
