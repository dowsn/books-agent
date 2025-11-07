import asyncio
from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from mcp_agent.workflows.llm.augmented_llm_google import GoogleAugmentedLLM


app = MCPApp(
    name="open_library_test",
    description="Test Open Library MCP server"
)


async def test_open_library():
    """Test the Open Library MCP server with a known ISBN"""
    
    async with app.run() as agent_app:
        logger = agent_app.logger
        
        print("🧪 Testing Open Library MCP Server")
        print("=" * 60)
        
        # Create agent with access to open-library MCP server
        agent = Agent(
            name="openlibrary_tester",
            instruction="""You are testing the Open Library MCP server.
            
Use the Open Library tools to look up the book with ISBN: 9780140328721
(This is "Fantastic Mr. Fox" by Roald Dahl)

Return information you found about this book, including:
- Title
- Author(s)
- Publisher
- Publication year
- Description (if available)
- Number of pages (if available)
""",
            server_names=["open-library"],  # Only use open-library MCP server
            context=agent_app.context,
        )
        
        async with agent:
            logger.info("openlibrary_tester: Agent initialized with open-library MCP server")
            
            # Attach Gemini LLM
            llm = await agent.attach_llm(
                lambda agent: GoogleAugmentedLLM(model="gemini-2.0-flash-exp", agent=agent)
            )
            
            print("📚 Looking up ISBN: 9780140328721 (Fantastic Mr. Fox)")
            print()
            
            # Run the test query
            result = await llm.generate_str(
                message="Look up the book with ISBN 9780140328721 using Open Library and tell me what you find."
            )
            
            print("📊 Result:")
            print(result)
            print()
            print("=" * 60)
            print("✅ Open Library MCP server test complete!")


async def main():
    await test_open_library()


if __name__ == "__main__":
    asyncio.run(main())
