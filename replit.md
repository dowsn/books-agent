# Book ISBN Extractor - Autonomous Agent

## Project Overview
A production-ready autonomous AI agent using mcp-agent framework with Google Gemini vision that extracts ISBN and book metadata from cover images, then intelligently enriches the data using a waterfall strategy across multiple web APIs.

## Purpose
Demonstrate advanced agent capabilities:
- **Autonomous tool orchestration** - Agent decides which tools to call based on Book state
- **Waterfall fallback strategy** - Google Books → Open Library → Brave Search
- **State-aware decision making** - Agent tracks which Book fields are filled vs missing
- **Type-safe data merging** - Proper conversion of API responses to Pydantic models

## Current State (October 30, 2025)
✅ **Production-ready fully autonomous agent with German language support**
- **FULLY AUTONOMOUS:** Agent now calls ALL tools including extract_from_photo
- Agent orchestrates complete workflow: photo extraction → web enrichment → data merging
- All Book fields now strings (including page_count)
- New field names: authors, published_year, location, topic, genre
- **German language support:** Descriptions/topics in German, original titles for foreign books
- Successfully tested with German book (ISBN 9783423114628)
- Proper type conversion and Pydantic validation
- Error handling for missing API keys and failed requests
- Source attribution (photo/web/photo+web)

## Recent Changes

### Latest: 🎉 SUCCESS - Both MCP Servers Working! (November 7, 2025)

**MCP Integration Complete:**
- ✅ **Brave Search MCP** - Working via npm with proper secrets file
- ✅ **Open Library MCP** - Working via git clone + build from GitHub/Smithery
- ✅ Both servers tested individually and together
- ✅ All 7 MCP tools (1 Brave + 6 Open Library) functional

**Configuration Breakthroughs:**
1. **Secrets File:** Fixed `mcp_agent.secrets.yaml` structure - must use `mcp.servers.{name}.env.KEY`
2. **Open Library:** Available via Smithery (not npm) - cloned from GitHub and built locally
3. **Both servers** connect simultaneously and work in parallel

**Architecture:**
- **3 Custom Tools:** extract_from_photo, search_google_books, search_open_library
- **2 MCP Servers:** brave-search (npm), open-library (git clone + build)
- **Total:** 3 custom tools + 7 MCP tools available
- **Result:** Full MCP integration achieved!

**Documentation:**
- Created `tests/SUCCESS_BOTH_MCP_SERVERS.md` with complete setup guide
- Updated all docs to reflect working MCP servers
- Installation instructions for Open Library MCP from GitHub

## Previous Changes (October 30, 2025)

### Latest: Fully Autonomous Agent + German Language Support (October 30, 2025)

**Major Refactor to True Autonomy:**
- **Before:** Two-step process (manual photo extraction → agent for web enrichment)
- **After:** Single autonomous agent orchestrates ALL tools
- Agent now calls `extract_from_photo` autonomously as first step
- Simplified workflow: give agent image path, it handles everything
- Follows mcp-agent best practices for autonomous tool orchestration

**Book Model Updates:**
- All fields now strings: `title`, `isbn`, `topic`, `description`, `published_year`, `publisher`, `location`, `authors`, `genre`, `page_count`, `language`
- Renamed fields:
  - `author` → `authors`
  - `year` → `published_year`
  - `city` → `location`
  - `categories` → `topic`
  - Added new field: `genre`
- Type conversion: page_count from int to string

**German Language Requirements:**
- For German books (language: "de"): Keep all content in German
- For foreign books: Keep ORIGINAL title, translate description/topic/genre to German
- Agent instructions explicitly require German translations
- Tool docstrings updated to mention German translation requirement

**Testing Results:**
- ✅ Tested with German book "Der Richter und sein Henker" (ISBN 9783423114628)
- ✅ Agent autonomously called extract_from_photo
- ✅ Agent enriched with Google Books API
- ✅ All new fields populated correctly
- ✅ Description and topics in German
- ✅ All fields returned as strings
- ✅ Source: "photo+web"

## Previous Changes (October 29, 2025)

### Latest: MCP Servers Integration (October 29, 2025 - Evening)

