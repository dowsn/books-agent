# Book ISBN Extractor Agent

## Project Overview
A proof-of-concept AI agent that uses the mcp-agent framework with Google Gemini's vision capabilities to extract ISBN numbers and book metadata from book cover images.

## Purpose
Demonstrate integration between:
- mcp-agent framework (Model Context Protocol)
- Google Gemini multimodal AI (vision + text)
- Structured data extraction from images

## Current State
✅ Initial proof-of-concept implementation complete
- Gemini vision integration working
- Book data model defined with Pydantic
- Local image file processing implemented
- Agent successfully connects to Gemini API

## Recent Changes (October 28, 2025)
- Installed mcp-agent framework with Google Gemini support
- Created Book Pydantic model for structured outputs
- Implemented book_agent.py with Gemini 2.0 Flash vision
- Added test infrastructure and workflow
- Set up Gemini API key via Replit secrets

## Project Architecture

### Files
- `models.py` - Book data model (Pydantic)
- `book_agent.py` - Main agent implementation
- `README.md` - Project documentation
- `test_book_cover.jpg` - Test image (replace with actual book cover)

### Technology Stack
- **mcp-agent**: Agent framework built on Model Context Protocol
- **Google Gemini 2.0 Flash**: Multimodal AI with vision capabilities
- **Pydantic**: Data validation and structured outputs
- **Python 3.11**: Runtime environment

### How It Works
1. Loads a book cover image from local file
2. Sends image to Gemini vision model with extraction prompt
3. Gemini analyzes image and extracts ISBN, title, author, etc.
4. Returns structured Book object with extracted data

## Next Steps
- Replace test image with actual book cover containing visible ISBN
- Add web search integration to fetch complete book info using ISBN
- Support for remote image URLs
- Batch processing for multiple books
- Error handling improvements

## User Preferences
None documented yet.

## Notes
- Stock images typically don't have real ISBN numbers
- For best results, use actual photos of book covers with visible ISBN on back
- Gemini 2.0 Flash Exp model used for vision capabilities
