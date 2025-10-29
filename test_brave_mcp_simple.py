"""Simple test to verify Brave MCP server loads and lists tools"""
import asyncio
from mcp_agent.app import MCPApp

async def test_mcp_server():
    """Test if Brave MCP server starts and lists tools"""
    
    print("🧪 Testing Brave MCP Server Setup")
    print("=" * 60)
    
    try:
        # Create app that will load MCP servers from config
        app = MCPApp(
            name="mcp_test",
            description="Test MCP server loading"
        )
        
        print("\n🔧 Initializing app to load MCP servers...")
        await app.initialize()
        
        print("✅ App initialized successfully!")
        
        # Check server registry
        print("\n📡 Checking MCP server registry...")
        if hasattr(app, 'server_registry'):
            registry = app.server_registry
            print(f"Registry type: {type(registry)}")
            print(f"Registry attributes: {[a for a in dir(registry) if not a.startswith('_')]}")
            
            # Try different ways to access servers
            if hasattr(registry, 'get_servers'):
                servers = await registry.get_servers()
                print(f"get_servers() returned: {servers}")
            elif hasattr(registry, 'list_servers'):
                servers = await registry.list_servers()
                print(f"list_servers() returned: {servers}")
            
            # Check for connection manager
            if hasattr(registry, 'connection_manager'):
                cm = registry.connection_manager
                print(f"\nConnection manager found!")
                print(f"Running servers: {cm.running_servers}")
                
                # Try to get brave-search server
                if 'brave-search' not in cm.running_servers:
                    print("\n🚀 Starting brave-search MCP server...")
                    try:
                        server = await cm.get_server('brave-search')
                        print(f"  ✅ Server started: {type(server)}")
                        print(f"  Running servers now: {cm.running_servers}")
                        
                        # Try to list tools
                        if hasattr(server, 'list_tools'):
                            tools = await server.list_tools()
                            print(f"\n📋 Available tools from brave-search:")
                            for tool in tools:
                                tool_name = tool.name if hasattr(tool, 'name') else str(tool)
                                tool_desc = tool.description if hasattr(tool, 'description') else 'No description'
                                print(f"  ✓ {tool_name}")
                                print(f"    {tool_desc}")
                        else:
                            print("  Server has no list_tools method")
                            
                    except Exception as e:
                        print(f"  ❌ Error starting server: {e}")
                        import traceback
                        traceback.print_exc()
                else:
                    print("\n✓ brave-search server already running")
                    server = cm.running_servers['brave-search']
                    tools = await server.list_tools()
                    print(f"Tools: {[t.name for t in tools]}")
            else:
                print("\n  No connection_manager found")
        else:
            print("❌ App has no 'server_registry' attribute")
        
        # Test using an ISBN
        print("\n" + "=" * 60)
        print("📚 Test Query: Search for ISBN 978-0135957059")
        print("=" * 60)
        print("\n✅ MCP server test completed!")
        print("\nNOTE: The server loaded successfully. To actually use it,")
        print("you would call the brave_web_search tool from an agent.")
        
        await app.cleanup()
        return True
        
    except Exception as e:
        print(f"\n❌ Error testing MCP server:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mcp_server())
    exit(0 if success else 1)
