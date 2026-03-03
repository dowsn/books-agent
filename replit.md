# Book ISBN Extractor - Autonomous Agent

## Project Overview
A production-ready autonomous AI agent using mcp-agent framework with Google Gemini vision that extracts ISBN and book metadata from cover images, then intelligently enriches the data using a multi-source waterfall strategy. All output fields are in German.

## Current Architecture (March 2026)

### Tool Pipeline (in execution order)

1. **`extract_from_photo(image_path)`** — Gemini Vision
   - Extracts ISBN, title, author, publisher, year from book cover image
   - Returns ONLY visible metadata; never returns description
   - Full `try/except` — returns `{"error": ...}` on any failure

2. **`search_dnb_sru(isbn)`** — Deutsche Nationalbibliothek SRU XML API
   - Primary structured metadata source; no API key required
   - Parses MARC21 XML fields: title (`245$a`), subtitle (`245$b`), author (`100$a`),
     publisher (`264$b`), location (`264$a`), year (`264$c`), edition (`250$a`),
     series (`490$a/$v`), language (`041$a`), pages (`300$a`), subjects (`650$a`, `689$a`),
     description/notes (`520$a` or `500$a`), DDC codes (`082$a`)
   - Endpoint: `https://services.dnb.de/sru/dnb?...&recordSchema=MARC21-xml`

3. **`search_google_books(isbn)`** — Google Books API
   - Best for longer descriptions (English, translated by agent to German) and genre categories
   - No API key needed
   - Endpoint: `https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}`

4. **`search_open_library(isbn)`** — Open Library API
   - Fallback if above tools miss fields
   - Endpoint: `https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=details`

5. **MCP Brave Search** — Last resort
   - Only called if description still missing and `BRAVE_API_KEY` is set
   - Single MCP server configured in `mcp_agent.config.yaml`

### Data Merging Priority
- **isbn, title, authors**: prefer photo data (most reliable OCR source)
- **publisher, location, published_year, language, page_count, edition, series, subtitle**: prefer DNB SRU
- **description**: DNB SRU note/annotation if present (already German); otherwise Google Books translated
- **topic, genre**: prefer Google Books (translated to German)
- **source**: `"photo+web"` if merged, `"photo"` if only photo, `"web"` if only web

### Language Requirements
- German books: keep all content in German
- Foreign books: keep ORIGINAL title, translate description/topic/genre to German
- DNB portal description is usually already in German — preferred over Google Books

## File Structure
```
├── src/
│   ├── models.py                    — Pydantic models: Book, BookPhotoExtraction
│   └── book_extractor.py            — Autonomous agent with 5 custom tools + MCP
├── files/
│   └── book.png                     — Book cover image for testing
├── mcp_agent.config.yaml            — MCP server config (Brave Search)
├── mcp_agent.config.yaml.example    — Example config without secrets
├── mcp_agent.secrets.yaml.example   — Example secrets file
└── replit.md                        — This file
```

## Book Model Fields (all strings)
- `isbn` — ISBN-10 or ISBN-13
- `title` — Original book title
- `authors` — Author name(s), comma-separated
- `publisher` — Publisher name
- `published_year` — Publication year as string (e.g. "2023")
- `location` — City of publication
- `description` — Book description IN GERMAN
- `topic` — Topics/categories IN GERMAN
- `genre` — Genre IN GERMAN
- `page_count` — Number of pages as string (e.g. "300")
- `language` — Language code: "de", "en", "cs", etc.
- `source` — "photo", "web", or "photo+web"

## Required Environment Variables
| Variable | Required | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | ✅ Yes | Gemini vision for photo extraction |
| `FIRECRAWL_API_KEY` | Recommended | DNB portal enrichment via Firecrawl |
| `BRAVE_API_KEY` | Optional | Last-resort web search fallback |

**Firecrawl note:** Key may be stored without `fc-` prefix — code auto-corrects this.

## Technology Stack
- **mcp-agent** — Agent framework for autonomous tool orchestration
- **Google Gemini 2.0 Flash** — Multimodal AI for vision OCR
- **firecrawl-py 4.18.0** — JS-rendering web scraper (`AsyncV1FirecrawlApp`)
- **httpx** — Async HTTP client for DNB SRU, Google Books, Open Library
- **xml.etree.ElementTree** — MARC21 XML parser for DNB SRU responses
- **Pydantic** — Data validation and structured outputs
- **Python 3.11** — Runtime environment

## Key Design Decisions

### Why `search_dnb_portal` replaced `search_kvk`
KVK (Karlsruher Virtueller Katalog) renders its search results via internal CGI JavaScript that Firecrawl cannot capture even with 15+ second wait times. The DNB portal, by contrast, serves fully static HTML for its full record pages and yields complete structured book data via Firecrawl's AI extraction in one call.

### Why Firecrawl's `extract` format vs `markdown`
The `extract` format uses an AI model (internally) to fill a JSON schema from the raw page content. This is more reliable than regex-parsing markdown and handles varied page layouts gracefully.

### Why not use the Firecrawl SDK for all HTTP calls?
The `search_dnb_sru`, `search_google_books`, and `search_open_library` tools all target REST APIs that return structured JSON or XML directly — no JavaScript rendering needed. Using raw `httpx` for these saves Firecrawl credits for the DNB portal where it actually adds value.
