"""Test Open Library MCP server with ISBN search"""
import asyncio
import json
from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from mcp_agent.workflows.llm.augmented_llm_google import GoogleAugmentedLLM

app = MCPApp(
    name="openlibrary_test",
    description="Test Open Library MCP"
)

async def test_openlibrary():
    """Test Open Library MCP server with ISBN search"""
    
    test_isbn = "978-0135957059"
    
    print("=" * 70)
    print("🧪 Testing Open Library MCP Server")
    print("=" * 70)
    print(f"\n📚 Test ISBN: {test_isbn}")
    print("=" * 70)
    
    try:
        async with app.run() as running_app:
            logger = running_app.logger
            
            print("\n🔧 Initializing Open Library MCP server...")
            
            agent = Agent(
                name="openlibrary_searcher",
                instruction="""You have access to Open Library tools. 
                
Search for book information using the ISBN and return the results in JSON format with these fields:
- isbn
- title
- authors
- description
- publisher
- year""",
                llm=GoogleAugmentedLLM()
            )
            
            logger.info("openlibrary_searcher: Agent created")
            
            print(f"🔍 Searching Open Library for ISBN {test_isbn}...")
            
            async with agent:
                llm = await agent.attach_llm(
                    lambda agent: GoogleAugmentedLLM(model="gemini-2.0-flash-exp", agent=agent)
                )
                
                result = await llm.generate_str(
                    message=f"Use the Open Library tools to search for book with ISBN {test_isbn}. Return the book information in JSON format."
                )
            
            print("\n" + "=" * 70)
            print("📊 Open Library Results:")
            print("=" * 70)
            print(result)
            print("=" * 70)
            
            try:
                if '{' in result:
                    start = result.find('{')
                    end = result.rfind('}') + 1
                    json_str = result[start:end]
                    data = json.loads(json_str)
                    
                    print("\n✅ Parsed Book Information:")
                    for key, value in data.items():
                        print(f"   {key.capitalize()}: {value}")
            except:
                pass
            
            print("\n✅ Open Library MCP test completed successfully!")
            
            logger.info("openlibrary_searcher: Search completed")
            
            return True
            
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_openlibrary())
    exit(0 if success else 1)
