# =============================================================================
# MEDICAL DATA TEXT-TO-SQL AGENT WITH MCP PROTOCOL SUPPORT
# =============================================================================
#
# This application provides a text-to-SQL agent tool for medical data analysis built with:
#
# 1. Azure Functions - Serverless compute for text-to-SQL conversion
#    - HTTP triggers - Standard RESTful API endpoints accessible over HTTP
#    - MCP triggers - Model Context Protocol for AI agent integration (e.g., GitHub Copilot)
#
# 2. Azure Cosmos DB - NoSQL database for medical data storage
#    - Stores medical triplet data (MEDCode, Slot, Value)
#    - Enables SQL-like queries through the Cosmos DB SQL API
#
# 3. Azure OpenAI - Provides AI models for natural language understanding
#    - Converts natural language queries to SQL
#    - Uses GPT-4 for intelligent query generation
#
# 4. Azure API Management - Secure API gateway
#    - Rate limiting, authentication, and monitoring
#    - Centralizes API management and security policies
#
# The application provides both HTTP endpoints and MCP tools for natural language
# to SQL conversion, enabling AI assistants to query medical data using natural language.

import json
import logging
import os
import re
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

import azure.functions as func
from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey, exceptions
from azure.identity.aio import DefaultAzureCredential
from openai import AsyncAzureOpenAI

# Initialize the Azure Functions app
app = func.FunctionApp()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS AND CONFIGURATION
# =============================================================================

# Environment variables for Azure services
COSMOS_ENDPOINT_ENV = "COSMOS_ENDPOINT"
COSMOS_DATABASE_NAME_ENV = "COSMOSDB_DATABASE_NAME"
COSMOS_CONTAINER_NAME_ENV = "COSMOSDB_CONTAINER_NAME"
AZURE_OPENAI_ENDPOINT_ENV = "AZURE_OPENAI_ENDPOINT"
OPENAI_MODEL_NAME_ENV = "OPENAI_MODEL_NAME"
AZURE_OPENAI_API_VERSION_ENV = "AZURE_OPENAI_API_VERSION"

# Default values
DEFAULT_DATABASE_NAME = "medicaldata"
DEFAULT_CONTAINER_NAME = "medical_records"
DEFAULT_API_VERSION = "2024-02-15-preview"

# =============================================================================
# UTILITY CLASSES FOR MCP TOOL DEFINITIONS
# =============================================================================

class ToolProperty:
    """
    Defines a property for an MCP tool, including its name, data type, and description.
    
    These properties are used by AI assistants (like GitHub Copilot) to understand:
    - What inputs each tool expects
    - What data types those inputs should be
    - How to describe each input to users
    """
    def __init__(self, property_name: str, property_type: str, description: str):
        self.propertyName = property_name
        self.propertyType = property_type
        self.description = description
        
    def to_dict(self):
        """Converts the property definition to a dictionary format for JSON serialization."""
        return {
            "propertyName": self.propertyName,
            "propertyType": self.propertyType,
            "description": self.description,
        }

# =============================================================================
# MEDICAL DATA PROCESSOR CLASS
# =============================================================================

