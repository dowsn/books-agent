# Book ISBN Extractor

A fully autonomous AI agent using the mcp-agent framework with Google Gemini vision to extract ISBN and book metadata from cover images, then intelligently enrich with web data. Supports multilingual books with German output.

## How It Works

The book extractor uses a fully autonomous agent that orchestrates all tools:

### 🤖 Fully Autonomous Workflow

The agent autonomously executes the complete workflow without manual steps:

**Tools Available:**
1. `extract_from_photo` - Gemini vision extracts visible metadata (ISBN, title, authors, publisher, year)
2. `search_google_books` - PRIMARY: Calls Google Books API for complete data
3. `search_open_library` - FALLBACK: Alternative book database
4. `search_brave` - LAST RESORT: Web search if both APIs fail (optional)

**Autonomous Execution:**
1. Agent calls `extract_from_photo` to get ISBN and visible metadata
2. Agent calls `search_google_books` for description, topics, genre, language
3. If fields missing, agent calls `search_open_library` as fallback
4. If description still missing, agent tries `search_brave` (if API key available)
5. Agent merges all data, converts types, and returns complete Book object

### 🌍 Language Support

**German Language Output:**
- **German books**: All fields in German (title, description, topics, genre)
- **Foreign books**: Original title preserved, but description/topics/genre translated to German
- Example: English book "The Great Gatsby" → title: "The Great Gatsby", description: "Roman über..." (German)

**Book Fields (all strings):**
- `isbn` - ISBN-10 or ISBN-13
- `title` - Original title (German for German books, original language for foreign books)
- `authors` - Author name(s)
- `publisher` - Publisher name
- `published_year` - Publication year
- `location` - City/location of publication
- `description` - Book description in German
- `topic` - Book topics/categories in German
- `genre` - Book genre in German
- `page_count` - Number of pages
- `language` - Language code (de, en, cs, etc.)

### 🎯 Key Features
- **Fully autonomous**: Single agent orchestrates ALL tools (photo extraction + web enrichment)
- **German support**: Outputs descriptions/topics in German for all books
- **Smart fallbacks**: Waterfall strategy ensures complete data
- **Type-safe**: All fields returned as strings for consistency
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
1. Call `extract_from_photo` to get ISBN, title, authors from image
2. Call `search_google_books(isbn)` for description, language, topics
3. If any fields still missing, call `search_open_library(isbn)` as fallback
4. If description still missing and Brave API available, call `search_brave(query)`
5. Translate description/topics/genre to German if book is not German
6. Merge all data and display complete Book object

**Example Output (German book):**
```
📚 Complete Book Information:
============================================================
Title: Der Richter und sein Henker
Authors: Friedrich Dürrenmatt
ISBN: 9783423114628
Publisher: dtv
Year: 2003
Location: München
Language: de
Topic: Kriminalromane, Schweizer Literatur
Genre: Krimi, Roman
Pages: 144
Description: In seinem Kriminalroman »Der Richter und sein Henker« schildert...
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
    """Gemini vision extracts ISBN, title, authors, publisher, year"""

@app.tool()
async def search_google_books(isbn: str) -> dict:
    """Calls Google Books API for description, language, topics, genre"""

@app.tool()
async def search_open_library(isbn: str) -> dict:
    """Calls Open Library API as fallback"""

@app.tool()
async def search_brave(query: str) -> dict:
    """Web search as last resort (requires BRAVE_API_KEY)"""
```

The agent receives comprehensive instructions and autonomously:
- Calls `extract_from_photo` as first step to get the image path
- Orchestrates the waterfall strategy based on which Book fields are missing
- Translates descriptions/topics to German for non-German books
- Merges data from all sources with proper type conversions

## Technologies Used

- [mcp-agent](https://mcp-agent.com/) - Agent framework built on Model Context Protocol
- [Google Gemini](https://ai.google.dev/) - Multimodal AI for vision and text processing
- [Pydantic](https://docs.pydantic.dev/) - Data validation and structured outputs
