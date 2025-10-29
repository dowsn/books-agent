# Book ISBN Extractor

An intelligent agent using the mcp-agent framework with Google Gemini vision to extract ISBN and book metadata from cover images, then enrich with web data from Google Books API.

## How It Works

The book extractor uses an intelligent agent-based workflow:

### 🔍 Step 1: Vision OCR (Gemini 2.0 Flash)
- Extracts ISBN, title, author, publisher, year from book cover image
- Uses Gemini vision API for accurate OCR
- **No description from photos** - only visible metadata

### 🌐 Step 2: Web Enrichment (Autonomous Agent)
The agent has 4 specialized tools and orchestrates them autonomously:

**Tools Available:**
1. `extract_from_photo` - Gemini vision extracts visible metadata (ISBN, title, author)
2. `search_google_books` - PRIMARY: Calls Google Books API for complete data
3. `search_open_library` - FALLBACK: Alternative book database
4. `search_brave` - LAST RESORT: Web search if both APIs fail (optional)

**Waterfall Logic:**
- Agent tracks which Book fields are filled vs null
- Calls Google Books first for description, language, categories
- Falls back to Open Library if Google Books missing data
- Uses Brave Search only if critical fields still missing
- Stops when all required fields are populated

### 🎯 Key Features
- **Autonomous orchestration**: Agent decides which tools to call based on Book state
- **Specific tools**: Each tool has clear purpose (not generic fetch)
- **Smart fallbacks**: Waterfall strategy ensures complete data
- **Type-safe**: Agent converts data to correct types (year as string, categories joined)
- **Source tracking**: Shows "photo", "web", or "photo+web"
- **Description guarantee**: Description ALWAYS from web, never from photo!

## Setup

1. Dependencies are already installed in this Replit project:
   - mcp-agent[google] - Agent framework with Gemini support
   - mcp-server-fetch - MCP server for HTTP requests
   - google-genai - Gemini API client

2. Add your Gemini API key to Replit Secrets:
   - Get a free API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Add it as `GEMINI_API_KEY` in Replit Secrets

3. (Optional) Add Brave Search for last-resort fallback:
   - Get a free API key from [Brave Search API](https://brave.com/search/api/)
   - Add it as `BRAVE_API_KEY` in Replit Secrets
   - The agent will automatically use it if Google Books and Open Library fail

4. Configuration file `mcp_agent.config.yaml` is already set up

## Usage

1. Place your book cover image in `files/book.png`

2. Run the extractor:
```bash
python src/book_extractor.py
```

The autonomous agent will:
1. Use Gemini vision to extract ISBN, title, author from image
2. Check which Book fields are missing
3. Call `search_google_books(isbn)` for description, language, categories
4. If any fields still missing, call `search_open_library(isbn)`
5. If description still missing and Brave API available, call `search_brave(query)`
6. Merge all data and display complete Book object

**Example Output:**
```
📚 Complete Book Information:
============================================================
Title: Bílá Voda
Author: Kateřina Tučková
ISBN: 978-80-275-1365-9
Publisher: Host
Year: 2022
Language: cs
Categories: Fiction
Pages: 640
Description: Román o osudech tří žen, řeholnic, jejichž životy...
Source: photo+web ✓
============================================================
```

## Project Structure

```
├── src/
│   ├── models.py           - Pydantic models (Book, BookPhotoExtraction)
│   └── book_extractor.py   - Autonomous agent with 4 specialized tools
├── files/
│   └── book.png            - Book cover image for extraction
├── mcp_agent.config.yaml   - Agent configuration
└── README.md               - This file
```

## How the Agent Works

The agent is built with the mcp-agent framework and has access to 4 custom tools:

```python
@app.tool()
async def extract_from_photo(image_path: str) -> dict:
    """Gemini vision extracts ISBN, title, author, publisher, year"""

@app.tool()
async def search_google_books(isbn: str) -> dict:
    """Calls Google Books API for description, language, categories"""

@app.tool()
async def search_open_library(isbn: str) -> dict:
    """Calls Open Library API as fallback"""

@app.tool()
async def search_brave(query: str) -> dict:
    """Web search as last resort (requires BRAVE_API_KEY)"""
```

The agent receives instructions with the waterfall strategy and autonomously decides which tools to call based on which Book fields are still missing.

## Technologies Used

- [mcp-agent](https://mcp-agent.com/) - Agent framework built on Model Context Protocol
- [Google Gemini](https://ai.google.dev/) - Multimodal AI for vision and text processing
- [Pydantic](https://docs.pydantic.dev/) - Data validation and structured outputs
