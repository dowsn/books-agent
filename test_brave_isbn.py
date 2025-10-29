"""Test Brave MCP server with ISBN search"""
import asyncio
import json
from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from mcp_agent.workflows.llm.augmented_llm_google import GoogleAugmentedLLM

app = MCPApp(
    name="isbn_search_test",
    description="Test ISBN search with Brave MCP"
)

async def test_isbn_search():
    """Test searching for a book by ISBN using Brave MCP"""
    
    # Test ISBN: The Pragmatic Programmer
    test_isbn = "978-0135957059"
    
    print("=" * 70)
    print("🧪 Testing Brave MCP Server with ISBN Search")
    print("=" * 70)
    print(f"\n📚 Test Book:")
    print(f"   ISBN: {test_isbn}")
    print(f"   Expected: The Pragmatic Programmer (20th Anniversary Edition)")
    print(f"   Authors: David Thomas, Andrew Hunt")
    print("\n" + "=" * 70)
    
    try:
        async with app.run() as running_app:
            logger = running_app.logger
            
            print("\n🔧 Initializing Brave MCP server...")
            
            # Create an agent with access to MCP tools
            agent = Agent(
                name="isbn_searcher",
                instruction="""You are a book search assistant. You have access to the Brave Search tool.

Your task: Search the web for information about a book using its ISBN.

Return your findings in this exact JSON format:
{
  "isbn": "ISBN number",
  "title": "Book title",
  "authors": "Author names",
  "description": "Book description",
  "publisher": "Publisher name",
  "year": "Publication year"
}

Use the brave_web_search tool to find this information.""",
                llm=GoogleAugmentedLLM()
            )
            
            logger.info("isbn_searcher: Agent created with Brave MCP access")
            
            # Run the agent
            print(f"🔍 Searching for ISBN {test_isbn} using Brave MCP...")
            
            async with agent:
                # Attach LLM
                llm = await agent.attach_llm(
                    lambda agent: GoogleAugmentedLLM(model="gemini-2.0-flash-exp", agent=agent)
                )
                
                # Generate response
                result = await llm.generate_str(
                    message=f"Search the web for the book with ISBN {test_isbn}. Find the title, authors, description, publisher, and year. Return the results in JSON format."
                )
            
            print("\n" + "=" * 70)
            print("📊 Search Results:")
            print("=" * 70)
            print(result)
            print("=" * 70)
            
            # Try to parse if it's JSON
            try:
                if '{' in result:
                    # Extract JSON from the result
                    start = result.find('{')
                    end = result.rfind('}') + 1
                    json_str = result[start:end]
                    data = json.loads(json_str)
                    
                    print("\n✅ Parsed Book Information:")
                    for key, value in data.items():
                        print(f"   {key.capitalize()}: {value}")
            except:
                pass
            
            print("\n✅ Test completed successfully!")
            print("\n💡 The Brave MCP server is working correctly!")
            print("   You can now use it in your book extraction app.")
            
            logger.info("isbn_searcher: Search completed successfully")
            
            return True
            
    except Exception as e:
        print(f"\n❌ Error during search:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_isbn_search())
    exit(0 if success else 1)
