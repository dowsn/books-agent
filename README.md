# Book ISBN Extractor

An intelligent agent using the mcp-agent framework with Google Gemini vision to extract ISBN and book metadata from cover images, then enrich with web data from Google Books API.

## How It Works

The book extractor uses an intelligent agent-based workflow:

### 🔍 Step 1: Vision OCR (Gemini 2.0 Flash)
- Extracts ISBN, title, author, publisher, year from book cover image
- Uses Gemini vision API for accurate OCR
- **No description from photos** - only visible metadata

### 🌐 Step 2: Web Enrichment (Autonomous Agent)
The agent autonomously collects missing data using a waterfall strategy:
1. **Google Books API** - Primary source for description, language, categories
2. **Open Library API** - Fallback if Google Books fails or has missing data
3. **Brave Search** - Last resort (optional, requires free API key)

The agent intelligently tracks which fields it has and only calls APIs when needed!

### 🎯 Key Features
- **mcp-agent framework**: Autonomous agent with tool access
- **Gemini vision**: Accurate ISBN and metadata extraction
- **MCP fetch server**: HTTP requests to Google Books API
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

The agent will automatically:
1. Extract ISBN and metadata from the image using Gemini vision
2. Connect to the fetch MCP server
3. Call Google Books API with the ISBN
4. Retrieve complete book information (description, language, categories)
5. Display merged results with source attribution

**Example Output:**
```
📚 Complete Book Information:
============================================================
Author: Kateřina Tučková
ISBN: 978-80-275-1365-9
Publisher: Host
Year: 2022
Language: cs
Description: [Full description from Google Books API...]
Source: photo+web
============================================================
```

## Project Structure

```
├── src/
│   ├── models.py           - Pydantic models (Book, BookPhotoExtraction)
│   ├── book_extractor.py   - Main agent with vision + web enrichment
│   ├── book_agent.py       - Legacy implementation (deprecated)
│   └── web_enrichment.py   - Helper functions (deprecated)
├── files/
│   └── book.png            - Book cover image for extraction
├── mcp_agent.config.yaml   - MCP server configuration
└── README.md               - This file
```

## Technologies Used

- [mcp-agent](https://mcp-agent.com/) - Agent framework built on Model Context Protocol
- [Google Gemini](https://ai.google.dev/) - Multimodal AI for vision and text processing
- [Pydantic](https://docs.pydantic.dev/) - Data validation and structured outputs
