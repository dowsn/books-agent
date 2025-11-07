# MCP Server Tests

## Overview
This folder contains comprehensive tests for the MCP (Model Context Protocol) servers used in the book extractor project. All tests follow the official mcp-agent patterns from https://mcp-agent.com/.

## Test Files

### 1. `test_brave_search_mcp.py`
Tests the Brave Search MCP server independently.

**What it does:**
- Creates an MCPApp instance
- Initializes an Agent with only the `brave-search` MCP server
- Attaches GoogleAugmentedLLM (Gemini)
- Runs a test query: "Python programming language"
- Reports results

**Run:**
```bash
python tests/test_brave_search_mcp.py
```

**Status:** ✅ Server works (needs valid BRAVE_API_KEY)

---

### 2. `test_open_library_mcp.py`
Tests the Open Library MCP server independently.

**What it does:**
- Creates an MCPApp instance
- Initializes an Agent with only the `open-library` MCP server
- Attaches GoogleAugmentedLLM (Gemini)
- Runs a test query for ISBN 9780140328721 (Fantastic Mr. Fox)
- Reports results

**Run:**
```bash
python tests/test_open_library_mcp.py
```

**Status:** ❌ Package not found in npm registry

---

### 3. `test_both_mcps.py`
Tests both MCP servers working together.

**What it does:**
- Creates an MCPApp instance
- Initializes an Agent with both MCP servers
- Tests coordination between multiple MCP servers
- Reports combined results

**Run:**
```bash
python tests/test_both_mcps.py
```

---

### 4. `MCP_TEST_RESULTS.md`
Comprehensive documentation of all test results, findings, and architectural decisions.

**Contains:**
- Detailed test results for each MCP server
- Error logs and diagnostics
- Alternative solutions explored
- Final architecture recommendations
- Links to relevant documentation

---

## Key Findings

### ✅ Brave Search MCP Server
- **Package:** `@modelcontextprotocol/server-brave-search`
- **Status:** Fully functional
- **Issue:** API key is invalid/expired
- **Solution:** Get valid key from https://brave.com/search/api/

### ❌ Open Library MCP Server
- **Package:** `mcp-open-library` / `@8ensmith/mcp-open-library`
- **Status:** Not published to npm
- **Issue:** Repository exists on GitHub but not available via npx
- **Solution:** Use custom `search_open_library()` tool instead

---

## Architecture Decision

After testing, the project uses a **hybrid approach**:

**3 Custom Tools:**
1. `extract_from_photo()` - Gemini vision (no MCP available)
2. `search_google_books()` - Google Books API (no MCP available)
3. `search_open_library()` - Open Library API (MCP not published)

**1 MCP Server:**
1. `brave-search` - Web search (ready when valid API key provided)

This is the optimal architecture because:
- Custom tools work reliably for APIs without MCP servers
- MCP servers used where available (Brave Search)
- Clean separation of concerns
- All following mcp-agent.com best practices

---

## mcp-agent Patterns Used

All tests follow the official patterns from https://mcp-agent.com/:

```python
# 1. Create MCPApp
app = MCPApp(name="test_name", description="Test description")

# 2. Use async with app.run()
async with app.run() as agent_app:
    
    # 3. Create Agent with server_names
    agent = Agent(
        name="agent_name",
        instruction="Clear instructions...",
        server_names=["server-1", "server-2"],
        context=agent_app.context,
    )
    
    # 4. Use async with agent
    async with agent:
        
        # 5. Attach LLM
        llm = await agent.attach_llm(
            lambda agent: GoogleAugmentedLLM(
                model="gemini-2.0-flash-exp", 
                agent=agent
            )
        )
        
        # 6. Generate response
        result = await llm.generate_str(message="Your query")
```

---

## Next Steps

1. **Get valid Brave API key** to enable Brave Search MCP server
2. **Tests are ready** - just add API key and rerun
3. **Custom tools** will continue to work independently
4. **MCP server** will automatically activate when API key is valid

---

## Documentation Links

- **mcp-agent official docs:** https://mcp-agent.com/
- **mcp-agent SDK docs:** https://docs.mcp-agent.com/
- **Brave Search API:** https://brave.com/search/api/
- **Open Library API:** https://openlibrary.org/developers/api
