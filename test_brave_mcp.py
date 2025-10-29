"""Test script to verify Brave MCP server is working correctly"""
import asyncio
from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from mcp_agent.workflows.llm.augmented_llm_google import GoogleAugmentedLLM

# Create a simple test app
app = MCPApp(
    name="brave_mcp_test",
    description="Test Brave MCP server connection"
)

async def test_brave_mcp():
    """Test Brave MCP server with a simple ISBN search"""
    
    # Test ISBN: "The Pragmatic Programmer" - 978-0135957059
    test_isbn = "978-0135957059"
    
    print(f"🧪 Testing Brave MCP Server")
    print(f"=" * 60)
    print(f"Test ISBN: {test_isbn}")
    print(f"Book: The Pragmatic Programmer")
    print(f"=" * 60)
    
    try:
        # Initialize app to load MCP servers
        print("\n🔧 Initializing MCP app...")
        await app.initialize()
        
        # Check server registry for MCP servers
        print("\n🔍 Checking MCP server registry...")
        if hasattr(app, 'server_registry'):
            servers = app.server_registry
            print(f"Server registry: {servers}")
            
            if servers and hasattr(servers, 'servers'):
                print(f"Registered servers: {list(servers.servers.keys())}")
                
                # Try to get tools from each server
                for server_name, server in servers.servers.items():
                    print(f"\n📡 Server: {server_name}")
                    if hasattr(server, 'list_tools'):
                        tools = await server.list_tools()
                        print(f"  Tools: {[t.name for t in tools]}")
        
        # Try running a simple test with the agent
        print("\n🤖 Creating agent to test Brave search...")
        llm = GoogleAugmentedLLM()
        agent = Agent(llm=llm)
        
        # Test search query
        search_query = f"Search the web for the book 'The Pragmatic Programmer' with ISBN {test_isbn}. What is the book about?"
        print(f"\n🔎 Running agent with query...")
        
        # Run the agent with access to MCP tools
        response = await agent.run(
            task=search_query,
            context={"app": app}
        )
        
        print(f"\n📊 Agent Response:")
        print(f"=" * 60)
        print(response)
        print(f"=" * 60)
        
        print(f"\n✅ Brave MCP test completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error during Brave MCP test:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up
        try:
            await app.cleanup()
        except:
            pass

if __name__ == "__main__":
    success = asyncio.run(test_brave_mcp())
    exit(0 if success else 1)
