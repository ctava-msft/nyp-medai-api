<!--
---
name: Medical Data Text-to-SQL Service with MCP Tools
description: A serverless medical data natural language query service using Azure Functions, Azure OpenAI, Cosmos DB, and API Management.
page_type: sample
languages:
- python
- bicep
- azdeveloper
products:
- azure-functions
- azure-openai
- azure-cosmos-db
- azure-api-management
- azure-ai-services
urlFragment: medai-text-to-sql
---
-->

<p align="center">
  <b>MedAI Text-to-SQL · Intelligent Medical Data Query Service with MCP Tools</b>
</p>

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://github.com/codespaces/new?hide_repo_select=true&ref=main&repo=ctava-msft/ct-medimageinsights&machine=basicLinux32gb&devcontainer_path=.devcontainer%2Fdevcontainer.json)
[![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/ctava-msft/ct-medimageinsights)

MedAI Text-to-SQL is an **Azure Functions**–based reference application that converts natural language queries into SQL and executes them against medical triplet data. The service exposes functionality through **MCP (Model Context Protocol) tools** consumable by GitHub Copilot Chat and other MCP‑aware clients, and provides a secure API gateway through **Azure API Management**.

* **Natural Language to SQL** – converts plain English queries to SQL using **Azure OpenAI GPT-4**
* **Medical Data Storage** – persists medical triplet data (MEDCode, Slot, Value) in **Cosmos DB**
* **Secure API Gateway** – exposes endpoints through **Azure API Management** with rate limiting and authentication
* **MCP Protocol Support** – integrates with GitHub Copilot and other AI assistants as interactive tools
* **Healthcare Compliance** – designed with security best practices for medical data handling
* **Sample Data Included** – automatically loads sample medical data on startup

The project ships with reproducible **azd** infrastructure, so `azd up` will stand up the entire stack – Functions, Cosmos DB, Azure OpenAI, and API Management – in a single command.

## Features

* **Text-to-SQL Conversion** – convert natural language to SQL using GPT-4
* **Medical Data Query** – query medical triplet data with natural language interface
* **Sample Data Endpoints** – retrieve sample medical data for testing
* **Secure API Gateway** – Azure API Management with rate limiting and authentication
* **MCP Protocol Support** – integrate with GitHub Copilot and other AI assistants
* **Auto Sample Data** – automatically loads sample data on first deployment
* **Comprehensive Logging** – Application Insights integration with detailed diagnostics

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/text-to-sql` | POST | Convert natural language to SQL and execute query |
| `/api/sample-data` | GET | Retrieve sample medical data records |
| `/api/medical-data` | POST | Upload new medical data records |  
| `/api/health` | GET | Health check endpoint |

### MCP Tools

| Tool Name | Purpose |
|-----------|---------|
| `text_to_sql` | Convert natural language queries to SQL and execute against medical data |

## Getting Started

### Prerequisites

* Azure subscription with appropriate permissions
* Azure CLI (`az`) installed
* Azure Developer CLI (`azd`) installed
* Python 3.11+ for local development

### Quick Deployment

```bash
# Clone the repository
git clone <repository-url>
cd nyp-medai-api

# Login to Azure
azd auth login

# Deploy everything
azd up
```

The deployment will:
1. Create all Azure resources (Functions, Cosmos DB, OpenAI, API Management)
2. Deploy the function app code
3. Configure API Management with proper endpoints
4. Load sample medical data automatically

### Local Development

```bash
# Install dependencies
pip install -r src/requirements.txt

# Generate local settings from deployed resources
./scripts/generate-settings.sh

# Run locally
cd src
func start
```

## Usage Examples

### Via HTTP API

```bash
# Query medical data with natural language
curl -X POST "https://your-function-app.azurewebsites.net/api/text-to-sql" \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me all blood pressure measurements"}'

# Get sample data
curl "https://your-function-app.azurewebsites.net/api/sample-data?limit=5"

# Health check
curl "https://your-function-app.azurewebsites.net/api/health"
```

1. Install required packages:

    ```shell
    python -m venv .venv 
    .\.venv\Scripts\activate
    ```

    ```shell
    pip install -r requirements.txt
    ```

### Via API Management

```bash
# Query through APIM gateway
curl -X POST "https://your-apim.azure-api.net/medical/text-to-sql" \
  -H "Content-Type: application/json" \
  -H "Ocp-Apim-Subscription-Key: YOUR-KEY" \
  -d '{"query": "Find all records for MEDCode 1302"}'
```

### Sample Natural Language Queries

- "Show me all records for MEDCode 1302"
- "Find measurements containing blood pressure"  
- "Get all records where the slot is 150"
- "Show me sodium level measurements"
- "Find all heart rate records"

## Architecture

The solution uses a serverless architecture with these Azure services:

- **Azure Functions** - Serverless compute hosting the API endpoints
- **Azure Cosmos DB** - NoSQL database storing medical triplet data
- **Azure OpenAI** - GPT-4 model for natural language to SQL conversion
- **Azure API Management** - Secure API gateway with rate limiting
- **Application Insights** - Monitoring, logging, and diagnostics

## Sample Data Structure

The system works with medical triplet data:

```json
{
  "id": "unique-identifier",
  "MEDCode": 1302,
  "Slot": 150, 
  "Value": "Blood pressure systolic",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

Sample data is automatically loaded including:
- Blood pressure measurements
- Heart rate data
- Temperature readings
- Sodium levels
- Glucose measurements

## Security & Compliance

- **Managed Identity** authentication between all Azure services
- **HTTPS only** communication
- **API Management** gateway with subscription keys and rate limiting
- **Application Insights** for comprehensive monitoring and audit trails
- **Network isolation** ready (Private Endpoints can be enabled)

### Required Azure Role Assignments

The managed identity requires these permissions:
* **Cosmos DB Data Contributor** - for reading/writing medical data
* **Storage Blob Data Owner and Queue Data Contributor** - for Azure Functions storage
* **Application Insights Monitoring Metrics Publisher** - for telemetry
* **Azure AI Project Developer** - for AI services access

For production deployments, we recommend:
* Restrict inbound traffic with Private Endpoints + VNet integration
* Enable network security features like service endpoints and firewall rules

## Monitoring & Diagnostics

The solution includes comprehensive monitoring:

- **Application Insights** integration for all functions
- **Structured logging** throughout the application
- **Health check endpoint** for service monitoring
- **Custom metrics** for query performance tracking
- **Distributed tracing** for request correlation

## Resources

* Blog – *Build AI agent tools using Remote MCP with Azure Functions* ([Tech Community](https://techcommunity.microsoft.com/blog/appsonazureblog/build-ai-agent-tools-using-remote-mcp-with-azure-functions/4401059))
* Model Context Protocol spec – [https://aka.ms/mcp](https://aka.ms/mcp)
* Azure Functions Remote MCP docs – [https://aka.ms/azure-functions-mcp](https://aka.ms/azure-functions-mcp)
* Develop Python apps for Azure AI – [https://learn.microsoft.com/azure/developer/python/azure-ai-for-python-developers](https://learn.microsoft.com/azure/developer/python/azure-ai-for-python-developers)

## Contributing

Standard **fork → branch → PR** workflow. Use *Conventional Commits* (`feat:`, `fix:`) in commit messages.

## License

MIT © Microsoft Corporation
---

## Contributing

Standard **fork → branch → PR** workflow. Use *Conventional Commits* (`feat:`, `fix:`) in commit messages.

---

## License

MIT © Microsoft Corporation
