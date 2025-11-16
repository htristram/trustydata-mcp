"""
TrustyData Remote MCP Server - Streamable HTTP (MCP 2025-06-18)
A Model Context Protocol server for claude.ai custom connectors
Compliant with MCP Streamable HTTP specification
"""

import os
import logging
import uuid
from typing import Any, Optional
from datetime import datetime
import httpx
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import Response, JSONResponse, StreamingResponse
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
import uvicorn
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("trustydata-mcp-remote")

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8080")
TRUSTYDATA_API_KEY = os.getenv("TRUSTYDATA_API_KEY")
SERVER_AUTH_TOKEN = os.getenv("SERVER_AUTH_TOKEN")  # For authenticating clients
MCP_PROTOCOL_VERSION = "2025-06-18"

if not TRUSTYDATA_API_KEY:
    logger.warning("TRUSTYDATA_API_KEY environment variable not set")

if not SERVER_AUTH_TOKEN:
    logger.warning("SERVER_AUTH_TOKEN not set - authentication disabled (NOT RECOMMENDED FOR PRODUCTION)")

# Session management
sessions = {}  # session_id -> session_data

# Create MCP server instance
mcp_server = Server("trustydata-mcp")


class Session:
    """Manages MCP session state"""
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now()
        self.initialized = False

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "initialized": self.initialized
        }


def get_or_create_session(session_id: Optional[str] = None) -> Session:
    """Get existing session or create new one"""
    if session_id and session_id in sessions:
        return sessions[session_id]

    new_session_id = session_id or str(uuid.uuid4())
    session = Session(new_session_id)
    sessions[new_session_id] = session
    logger.info(f"Created new session: {new_session_id}")
    return session


async def verify_auth(request: Request) -> bool:
    """Verify request authentication"""
    if not SERVER_AUTH_TOKEN:
        # Auth disabled for development
        return True

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return False

    token = auth_header[7:]  # Remove "Bearer " prefix
    return token == SERVER_AUTH_TOKEN


@mcp_server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools."""
    return [
        types.Tool(
            name="search_localities",
            description="""Search for French localities (cities, towns, villages) with comprehensive filtering options and demographic data.

This tool combines data from La Poste, the French postal service, with official French administrative from INSEE.
**Search Methods:**
- By name: partial or full locality name (e.g., 'Paris', 'Saint-Denis')
- By postal code(s): single code or list of codes (e.g., ['75001', '92100', '77100'])
- By region: single or list of region name or INSEE code (e.g., 'ILE DE FRANCE' or '11')
- By department: single ou list of department name or INSEE code (e.g., 'Paris' or '75')
- By population: min/max thresholds

**Returned Data (when details=true):**
- Official locality name and INSEE code
- Postal code(s)
- Population data (2022, 2016, 2011): total, municipal, and counted separately
- Department information: name, code, population
- Region information: name, code, population

**Best Practices:**
- Use postal_codes for exact matching when you have a list of postal codes
- Use q (name search) for fuzzy/partial matching
- Combine filters to narrow results (e.g., region + population range)
- Set limit appropriately: default 20, max 1000
- Enable details=true to get full demographic information

**Typical Use Cases:**
- Enrich address databases with population data
- Validate postal codes and locality names
- Analyze demographic distribution by region/department
- Build autocomplete systems for French addresses

