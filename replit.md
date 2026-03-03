# Book ISBN Extractor - Autonomous Agent

## Project Overview
A production-ready autonomous AI agent using mcp-agent framework with Google Gemini vision that extracts ISBN and book metadata from cover images, then intelligently enriches the data using a multi-source waterfall strategy. All output fields are in German.

## Current Architecture (March 2026)

### Tool Pipeline (in execution order)

1. **`extract_from_photo(image_path)`** — Gemini Vision
   - Extracts ISBN, title, author, publisher, year from book cover image
   - Returns ONLY visible metadata; never returns description

2. **`search_dnb_sru(isbn)`** — Deutsche Nationalbibliothek SRU XML API
   - Primary structured metadata source; no API key required
   - Returns: title, author, publisher, location, year, language, page_count, subjects
   - Endpoint: `https://services.dnb.de/sru/dnb?...&recordSchema=MARC21-xml`
   - Best source for German-language books

3. **`search_dnb_portal(isbn)`** — DNB Web Portal via Firecrawl (NEW)
   - Enriches DNB SRU data with fields the XML API omits
   - Returns: subtitle, edition, series, description (annotation, usually already in German)
   - Uses `AsyncV1FirecrawlApp` with structured JSON extraction (`extract` format)
   - Requires `FIRECRAWL_API_KEY`; handles missing `fc-` prefix automatically
   - Endpoint: `https://portal.dnb.de/opac/showFullRecord?currentResultId="{isbn}"%26any&currentPosition=0`

4. **`search_google_books(isbn)`** — Google Books API
   - Best for description (English) and categories; no API key needed
   - Agent translates description and categories to German
   - Endpoint: `https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}`

5. **`search_open_library(isbn)`** — Open Library API
   - Fallback if above tools miss fields
   - Endpoint: `https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=details`

6. **MCP Brave Search** — Last resort
   - Only called if description still missing and `BRAVE_API_KEY` is set
   - Single MCP server configured in `mcp_agent.config.yaml`

### Data Merging Priority
- **isbn, title, authors**: prefer photo data (most reliable OCR source)
- **publisher, location, published_year, language, page_count**: prefer DNB SRU
- **subtitle, edition, series, description**: prefer DNB portal (Firecrawl)
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
