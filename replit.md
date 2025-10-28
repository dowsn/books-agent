# Book ISBN Extractor Agent

## Project Overview
An intelligent AI agent using the mcp-agent framework with Google Gemini 2.0 Flash vision that extracts ISBN numbers and book metadata from book cover images, then enriches the data with complete book information from web APIs.

## Purpose
Demonstrate integration between:
- mcp-agent framework (Model Context Protocol for tool access)
- Google Gemini multimodal AI (vision OCR for image extraction)
- MCP fetch server (HTTP requests to external APIs)
- Structured data extraction and web enrichment

## Current State
✅ **Production-ready implementation complete**
- Two-step workflow: Photo extraction → Web enrichment
- Gemini vision extracts ISBN, title, author, publisher, year (NO description)
- Agent autonomously calls Google Books API via fetch MCP server
- Fallback to Open Library API when Google Books fails
- Source tracking (photo/web/photo+web) for data attribution
- Successfully tested with real book images

## Recent Changes (October 28, 2025)

### Phase 1: Initial Setup
- Installed mcp-agent framework with Google Gemini support
- Created Book and BookPhotoExtraction Pydantic models
- Set up Gemini API key via Replit secrets

### Phase 2: Agent Architecture Rebuild
- Restructured to follow mcp-agent patterns from official examples
- Created `mcp_agent.config.yaml` to configure fetch MCP server
- Implemented agent-driven workflow with autonomous tool use
- Replaced manual API calls with intelligent agent instructions

### Phase 3: Web Enrichment & Fallbacks
- Added Google Books API as primary data source
- Implemented Open Library API as fallback (no API key required)
- Added title+author search fallback for missing ISBNs
- Verified description NEVER comes from photo, only from web APIs

### Phase 4: Testing & Validation
- Successfully extracted ISBN 978-80-275-1365-9 from Czech book
- Retrieved Czech description from Google Books API
- Verified source tracking shows "photo+web"
- Passed architect review with PASS status

## Project Architecture

### Files
```
├── src/
│   ├── models.py           - Book data models (Pydantic)
│   └── book_extractor.py   - Main agent with vision + web enrichment
├── files/
│   └── book.png            - Book cover image for extraction
├── mcp_agent.config.yaml   - MCP server configuration (fetch)
├── README.md               - User documentation
└── replit.md               - This file (project memory)
```

### Technology Stack
- **mcp-agent**: Agent framework built on Model Context Protocol
- **Google Gemini 2.0 Flash**: Multimodal AI with vision OCR
- **mcp-server-fetch**: MCP server for HTTP requests
- **Pydantic**: Data validation and structured outputs
- **Python 3.11**: Runtime environment

### Two-Step Workflow

**Step 1: Vision OCR (Photo Extraction)**
- Gemini vision extracts visible metadata from image:
  - ISBN number
  - Title
  - Author
  - Publisher
  - Publication year
- **Critical**: NO description from photo (requirement)

**Step 2: Web Enrichment (Agent-Driven)**
- Agent connects to fetch MCP server
- Calls Google Books API with ISBN
- Parses JSON response for complete book data:
  - Description (from web only!)
  - Language
  - Categories
  - Page count
- Falls back to Open Library if Google Books fails
- Merges photo + web data with source attribution

### Fallback Strategy
1. **Primary**: Google Books API (`https://www.googleapis.com/books/v1/volumes`)
2. **Fallback 1**: Open Library by ISBN (`https://openlibrary.org/api/books`)
3. **Fallback 2**: Open Library search by title+author

All fallbacks use the existing fetch MCP tool (no additional dependencies or API keys).

## Key Design Decisions

### Why Agent-Based Architecture?
- **Autonomous tool use**: Agent decides when/how to call fetch tool
- **Flexible fallbacks**: Instructions guide agent to try multiple APIs
- **Scalable**: Easy to add more data sources without code changes

### Why Separate Photo and Web Models?
- **BookPhotoExtraction**: Only visible metadata (no description field)
- **Book**: Complete data with description from web
- **Prevents**: Description from accidentally coming from photo

### Why fetch MCP Server?
- **Universal HTTP client**: Can call any REST API
- **No authentication burden**: Works with public APIs (Google Books, Open Library)
- **MCP pattern compliance**: Clean separation of concerns

## User Preferences
None documented yet.

## Next Steps (Optional Enhancements)
- Add image upload support for user-provided covers
- Support batch processing for multiple books
- Add more fallback sources (Amazon, GoodReads)
- Export results to CSV/JSON formats
- Add caching to reduce API calls

## Notes
- Description field MUST NEVER come from photo extraction (enforced by model design)
- Agent uses detailed instructions to parse Google Books JSON structure
- Markdown code fences in agent responses are stripped during JSON parsing
- Source tracking helps verify data provenance (photo vs web vs both)
- Workflow configured to run `python src/book_extractor.py` on start