Returns up to 1000 results per query with official INSEE population census data.""",
            inputSchema={
                "type": "object",
                "properties": {
                    "q": {
                        "type": "string",
                        "description": "Search query for locality name (e.g., 'Paris', 'Lyon', 'Marseille')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 1000)",
                        "default": 1000,
                        "minimum": 1,
                        "maximum": 1000,
                    },
                    "department_code": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by department INSEE code(s) (e.g., ['75'] for Paris, ['13'] for Bouches-du-Rhône).",
                    },
                    "postal_code": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by postal code(s) (e.g., ['75001'] for Paris 1er arrondissement). It can filter by multiple postal codes simultaneously (e.g., ['75001','62930'] for Paris 1er arrondissement and Wimereux).",
                    },

                    "department_name": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by department name(s) (e.g., ['Paris', 'Rhône'])",
                    },
                    "region_code": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by region INSEE code(s) (e.g., ['11'] for Île-de-France)",
                    },
                    "region_name": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by region name(s) in UPPERCASE (e.g., ['BRETAGNE', 'OCCITANIE', 'ILE DE FRANCE'])",
                    },
                    "population_min": {
                        "type": "integer",
                        "description": "Minimum population threshold",
                        "minimum": 0,
                    },
                    "population_max": {
                        "type": "integer",
                        "description": "Maximum population threshold",
                        "minimum": 0,
                    },
                    "details": {
                        "type": "boolean",
                        "description": "Include detailed administrative information (default: true)",
                        "default": True,
                    },
                },
                "required": [],
            },
        )
    ]


@mcp_server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle tool execution requests."""

    if name != "search_localities":
        raise ValueError(f"Unknown tool: {name}")

    if not TRUSTYDATA_API_KEY:
        return [
            types.TextContent(
                type="text",
                text="Error: TRUSTYDATA_API_KEY environment variable not set. Please configure your API key.",
            )
        ]

    # Build query parameters
    params = {}
    if arguments:
        for key, value in arguments.items():
            if value is not None:
                params[key] = value

    # Make API request
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {TRUSTYDATA_API_KEY}",
                "Accept": "application/json",
            }

            logger.info(f"Searching localities with params: {params}")

            response = await client.get(
                f"{API_BASE_URL}/locality/search",
                headers=headers,
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            # Format response
            status = data.get("status", "UNKNOWN")
            message = data.get("message", "")
            count = data.get("count", 0)
            choices = data.get("choices", [])

            if status != "OK" or count == 0:
                return [
                    types.TextContent(
                        type="text",
                        text=f"Status: {status}\nMessage: {message}\nNo localities found matching your criteria.",
                    )
                ]

            # Format results
            result_text = f"Found {count} localit{'y' if count == 1 else 'ies'}:\n\n"

            for idx, locality in enumerate(choices, 1):
                name = locality.get('nom_commune', 'N/A')
                result_text += f"{idx}. **{name}**\n"

                cog = locality.get("cog", {})
                if cog.get("insee"):
                    result_text += f"   - INSEE Code: {cog['insee']}\n"

                if locality.get("code_postal"):
                    result_text += f"   - Postal Code: {locality['code_postal']}\n"

                for population_data in locality.get("population", []):
                    popt = population_data.get('totale')
                    popm = population_data.get('municipale')
                    popa = population_data.get('comptee_a_part')
                    periode = population_data.get('periode', 'N/A')
                    result_text += f"   - Population ville ({periode}): totale={popt}, municipale={popm}, comptée à part={popa}\n"

                dept = locality.get("departement")
                if dept:
                    dept_name = dept.get('libelle', 'N/A')
                    dept_code = dept.get('id', 'N/A')
                    result_text += f"   - Department: {dept_name} ({dept_code})\n"

                    for population_data in dept.get("population", []):
                        popt = population_data.get('totale')
                        popm = population_data.get('municipale')
                        popa = population_data.get('comptee_a_part')
                        periode = population_data.get('periode', 'N/A')
                        result_text += f"   - Population département ({periode}): totale={popt}, municipale={popm}, comptée à part={popa}\n"

                region = locality.get("region")
                if region:
                    region_name = region.get('libelle', 'N/A')
                    region_code = region.get('id', 'N/A')
                    result_text += f"   - Region: {region_name} ({region_code})\n"

                    for population_data in region.get("population", []):
                        popt = population_data.get('totale')
                        popm = population_data.get('municipale')
                        popa = population_data.get('comptee_a_part')
                        periode = population_data.get('periode', 'N/A')
                        result_text += f"   - Population région ({periode}): totale={popt}, municipale={popm}, comptée à part={popa}\n"


                result_text += "\n"

            return [types.TextContent(type="text", text=result_text.strip())]

    except httpx.HTTPStatusError as e:
        error_msg = f"API Error ({e.response.status_code}): {e.response.text}"
        logger.error(error_msg)
        return [types.TextContent(type="text", text=error_msg)]
    except Exception as e:
        error_msg = f"Error searching localities: {str(e)}"
        logger.error(error_msg)
        return [types.TextContent(type="text", text=error_msg)]


async def handle_mcp_endpoint(request: Request):
    """
    Main MCP endpoint - handles both POST and GET according to Streamable HTTP spec
    POST: Client-to-server messages
    GET: Server-to-client streaming (SSE)
    """

    # Verify authentication
    if not await verify_auth(request):
        return Response("Unauthorized", status_code=401)

    # Verify MCP protocol version
    protocol_version = request.headers.get("MCP-Protocol-Version", "2025-03-26")
    logger.info(f"MCP Protocol Version: {protocol_version}")

    # Get or create session
    session_id = request.headers.get("Mcp-Session-Id")
    session = get_or_create_session(session_id)

    if request.method == "POST":
        return await handle_post(request, session)
    elif request.method == "GET":
        return await handle_get(request, session)
    else:
        return Response("Method not allowed", status_code=405)


async def handle_post(request: Request, session: Session):
    """
    Handle POST requests - client-to-server messages
    Returns either:
    - 202 Accepted (for notifications/responses)
    - JSON response (for requests)
    - SSE stream (for requests that need streaming)
    """
    try:
        # Parse JSON-RPC message
        body = await request.body()
        message = json.loads(body.decode('utf-8'))

        logger.info(f"Received message: {message.get('method', 'response')}")

        # Handle initialization
        if message.get("method") == "initialize":
            # Process initialization through MCP server
            response = {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {
                        "tools": {},
                    },
                    "serverInfo": {
                        "name": "trustydata-mcp",
                        "version": "1.0.0",
                        "icon": {
                            "type": "url",
                            "url": "https://mcp.trustydata.app/favicon.ico"
                        }
                    }
                }
            }

            session.initialized = True

            # Return JSON response with session ID header
            return JSONResponse(
                response,
                headers={
                    "Mcp-Session-Id": session.session_id,
                    "Content-Type": "application/json"
                }
            )

        # Handle tools/list
        if message.get("method") == "tools/list":
            tools = await handle_list_tools()
            response = {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {
                    "tools": [
                        {
                            "name": tool.name,
                            "description": tool.description,
                            "inputSchema": tool.inputSchema
                        }
                        for tool in tools
                    ]
                }
            }

            return JSONResponse(
                response,
                headers={
                    "Mcp-Session-Id": session.session_id,
                    "Content-Type": "application/json"
                }
            )

        # Handle tools/call
        if message.get("method") == "tools/call":
            params = message.get("params", {})
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            result = await handle_call_tool(tool_name, arguments)

            response = {
                "jsonrpc": "2.0",
                "id": message.get("id"),
                "result": {
                    "content": [
                        {
                            "type": item.type,
                            "text": item.text if hasattr(item, 'text') else ""
                        }
                        for item in result
                    ]
                }
            }

            return JSONResponse(
                response,
                headers={
                    "Mcp-Session-Id": session.session_id,
                    "Content-Type": "application/json"
                }
            )

        # For other messages, return 202 Accepted
        return Response(
            status_code=202,
            headers={"Mcp-Session-Id": session.session_id}
        )

    except Exception as e:
        logger.error(f"Error handling POST: {str(e)}", exc_info=True)
        error_response = {
            "jsonrpc": "2.0",
            "id": message.get("id") if 'message' in locals() else None,
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }
        return JSONResponse(error_response, status_code=500)


