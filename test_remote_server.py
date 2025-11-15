"""
Test script for TrustyData MCP Remote Server
Tests the Streamable HTTP protocol implementation
"""

import os
import sys
import json
import httpx
from typing import Optional

# Configuration
BASE_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8500")
AUTH_TOKEN = os.getenv("SERVER_AUTH_TOKEN", "")

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_test(name: str):
    """Print test name"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}→ {name}{Colors.END}")


def print_success(msg: str):
    """Print success message"""
    print(f"  {Colors.GREEN}✓ {msg}{Colors.END}")


def print_error(msg: str):
    """Print error message"""
    print(f"  {Colors.RED}✗ {msg}{Colors.END}")


def print_warning(msg: str):
    """Print warning message"""
    print(f"  {Colors.YELLOW}⚠ {msg}{Colors.END}")


async def test_health_check():
    """Test health check endpoint"""
    print_test("Testing health check endpoint")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/health")

            if response.status_code == 200:
                data = response.json()
                print_success(f"Health check passed")
                print(f"    Status: {data.get('status')}")
                print(f"    Service: {data.get('service')}")
                print(f"    Version: {data.get('version')}")
                print(f"    Protocol: {data.get('protocol_version')}")
                return True
            else:
                print_error(f"Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Health check failed: {str(e)}")
            return False


async def test_initialize(session_id: Optional[str] = None) -> Optional[str]:
    """Test MCP initialize request"""
    print_test("Testing MCP initialize")

    headers = {
        "Content-Type": "application/json",
        "MCP-Protocol-Version": "2025-06-18",
        "Accept": "application/json",
    }

    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"

    if session_id:
        headers["Mcp-Session-Id"] = session_id

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/mcp",
                headers=headers,
                json=payload
            )

            if response.status_code == 200:
                data = response.json()
                new_session_id = response.headers.get("Mcp-Session-Id")

                print_success("Initialize successful")
                print(f"    Session ID: {new_session_id}")
                print(f"    Protocol: {data.get('result', {}).get('protocolVersion')}")
                print(f"    Server: {data.get('result', {}).get('serverInfo', {}).get('name')}")

                return new_session_id
            else:
                print_error(f"Initialize failed: {response.status_code}")
                print(f"    Response: {response.text}")
                return None
        except Exception as e:
            print_error(f"Initialize failed: {str(e)}")
            return None


async def test_list_tools(session_id: str):
    """Test tools/list request"""
    print_test("Testing tools/list")

    headers = {
        "Content-Type": "application/json",
        "MCP-Protocol-Version": "2025-06-18",
        "Mcp-Session-Id": session_id,
        "Accept": "application/json",
    }

    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"

    payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/mcp",
                headers=headers,
                json=payload
            )

            if response.status_code == 200:
                data = response.json()
                tools = data.get('result', {}).get('tools', [])

                print_success(f"Found {len(tools)} tool(s)")
                for tool in tools:
                    print(f"    - {tool.get('name')}: {tool.get('description')[:60]}...")

                return True
            else:
                print_error(f"List tools failed: {response.status_code}")
                print(f"    Response: {response.text}")
                return False
        except Exception as e:
            print_error(f"List tools failed: {str(e)}")
            return False


async def test_call_tool(session_id: str):
    """Test tools/call request"""
    print_test("Testing tools/call - search_localities")

    headers = {
        "Content-Type": "application/json",
        "MCP-Protocol-Version": "2025-06-18",
        "Mcp-Session-Id": session_id,
        "Accept": "application/json",
    }

    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"

    payload = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "search_localities",
            "arguments": {
                "q": "Paris",
                "limit": 3
            }
        }
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                f"{BASE_URL}/mcp",
                headers=headers,
                json=payload
            )

            if response.status_code == 200:
                data = response.json()
                result = data.get('result', {})
                content = result.get('content', [])

                print_success("Tool call successful")

                if content:
                    text = content[0].get('text', '')
                    # Show first 200 chars
                    preview = text[:200] + '...' if len(text) > 200 else text
                    print(f"    Result preview:\n    {preview}")

                return True
            else:
                print_error(f"Tool call failed: {response.status_code}")
                print(f"    Response: {response.text}")
                return False
        except Exception as e:
            print_error(f"Tool call failed: {str(e)}")
            return False


async def test_search_localities_detailed(session_id: str):
    """Test search_localities with various filters and scenarios"""
    print_test("Testing search_localities - Detailed Tests")

    headers = {
        "Content-Type": "application/json",
        "MCP-Protocol-Version": "2025-06-18",
        "Mcp-Session-Id": session_id,
        "Accept": "application/json",
    }

    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"

    test_cases = [
        {
            "name": "Search by name only",
            "arguments": {
                "q": "Lyon",
                "limit": 5
            }
        },
        {
            "name": "Search with department filter",
            "arguments": {
                "q": "st denis",
                "department_code": ["93"],
                "limit": 5
            }
        },
        {
            "name": "Search with region filter",
            "arguments": {
                "q": "Mont",
                "region_name": ["BRETAGNE"],
                "limit": 5
            }
        },
        {
            "name": "Search with population filter",
            "arguments": {
                "q": "Paris",
                "population_min": 100000,
                "limit": 5
            }
        },
        {
            "name": "Search with multiple filters",
            "arguments": {
                "q": "lyon",
                "department_code": ["69"],
                "population_min": 50000,
                "limit": 5
            }
        },
        {
            "name": "Search with no results",
            "arguments": {
                "q": "XYZ_NONEXISTENT_CITY_123",
                "limit": 5
            }
        }
    ]

    all_passed = True

    for idx, test_case in enumerate(test_cases, 1):
        print(f"\n  Test {idx}: {test_case['name']}")

        payload = {
            "jsonrpc": "2.0",
            "id": 100 + idx,
            "method": "tools/call",
            "params": {
                "name": "search_localities",
                "arguments": test_case["arguments"]
            }
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{BASE_URL}/mcp",
                    headers=headers,
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    result = data.get('result', {})
                    content = result.get('content', [])

                    if content:
                        text = content[0].get('text', '')
                        
                        # Extract number of results from response
                        if "No localities found" in text:
                            count = 0
                        else:
                            # Try to extract count from "Found X localities:" or "Found X locality:"
                            import re
                            match = re.search(r'Found (\d+) localit(?:y|ies)', text)
                            count = int(match.group(1)) if match else 0

                        print_success(f"Query succeeded - Found {count} result(s)")
                        
                        # Show a snippet of the result
                        lines = text.split('\n')[:5]
                        for line in lines:
                            if line.strip():
                                print(f"      {line[:70]}")
                    else:
                        print_warning("No content in response")
                        all_passed = False
                else:
                    print_error(f"Request failed: {response.status_code}")
                    print(f"      Response: {response.text[:100]}")
                    all_passed = False

            except Exception as e:
                print_error(f"Exception: {str(e)}")
                all_passed = False

    return all_passed


async def test_authentication():
    """Test authentication"""
    print_test("Testing authentication")

    if not AUTH_TOKEN:
        print_warning("No AUTH_TOKEN set - skipping authentication test")
        return True

    # Try without token
    headers = {
        "Content-Type": "application/json",
        "MCP-Protocol-Version": "2025-06-18",
    }

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2025-06-18"}
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/mcp",
                headers=headers,
                json=payload
            )

            if response.status_code == 401:
                print_success("Authentication required (as expected)")
                return True
            else:
                print_warning(f"Expected 401, got {response.status_code}")
                return False
        except Exception as e:
            print_error(f"Authentication test failed: {str(e)}")
            return False


async def main():
    """Run all tests"""
    print(f"{Colors.BOLD}╔═══════════════════════════════════════════════════╗{Colors.END}")
    print(f"{Colors.BOLD}║   TrustyData MCP Remote Server - Test Suite      ║{Colors.END}")
    print(f"{Colors.BOLD}╚═══════════════════════════════════════════════════╝{Colors.END}")
    print(f"\nServer URL: {BASE_URL}")
    if AUTH_TOKEN:
        print(f"Auth Token: {AUTH_TOKEN[:8]}...")
    else:
        print("Auth Token: Not set")
    print("")

    results = []

    # Run tests
    results.append(("Health Check", await test_health_check()))

    if AUTH_TOKEN:
        results.append(("Authentication", await test_authentication()))

    session_id = await test_initialize()
    results.append(("Initialize", session_id is not None))

    if session_id:
        results.append(("List Tools", await test_list_tools(session_id)))
        results.append(("Call Tool", await test_call_tool(session_id)))
        results.append(("Search Localities Detailed", await test_search_localities_detailed(session_id)))

    # Summary
    print(f"\n{Colors.BOLD}═══════════════════════════════════════════════════{Colors.END}")
    print(f"{Colors.BOLD}Test Summary:{Colors.END}\n")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = f"{Colors.GREEN}✓ PASS{Colors.END}" if result else f"{Colors.RED}✗ FAIL{Colors.END}"
        print(f"  {name}: {status}")

    print(f"\n{Colors.BOLD}Total: {passed}/{total} tests passed{Colors.END}")

    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ All tests passed!{Colors.END}")
        print(f"\n{Colors.BOLD}Your server is ready to be used with claude.ai{Colors.END}")
        print(f"Add it as a custom connector using URL: {BASE_URL}/mcp")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ Some tests failed{Colors.END}")
        return 1


if __name__ == "__main__":
    import asyncio
    sys.exit(asyncio.run(main()))
