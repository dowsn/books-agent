# ✅ MCP Servers Setup - COMPLETE

## Problem Solved: npx Issue

**Original Issue:**
```
/nix/store/.../npx: line 6: XDG_CONFIG_HOME: unbound variable
```

**Solution:**
Set required environment variables in `mcp_agent.config.yaml`:
```yaml
env:
  XDG_CONFIG_HOME: /tmp/.config
  HOME: /tmp
```

## 🎯 Both MCP Servers Working

### 1. Brave Search MCP
- **Package:** `@modelcontextprotocol/server-brave-search`
- **Purpose:** Web search functionality
- **API Key:** Uses `BRAVE_API_KEY` environment variable (already configured)
- **Status:** ✅ Working perfectly

### 2. Open Library MCP
- **Package:** `mcp-open-library`
- **Source:** https://github.com/8enSmith/mcp-open-library
- **Purpose:** Book metadata from Open Library API
- **API Key:** None required (public API)
- **Status:** ✅ Working perfectly

## Configuration

File: `mcp_agent.config.yaml`

```yaml
mcp:
  servers:
    brave-search:
      command: npx
      args:
        - "-y"
        - "@modelcontextprotocol/server-brave-search"
      env:
        BRAVE_API_KEY: ${BRAVE_API_KEY}
        XDG_CONFIG_HOME: /tmp/.config
        HOME: /tmp
    
    open-library:
      command: npx
      args:
        - "-y"
        - "mcp-open-library"
      env:
        XDG_CONFIG_HOME: /tmp/.config
        HOME: /tmp
```

## ✅ Tests Passed

### Test 1: Brave Search with ISBN
```bash
python test_brave_isbn.py
```
**Result:** Successfully searched for ISBN 978-0135957059 and returned structured book data

### Test 2: Open Library with ISBN
```bash
python test_openlibrary_mcp.py
```
**Result:** Successfully retrieved book metadata from Open Library API

### Test 3: Both Servers Together
```bash
python test_both_mcp_servers.py
```
**Result:** Both servers initialized and running simultaneously

## 📝 Test Files Created

1. `test_brave_mcp_simple.py` - Simple connection test for Brave MCP
2. `test_brave_isbn.py` - Full ISBN search test with Brave
3. `test_openlibrary_mcp.py` - Open Library ISBN search test
4. `test_both_mcp_servers.py` - Comprehensive test of both servers

## 🎯 How to Use in Your App

Both MCP servers are now available to any agent created with `mcp_agent.app.MCPApp`. Agents can autonomously:

1. **Use Brave Search** - Call `brave_web_search` tool for web searches
2. **Use Open Library** - Call Open Library tools for book metadata
3. **Combine both** - Agent chooses the best tool based on the task

## Example Agent Usage

```python
from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from mcp_agent.workflows.llm.augmented_llm_google import GoogleAugmentedLLM

app = MCPApp(name="my_app", description="My app with MCP servers")

async with app.run() as running_app:
    agent = Agent(
        name="book_searcher",
        instruction="Search for books using available tools",
        llm=GoogleAugmentedLLM()
    )
    
    async with agent:
        llm = await agent.attach_llm(
            lambda agent: GoogleAugmentedLLM(agent=agent)
        )
        
        result = await llm.generate_str(
            message="Search for book with ISBN 978-0135957059"
        )
        # Agent will automatically use Brave or Open Library tools
```

## 🔧 Key Fix

The critical fix was adding these environment variables to each MCP server configuration:
```yaml
env:
  XDG_CONFIG_HOME: /tmp/.config
  HOME: /tmp
```

Without these, npx would fail with "unbound variable" error in the Replit/NixOS environment.

## ✅ Status: READY FOR PRODUCTION

Both MCP servers are:
- ✅ Configured correctly
- ✅ Tested with real ISBNs
- ✅ Working without errors
- ✅ Ready to use in the book extractor app