async def handle_get(request: Request, session: Session):
    """
    Handle GET requests - server-to-client streaming via SSE
    Note: Most basic MCP servers don't need this, but it's part of the spec
    """
    accept = request.headers.get("Accept", "")

    if "text/event-stream" not in accept:
        return Response("Not Acceptable", status_code=406)

    # For now, return 405 as we don't support server-initiated streaming
    # This is optional per the spec
    return Response("Method Not Allowed - Server does not support SSE streaming", status_code=405)


async def handle_delete(request: Request):
    """Handle DELETE requests - session termination"""
    if not await verify_auth(request):
        return Response("Unauthorized", status_code=401)

    session_id = request.headers.get("Mcp-Session-Id")
    if session_id and session_id in sessions:
        del sessions[session_id]
        logger.info(f"Deleted session: {session_id}")
        return Response(status_code=204)

    return Response("Session not found", status_code=404)


async def health_check(request: Request):
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "service": "trustydata-mcp",
        "version": "1.0.0",
        "protocol_version": MCP_PROTOCOL_VERSION,
        "sessions": len(sessions)
    })


# Create Starlette app with CORS
app = Starlette(
    debug=True,
    routes=[
        Route("/mcp", endpoint=handle_mcp_endpoint, methods=["GET", "POST"]),
        Route("/mcp", endpoint=handle_delete, methods=["DELETE"]),
        Route("/health", endpoint=health_check, methods=["GET"]),
    ],
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )
    ]
)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8500"))
    host = os.getenv("HOST", "127.0.0.1")

    logger.info(f"Starting TrustyData Remote MCP Server")
    logger.info(f"Protocol Version: {MCP_PROTOCOL_VERSION}")
    logger.info(f"Listening on {host}:{port}")
    logger.info(f"MCP Endpoint: http://{host}:{port}/mcp")
    logger.info(f"API TrustyData Base URL: {API_BASE_URL}")

    if not SERVER_AUTH_TOKEN:
        logger.warning("⚠️  WARNING: Running without authentication!")
        logger.warning("⚠️  Set SERVER_AUTH_TOKEN environment variable for production")

    uvicorn.run(app, host=host, port=port, log_level="info")
