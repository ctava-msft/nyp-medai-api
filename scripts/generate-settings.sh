#!/bin/bash

# Get values from azd environment
echo "Getting environment values from azd..."
COSMOS_ENDPOINT=$(azd env get-values | grep COSMOS_ENDPOINT | cut -d'"' -f2)
AZURE_OPENAI_ENDPOINT=$(azd env get-values | grep AZURE_OPENAI_ENDPOINT | cut -d'"' -f2)
COSMOSDB_DATABASE_NAME=$(azd env get-values | grep COSMOSDB_DATABASE_NAME | cut -d'"' -f2)
COSMOSDB_CONTAINER_NAME=$(azd env get-values | grep COSMOSDB_CONTAINER_NAME | cut -d'"' -f2)

# Create or update local.settings.json
echo "Generating local.settings.json in src directory..."
cat > src/local.settings.json << EOF
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
EOF

echo "local.settings.json generated successfully in src directory!"