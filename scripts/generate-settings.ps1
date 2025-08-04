# PowerShell script to generate local.settings.json

# Get values from azd environment
Write-Host "Getting environment values from azd..."
$azdValues = azd env get-values
$COSMOS_ENDPOINT = ($azdValues | Select-String 'COSMOS_ENDPOINT="(.*?)"').Matches.Groups[1].Value
$AZURE_OPENAI_ENDPOINT = ($azdValues | Select-String 'AZURE_OPENAI_ENDPOINT="(.*?)"').Matches.Groups[1].Value
$COSMOSDB_DATABASE_NAME = ($azdValues | Select-String 'COSMOSDB_DATABASE_NAME="(.*?)"').Matches.Groups[1].Value
$COSMOSDB_CONTAINER_NAME = ($azdValues | Select-String 'COSMOSDB_CONTAINER_NAME="(.*?)"').Matches.Groups[1].Value

# Create the JSON content
$jsonContent = @"
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsSecretStorageType": "files",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "PYTHON_ENABLE_WORKER_EXTENSIONS": "True",
    "COSMOSDB_DATABASE_NAME": "$COSMOSDB_DATABASE_NAME",
    "COSMOSDB_CONTAINER_NAME": "$COSMOSDB_CONTAINER_NAME",
    "OPENAI_MODEL_NAME": "gpt-4o",
    "COSMOS_ENDPOINT": "$COSMOS_ENDPOINT",
    "AZURE_OPENAI_ENDPOINT": "$AZURE_OPENAI_ENDPOINT"
  }
}
"@

# Write content to local.settings.json
$settingsPath = Join-Path (Get-Location) "src" "local.settings.json"
$jsonContent | Out-File -FilePath $settingsPath -Encoding utf8

Write-Host "local.settings.json generated successfully in src directory!"