# Book ISBN Extractor Agent

A proof-of-concept agent using the mcp-agent framework with Google Gemini's vision capabilities to extract ISBN numbers and book metadata from book cover images.

## Features

### Two-Step Extraction Process

**Step 1: Photo Analysis (Gemini Vision)**
- Extract ISBN-10 and ISBN-13 from book cover images
- Extract book title, author, publisher, and publication year
- OCR recognition from visible text on the book cover
- ⚠️ **No description from photos** - only metadata

**Step 2: Web Enrichment (Google Books API)**
- Fetches complete book information using ISBN
- Adds description, categories, language, page count
- Provides fallback search using title + author if no ISBN
- Enriches photo data with web metadata

### Technology
- Uses Gemini 2.0 Flash with vision capabilities
- Google Books API for web enrichment
- Built on the mcp-agent framework
- Source tracking: shows "photo", "web", or "photo+web"

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your Gemini API key:
   - Get a free API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Add it to your environment as `GEMINI_API_KEY`

## Usage

Place a book cover image in the project directory named `test_book_cover.jpg` and run:

```bash
python src/book_agent.py
```

Or use the example script:

```bash
python src/example_usage.py
```

The agent will:
1. **Analyze the image** and extract:
   - ISBN number
   - Title
   - Author
   - Publisher
   - Publication year

2. **Enrich with web data** to add:
   - Description (from web, never from photo!)
   - Categories/genres
   - Language
   - Page count
   - Additional metadata

## Project Structure

```
├── src/
│   ├── models.py          - Pydantic data model for Book information
│   ├── book_agent.py      - Main agent using mcp-agent + Gemini vision
│   └── example_usage.py   - Usage examples and batch processing
├── test_book_cover.jpg    - Sample book cover image for testing
└── README.md              - This file
```

## Technologies Used

- [mcp-agent](https://mcp-agent.com/) - Agent framework built on Model Context Protocol
- [Google Gemini](https://ai.google.dev/) - Multimodal AI for vision and text processing
- [Pydantic](https://docs.pydantic.dev/) - Data validation and structured outputs