**Problem Solved: npx Issue**
- Error: `/nix/store/.../npx: line 6: XDG_CONFIG_HOME: unbound variable`
- **Solution:** Added environment variables to MCP server configurations
  ```yaml
  env:
    XDG_CONFIG_HOME: /tmp/.config
    HOME: /tmp
  ```

**MCP Servers Added:**
1. **Brave Search MCP** (`@modelcontextprotocol/server-brave-search`)
   - ✅ Configured and tested
   - Web search functionality
   - Uses BRAVE_API_KEY environment variable
   
2. **Open Library MCP** (`mcp-open-library`)
   - ✅ Configured and tested
   - Book metadata from Open Library API
   - No API key required
   - Source: https://github.com/8enSmith/mcp-open-library

**Test Files Created:**
- `test_brave_isbn.py` - Tested Brave search with ISBN
- `test_openlibrary_mcp.py` - Tested Open Library with ISBN
- `test_both_mcp_servers.py` - Comprehensive test of both servers
- `MCP_SETUP_SUCCESS.md` - Complete documentation of MCP setup

### Final Implementation: Autonomous Agent with Specialized Tools

**Phase 1: Tool Specialization**
- Created `extract_from_photo` tool using Gemini vision (NO description field)
- Created `search_google_books` tool calling Google Books API
- Created `search_open_library` tool calling Open Library API
- Created `search_brave` tool calling Brave Search API (optional)

**Phase 2: Autonomous Agent Architecture**
- Removed generic fetch MCP server
- Agent has 4 specific tools with clear purposes
- Waterfall instructions with Book state tracking
- Type conversion instructions (year as string, categories joined)

**Phase 3: Testing & Validation**
- Successfully tested with ISBN 978-80-275-1365-9 (Czech book)
- Agent autonomously called search_google_books
- Retrieved complete data with Czech description
- Proper type conversions passed Pydantic validation
- Source correctly labeled "photo+web"
- Passed architect review with PASS status

## Project Architecture

### File Structure
```
├── src/
│   ├── models.py           - Pydantic models (Book, BookPhotoExtraction)
│   └── book_extractor.py   - Autonomous agent with 2 custom tools
├── files/
│   └── book.png            - Book cover image for testing
├── mcp_agent.config.yaml   - MCP server configuration (Brave & Open Library)
├── README.md               - User documentation
└── replit.md               - This file (project memory)
```

### Technology Stack
- **mcp-agent**: Agent framework for autonomous tool orchestration
- **Google Gemini 2.0 Flash**: Multimodal AI for vision OCR
- **httpx**: Async HTTP client for API calls
- **Pydantic**: Data validation and structured outputs
- **Python 3.11**: Runtime environment

### Autonomous Agent Architecture

**3 Custom Tools + 1 MCP Server:**

1. **extract_from_photo(image_path)** - Custom Tool
   - Uses Gemini vision to extract ISBN, title, author, publisher, year
   - Returns ONLY visible metadata (NO description)
   - Enforces that description must come from web

2. **search_google_books(isbn)** - Custom Tool
   - PRIMARY web data source
   - Calls `https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}`
   - Returns: description, language, categories, page_count, publisher, year
   - Best quality descriptions

3. **search_open_library(isbn)** - Custom Tool
   - FALLBACK web data source
   - Calls `https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=details`
   - Returns: description, subjects, page_count, publisher, year
   - No API key required
   - **Note:** No MCP server available (not published to npm)

4. **MCP Brave Search Server** - @modelcontextprotocol/server-brave-search
   - LAST RESORT web search (via Model Context Protocol)
   - Provides web search tools from Brave Search API
   - Only used if both book APIs fail to provide description
   - Requires BRAVE_API_KEY environment variable
   - **Status:** Server works, needs valid API key

**Waterfall Logic:**

```
Agent receives photo data → checks Book state
  ↓
Calls search_google_books(isbn) [Custom Tool]
  ↓
If description or other fields missing:
  → Calls search_open_library(isbn) [Custom Tool]
  ↓
If description STILL missing and BRAVE_API_KEY available:
  → Uses MCP Brave Search tools [MCP Server]
  ↓
Merges all data → converts types → returns complete Book
```