class MedicalDataProcessor:
    """
    Processes natural language queries and converts them to SQL for medical triplet data.
    Uses Azure OpenAI for natural language understanding and CosmosDB for data storage.
    """
    
    def __init__(self):
        """Initialize the processor with Azure service connections."""
        self.cosmos_client = None
        self.database = None
        self.container = None
        self.openai_client = None
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Ensure all clients are properly initialized."""
        if not self._initialized:
            await self._setup_cosmos_client()
            await self._setup_openai_client()
            self._initialized = True
    
    async def _setup_cosmos_client(self):
        """Set up Cosmos DB client with managed identity authentication."""
        try:
            cosmos_endpoint = os.getenv(COSMOS_ENDPOINT_ENV)
            if not cosmos_endpoint:
                raise ValueError(f"Missing required environment variable: {COSMOS_ENDPOINT_ENV}")
            
            # Use managed identity for authentication
            credential = DefaultAzureCredential()
            self.cosmos_client = CosmosClient(cosmos_endpoint, credential=credential)
            
            database_name = os.getenv(COSMOS_DATABASE_NAME_ENV, DEFAULT_DATABASE_NAME)
            container_name = os.getenv(COSMOS_CONTAINER_NAME_ENV, DEFAULT_CONTAINER_NAME)
            
            self.database = self.cosmos_client.get_database_client(database_name)
            self.container = self.database.get_container_client(container_name)
            
            logger.info("Successfully connected to Cosmos DB")
            
        except Exception as e:
            logger.error(f"Error setting up Cosmos DB client: {e}")
            raise
    
    async def _setup_openai_client(self):
        """Set up Azure OpenAI client with managed identity authentication."""
        try:
            endpoint = os.getenv(AZURE_OPENAI_ENDPOINT_ENV)
            if not endpoint:
                raise ValueError(f"Missing required environment variable: {AZURE_OPENAI_ENDPOINT_ENV}")
            
            api_version = os.getenv(AZURE_OPENAI_API_VERSION_ENV, DEFAULT_API_VERSION)
            
            # Use managed identity for authentication
            credential = DefaultAzureCredential()
            token = await credential.get_token("https://cognitiveservices.azure.com/.default")
            
            self.openai_client = AsyncAzureOpenAI(
                azure_endpoint=endpoint,
                api_version=api_version,
                azure_ad_token=token.token
            )
            
            logger.info("Successfully connected to Azure OpenAI")
            
        except Exception as e:
            logger.error(f"Error setting up Azure OpenAI client: {e}")
            raise
    
    def get_database_schema(self) -> str:
        """Get the database schema as a string for the AI prompt."""
        schema_description = """
        Database Schema:
        Container: medical_records
        Document Structure:
        - id (string): Unique document identifier
        - MEDCode (number): Medical code identifier
        - Slot (number): Slot number for the measurement  
        - Value (string): The measurement value or description
        - timestamp (string): When the record was created
        
        SQL Query Guidelines for CosmosDB:
        - Use SELECT * FROM c WHERE ... syntax
        - Reference fields with c.MEDCode, c.Slot, c.Value
        - Use LIKE for text matching: c.Value LIKE '%search%'
        - Use = for exact matches: c.MEDCode = 1302
        - Use AND, OR for complex conditions
        - Use ORDER BY c.MEDCode for sorting
        
        Sample data structure:
        {
            "id": "unique-id",
            "MEDCode": 1302,
            "Slot": 150,
            "Value": "19928",
            "timestamp": "2024-08-02T10:00:00Z"
        }
        """
        return schema_description
    
    async def generate_sql_query(self, natural_language_query: str) -> str:
        """
        Convert natural language query to SQL using Azure OpenAI.
        
        Args:
            natural_language_query: The user's question in natural language
            
        Returns:
            Generated SQL query string for CosmosDB
        """
        await self._ensure_initialized()
        
        if not self.openai_client:
            raise RuntimeError("OpenAI client not properly initialized")
        
        schema = self.get_database_schema()
        
        system_message = f"""You are an expert SQL query generator for medical data analysis using Azure CosmosDB.

        {schema}
        
        Rules:
        1. Only generate SELECT statements
        2. Use CosmosDB SQL syntax: SELECT ... FROM c WHERE ...
        3. Return only the SQL query, no explanations or markdown formatting
        4. Handle text matching with LIKE for partial matches
        5. Use proper quoting for text values
        6. Consider case-insensitive matching with UPPER() or LOWER() functions
        7. Always reference fields with 'c.' prefix (e.g., c.MEDCode, c.Slot, c.Value)
        
        Common query patterns:
        - "Find all records for MEDCode X" -> SELECT * FROM c WHERE c.MEDCode = X
        - "Show measurements containing 'sodium'" -> SELECT * FROM c WHERE CONTAINS(UPPER(c.Value), UPPER('sodium'))
        - "Get all slot 150 records" -> SELECT * FROM c WHERE c.Slot = 150
        - "Find records with MEDCode 1302 and slot 150" -> SELECT * FROM c WHERE c.MEDCode = 1302 AND c.Slot = 150
        
        Convert this natural language query to CosmosDB SQL: {natural_language_query}"""
        
        try:
            model_name = os.getenv(OPENAI_MODEL_NAME_ENV, "gpt-4")
            
            response = await self.openai_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_message}
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            sql_query = response.choices[0].message.content.strip()
            
            # Clean up the SQL query (remove markdown formatting if present)
            sql_query = re.sub(r'```sql\n?', '', sql_query)
            sql_query = re.sub(r'```\n?', '', sql_query)
            sql_query = sql_query.strip()
            
            logger.info(f"Generated SQL: {sql_query}")
            return sql_query
            
        except Exception as e:
            logger.error(f"Error generating SQL query: {e}")
            raise
    
    async def execute_query(self, sql_query: str) -> List[Dict[str, Any]]:
        """
        Execute the SQL query against CosmosDB and return results.
        
        Args:
            sql_query: The SQL query to execute
            
        Returns:
            Query results as a list of dictionaries
        """
        await self._ensure_initialized()
        
        if not self.container:
            raise RuntimeError("Cosmos DB container not properly initialized")
        
        try:
            # Validate that it's a SELECT query for security
            if not sql_query.strip().upper().startswith('SELECT'):
                raise ValueError("Only SELECT queries are allowed")
            
            # Execute query against CosmosDB
            items = []
            async for item in self.container.query_items(
                query=sql_query,
                enable_cross_partition_query=True
            ):
                items.append(item)
            
            logger.info(f"Query executed successfully, returned {len(items)} rows")
            return items
            
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise
    
    async def process_natural_language_query(self, query: str) -> Dict[str, Any]:
        """
        Process a natural language query end-to-end.
        
        Args:
            query: Natural language query from user
            
        Returns:
            Dictionary containing SQL query, results, and metadata
        """
        try:
            # Generate SQL from natural language
            sql_query = await self.generate_sql_query(query)
            
            # Execute the query
            results = await self.execute_query(sql_query)
            
            return {
                "natural_language_query": query,
                "generated_sql": sql_query,
                "results": results,
                "row_count": len(results),
                "success": True,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing query '{query}': {e}")
            return {
                "natural_language_query": query,
                "generated_sql": None,
                "results": None,
                "row_count": 0,
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }

    async def get_sample_data(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get sample data from the medical records container.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of sample medical records
        """
        await self._ensure_initialized()
        
        if not self.container:
            raise RuntimeError("Cosmos DB container not properly initialized")
        
        try:
            query = f"SELECT TOP {limit} * FROM c ORDER BY c.MEDCode"
            items = []
            async for item in self.container.query_items(
                query=query,
                enable_cross_partition_query=True
            ):
                items.append(item)
            
            logger.info(f"Retrieved {len(items)} sample records")
            return items
            
        except Exception as e:
            logger.error(f"Error retrieving sample data: {e}")
            raise

    async def upload_medical_records(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Upload medical records to Cosmos DB.
        
        Args:
            records: List of medical records to upload
            
        Returns:
            Upload result summary
        """
        await self._ensure_initialized()
        
        if not self.container:
            raise RuntimeError("Cosmos DB container not properly initialized")
        
        uploaded_count = 0
        errors = []
        
        for i, record in enumerate(records):
            try:
                # Validate required fields
                if not all(field in record for field in ["MEDCode", "Slot", "Value"]):
                    errors.append(f"Record {i}: Missing required fields (MEDCode, Slot, Value)")
                    continue
                
                # Create document with unique ID
                document = {
                    "id": str(uuid.uuid4()),
                    "MEDCode": record["MEDCode"],
                    "Slot": record["Slot"], 
                    "Value": str(record["Value"]),
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                # Upload to CosmosDB
                await self.container.create_item(document)
                uploaded_count += 1
                
            except Exception as e:
                errors.append(f"Record {i}: {str(e)}")
        
        return {
            "uploaded_count": uploaded_count,
            "total_records": len(records),
            "errors": errors,
            "success": uploaded_count > 0,
            "timestamp": datetime.utcnow().isoformat()
        }

# Initialize global processor instance
processor = MedicalDataProcessor()

# =============================================================================
# MCP TOOL PROPERTY DEFINITIONS
# =============================================================================

# Properties for the text_to_sql tool
tool_properties_text_to_sql = [
    ToolProperty("query", "string", "The natural language query to convert to SQL and execute against the medical data. For example: 'Show me all records for MEDCode 1302' or 'Find measurements containing sodium'"),
]

# Convert tool properties to JSON for MCP tool registration
tool_properties_text_to_sql_json = json.dumps([prop.to_dict() for prop in tool_properties_text_to_sql])

# =============================================================================
# TEXT-TO-SQL FUNCTIONALITY
# =============================================================================

# HTTP endpoint for text-to-SQL conversion
@app.route(route="text-to-sql", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
async def http_text_to_sql(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP trigger function to convert natural language to SQL and execute the query.
    
    Expects JSON payload:
    {
        "query": "natural language query"
    }
    
    Returns:
    {
        "natural_language_query": "original query",
        "generated_sql": "generated SQL query", 
        "results": [...],
        "row_count": number,
        "success": true/false,
        "timestamp": "ISO datetime"
    }
    """
    try:
        logger.info("Processing text-to-SQL request")
        
        # Extract and validate the request body
        req_body = req.get_json()
        if not req_body or "query" not in req_body:
            return func.HttpResponse(
                json.dumps({"error": "Missing 'query' field in request body"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        query = req_body["query"]
        if not query or not query.strip():
            return func.HttpResponse(
                json.dumps({"error": "Query cannot be empty"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        # Process the natural language query
        result = await processor.process_natural_language_query(query.strip())
        
        logger.info(f"Query processed: success={result['success']}, rows={result.get('row_count', 0)}")
        
        # Return the result
        return func.HttpResponse(
            json.dumps(result, default=str),
            status_code=200 if result["success"] else 500,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logger.error(f"Error in http_text_to_sql: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                "error": f"Internal server error: {str(e)}",
                "success": False,
                "timestamp": datetime.utcnow().isoformat()
            }),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )

# MCP tool for text-to-SQL conversion
@app.generic_trigger(
    arg_name="req", 
    type="mcpToolTrigger",
    toolName="text_to_sql",
    description="Convert natural language queries to SQL and execute them against medical data. This tool analyzes medical triplet data (MEDCode, Slot, Value) and returns matching records based on your natural language description.",
    toolProperties=tool_properties_text_to_sql_json
)
async def mcp_text_to_sql(req: str) -> str:
    """
    MCP tool trigger for text-to-SQL conversion.
    
    This tool can be directly invoked by AI assistants (like GitHub Copilot) 
    via the Model Context Protocol to convert natural language queries to SQL
    and execute them against the medical data.
    """
    try:
        logger.info("Processing MCP text-to-SQL request")
        
        # Parse the MCP request
        req_data = json.loads(req)
        args = req_data.get("arguments", {})
        query = args.get("query", "").strip()
        
        if not query:
            return json.dumps({
                "error": "Query parameter is required and cannot be empty",
                "success": False
            })
        
        # Process the natural language query
        result = await processor.process_natural_language_query(query)
        
        # Format results for MCP response
        if result["success"]:
            # Create a user-friendly summary
            summary = f"Query: {result['natural_language_query']}\n"
            summary += f"Generated SQL: {result['generated_sql']}\n"
            summary += f"Results: {result['row_count']} records found\n\n"
            
            if result['row_count'] > 0:
                summary += "Sample results:\n"
                # Show first 5 results
                for i, record in enumerate(result['results'][:5]):
                    summary += f"Record {i+1}: MEDCode={record.get('MEDCode', 'N/A')}, "
                    summary += f"Slot={record.get('Slot', 'N/A')}, "
                    summary += f"Value={record.get('Value', 'N/A')}\n"
                
                if result['row_count'] > 5:
                    summary += f"... and {result['row_count'] - 5} more records\n"
            else:
                summary += "No matching records found.\n"
            
            result["summary"] = summary
        
        logger.info(f"MCP query processed: success={result['success']}")
        return json.dumps(result, default=str)
        
    except Exception as e:
        logger.error(f"Error in mcp_text_to_sql: {e}", exc_info=True)
        return json.dumps({
            "error": f"Error processing query: {str(e)}",
            "success": False,
            "timestamp": datetime.utcnow().isoformat()
        })

# =============================================================================
# SAMPLE DATA ENDPOINTS
# =============================================================================

# HTTP endpoint for getting sample data
@app.route(route="sample-data", methods=["GET"], auth_level=func.AuthLevel.FUNCTION)
async def http_get_sample_data(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP trigger function to get sample medical data."""
    try:
        logger.info("Processing sample data request")
        
        # Get limit parameter
        limit = int(req.params.get('limit', '10'))
        limit = min(max(limit, 1), 100)  # Ensure between 1 and 100
        
        # Get sample data
        sample_data = await processor.get_sample_data(limit)
        
        result = {
            "sample_data": sample_data,
            "count": len(sample_data),
            "success": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Sample data retrieved: {len(sample_data)} records")
        
        return func.HttpResponse(
            json.dumps(result, default=str),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logger.error(f"Error in http_get_sample_data: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                "error": f"Internal server error: {str(e)}",
                "success": False,
                "timestamp": datetime.utcnow().isoformat()
            }),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )

# HTTP endpoint for uploading medical data
@app.route(route="medical-data", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
async def http_upload_medical_data(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP trigger function to upload medical data to CosmosDB.
    
    Expects JSON payload with array of medical records:
    {
        "records": [
            {
                "MEDCode": 1302,
                "Slot": 150,
                "Value": "19928"
            },
            ...
        ]
    }
    """
    try:
        logger.info("Processing medical data upload request")
        
        req_body = req.get_json()
        if not req_body or "records" not in req_body:
            return func.HttpResponse(
                json.dumps({"error": "Missing 'records' field in request body"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        records = req_body["records"]
        if not isinstance(records, list):
            return func.HttpResponse(
                json.dumps({"error": "'records' must be an array"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        # Upload records
        result = await processor.upload_medical_records(records)
        
        logger.info(f"Medical data upload completed: {result['uploaded_count']}/{result['total_records']} records")
        
        return func.HttpResponse(
            json.dumps(result),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logger.error(f"Error in http_upload_medical_data: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                "error": f"Internal server error: {str(e)}",
                "success": False,
                "timestamp": datetime.utcnow().isoformat()
            }),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )

# Health check endpoint
@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
async def http_health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint for monitoring and load balancing."""
    try:
        logger.info("Processing health check")
        
        # Test CosmosDB connection
        try:
            sample_data = await processor.get_sample_data(1)
            cosmos_status = "healthy"
        except Exception as e:
            cosmos_status = f"unhealthy: {str(e)}"
        
        # Test OpenAI connection
        try:
            # Use a simple test instead of actual query generation
            if processor.openai_client:
                openai_status = "healthy"
            else:
                openai_status = "not initialized"
        except Exception as e:
            openai_status = f"unhealthy: {str(e)}"
        
        health_status = {
            "status": "healthy" if cosmos_status == "healthy" and openai_status == "healthy" else "degraded",
            "cosmos_db": cosmos_status,
            "azure_openai": openai_status,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "medical-data-text-to-sql"
        }
        
        logger.info(f"Health check completed: {health_status['status']}")
        
        return func.HttpResponse(
            json.dumps(health_status),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logger.error(f"Error in health check: {e}", exc_info=True)
        return func.HttpResponse(
            json.dumps({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )

# =============================================================================
# INITIALIZE SAMPLE DATA ON STARTUP
# =============================================================================

@app.function_name("initialize_sample_data")
@app.timer_trigger(schedule="0 0 0 1 1 *", arg_name="timer", run_on_startup=True)  # Run once on startup
async def initialize_sample_data(timer: func.TimerRequest) -> None:
    """Initialize sample medical data on function app startup."""
    try:
        logger.info("Initializing sample medical data")
        
        # Check if data already exists
        existing_data = await processor.get_sample_data(1)
        if existing_data:
            logger.info("Sample data already exists, skipping initialization")
            return
        
        # Sample medical data (matching the original CSV structure)
        sample_records = [
            {"MEDCode": 1302, "Slot": 150, "Value": "19928"},
            {"MEDCode": 1302, "Slot": 151, "Value": "Blood pressure systolic"},
            {"MEDCode": 1302, "Slot": 152, "Value": "120"},
            {"MEDCode": 1303, "Slot": 150, "Value": "Blood pressure diastolic"},
            {"MEDCode": 1303, "Slot": 151, "Value": "80"},
            {"MEDCode": 1304, "Slot": 150, "Value": "Heart rate"},
            {"MEDCode": 1304, "Slot": 151, "Value": "72"},
            {"MEDCode": 1305, "Slot": 150, "Value": "Temperature"},
            {"MEDCode": 1305, "Slot": 151, "Value": "98.6"},
            {"MEDCode": 1306, "Slot": 150, "Value": "Sodium level"},
            {"MEDCode": 1306, "Slot": 151, "Value": "142"},
            {"MEDCode": 1307, "Slot": 150, "Value": "Glucose"},
            {"MEDCode": 1307, "Slot": 151, "Value": "95"},
        ]
        
        # Upload sample data
        result = await processor.upload_medical_records(sample_records)
        logger.info(f"Sample data initialization completed: {result['uploaded_count']} records uploaded")
        
    except Exception as e:
        logger.error(f"Error initializing sample data: {e}", exc_info=True)