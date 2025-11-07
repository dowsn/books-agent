import asyncio
import os
from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from mcp_agent.workflows.llm.augmented_llm_google import GoogleAugmentedLLM


app = MCPApp(
    name="both_mcps_test",
    description="Test both Brave Search and Open Library MCP servers together"
)


async def test_both_mcps():
    """Test both MCP servers working together in one agent"""
    
    async with app.run() as agent_app:
        logger = agent_app.logger
        
        print("🧪 Testing Both MCP Servers Together")
        print("=" * 60)
        
        # Determine which servers are available
        server_names = ["open-library"]
        has_brave = bool(os.environ.get("BRAVE_API_KEY"))
        
        if has_brave:
            server_names.append("brave-search")
            print("✓ Brave Search MCP server available")
        else:
            print("○ Brave Search MCP server not available (missing BRAVE_API_KEY)")
        
        print("✓ Open Library MCP server available")
        print()
        
        # Create agent with access to both MCP servers
        agent = Agent(
            name="combined_tester",
            instruction="""You are testing both Open Library and Brave Search MCP servers.

TASK 1: Use Open Library to look up ISBN 9780140328721 (Fantastic Mr. Fox)
TASK 2: If Brave Search is available, search the web for "Roald Dahl books"

Report what you found from each source.
""",
            server_names=server_names,
            context=agent_app.context,
        )
        
        async with agent:
            logger.info(f"combined_tester: Agent initialized with MCP servers: {server_names}")
            
            # Attach Gemini LLM
            llm = await agent.attach_llm(
                lambda agent: GoogleAugmentedLLM(model="gemini-2.0-flash-exp", agent=agent)
            )
            
            print("🔬 Running combined test...")
            print()
            
            # Run the test query
            result = await llm.generate_str(
                message="First, look up ISBN 9780140328721 in Open Library. Then, if Brave Search is available, search for 'Roald Dahl books'. Summarize what you found from each source."
            )
            
            print("📊 Result:")
            print(result)
            print()
            print("=" * 60)
            print("✅ Combined MCP servers test complete!")


async def main():
    await test_both_mcps()


if __name__ == "__main__":
    asyncio.run(main())