**State Tracking:**
- Agent knows which Book fields are filled vs null
- Agent instructions show current state for each field
- Agent stops calling tools once all required fields populated
- Agent prefers photo data for: isbn, title, author (most reliable)
- Agent prefers web data for: description, language, categories, page_count

**Type Safety:**
- Agent converts integer year → string year
- Agent joins array categories → comma-separated string
- Agent keeps page_count as integer
- All conversions documented in agent instructions

## Key Design Decisions

### Why Specialized Tools Instead of Generic Fetch?
- **Clarity**: Agent sees explicit tool names (search_google_books vs fetch)
- **Purpose**: Each tool has specific scope and return structure
- **Instructions**: Easier to write waterfall logic with named tools
- **Debugging**: Logs show which tool was called and why

### MCP Integration Status (November 7, 2025)
- **Brave Search MCP**: ✅ Working via `@modelcontextprotocol/server-brave-search` (needs valid API key)
- **Open Library MCP**: ❌ Not available (package not published to npm)
- **Custom tools kept**: extract_from_photo, search_google_books, search_open_library
- **Node.js installed**: Required for npx to run MCP servers
- **Environment fix**: XDG_CONFIG_HOME and HOME variables set for npx
- **Hybrid architecture**: Custom tools + MCP where available
- **Test suite created**: Comprehensive MCP testing in `tests/` folder

### Why Separate Photo and Web Models?
- **BookPhotoExtraction**: Only visible metadata (enforces no description)
- **Book**: Complete data including description from web
- **Validation**: Pydantic ensures description can't come from photo
- **Type Safety**: Separate models prevent accidental data mixing

## Testing Results

**Test Book:** ISBN 978-80-275-1365-9 (Bílá Voda by Kateřina Tučková)

**Photo Extraction:**
- ✅ ISBN: 978-80-275-1365-9
- ✅ Title: (extracted but not shown in final output - used web title)
- ✅ Author: Kateřina Tučková
- ✅ Publisher: (not visible on cover)
- ✅ Year: (not visible on cover)

**Agent Autonomous Actions:**
- ✅ Called search_google_books("978-80-275-1365-9")
- ✅ Retrieved Czech description
- ✅ Retrieved language: cs
- ✅ Retrieved categories: Fiction
- ✅ Retrieved page_count: 640
- ✅ Retrieved publisher: Host
- ✅ Retrieved year: 2022
- ✅ Converted year from integer to string
- ✅ Converted categories from array to string

**Final Output:**
```
Title: Bílá Voda
Author: Kateřina Tučková
ISBN: 978-80-275-1365-9
Publisher: Host
Year: 2022
Language: cs
Categories: Fiction
Pages: 640
Description: Román o osudech tří žen, řeholnic, jejichž životy se protnuly v internačním klášteře v Bílé Vodě...
Source: photo+web ✓
```

## API Keys Required

1. **GEMINI_API_KEY** (required)
   - Get from: https://aistudio.google.com/app/apikey
   - Used for: Gemini vision OCR

2. **BRAVE_API_KEY** (optional)
   - Get from: https://brave.com/search/api/
   - Used for: Last-resort web search fallback
   - If not provided: Agent skips search_brave tool

## Next Steps (Optional Enhancements)

1. **Testing**: Add automated tests with mocked API responses
2. **Logging**: Add detailed tool invocation logs for debugging
3. **Batch Processing**: Support multiple book images at once
4. **Image Upload**: Web interface for uploading book covers
5. **Export**: Save results to CSV or JSON file
6. **Caching**: Cache API responses to reduce calls

## User Preferences
None documented yet.

## Notes
- Description field MUST NEVER come from photo extraction (enforced by model design)
- Agent autonomously decides which tools to call based on Book state
- Waterfall strategy ensures complete data even if primary APIs fail
- Type conversions prevent Pydantic validation errors
- Workflow configured to run `python src/book_extractor.py` on start
- No MCP servers currently configured (all tools are custom Python functions)
