import asyncio
import os
from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from mcp_agent.workflows.llm.augmented_llm_google import GoogleAugmentedLLM


app = MCPApp(
    name="brave_search_test",
    description="Test Brave Search MCP server"
)


async def test_brave_search():
    """Test the Brave Search MCP server with a simple query"""
    
    # Check if API key is available
    if not os.environ.get("BRAVE_API_KEY"):
        print("❌ BRAVE_API_KEY not set in environment")
        print("⚠️  Skipping Brave Search test")
        return
    
    async with app.run() as agent_app:
        logger = agent_app.logger
        
        print("🧪 Testing Brave Search MCP Server")
        print("=" * 60)
        
        # Create agent with access to brave-search MCP server
        agent = Agent(
            name="brave_tester",
            instruction="""You are testing the Brave Search MCP server.
            
Use the Brave Search tools to search for: "Python programming language"

Return a summary of what you found, including:
- Number of results
- Top result title and description
- Whether the search was successful
""",
            server_names=["brave-search"],  # Only use brave-search MCP server
            context=agent_app.context,
        )
        
        async with agent:
            logger.info("brave_tester: Agent initialized with brave-search MCP server")
            
            # Attach Gemini LLM
            llm = await agent.attach_llm(
                lambda agent: GoogleAugmentedLLM(model="gemini-2.0-flash-exp", agent=agent)
            )
            
            print("🔍 Searching for: 'Python programming language'")
            print()
            
            # Run the test query
            result = await llm.generate_str(
                message="Search for 'Python programming language' using Brave Search and summarize what you find."
            )
            
            print("📊 Result:")
            print(result)
            print()
            print("=" * 60)
            print("✅ Brave Search MCP server test complete!")


async def main():
    await test_brave_search()


if __name__ == "__main__":
    asyncio.run(main())
