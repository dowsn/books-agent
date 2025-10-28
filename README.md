# Book ISBN Extractor Agent

A proof-of-concept agent using the mcp-agent framework with Google Gemini's vision capabilities to extract ISBN numbers and book metadata from book cover images.

## Features

- Extract ISBN-10 and ISBN-13 from book cover images
- Extract book title, author, publisher, and publication year
- Uses Gemini 2.0 Flash with vision capabilities
- Built on the mcp-agent framework

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
python book_agent.py
```

The agent will analyze the image and extract:
- ISBN number
- Title
- Author
- Publisher
- Publication year
- Brief description

## Project Structure

- `models.py` - Pydantic data model for Book information
- `book_agent.py` - Main agent implementation using mcp-agent and Gemini vision
- `test_book_cover.jpg` - Sample book cover image for testing

## Technologies Used

- [mcp-agent](https://mcp-agent.com/) - Agent framework built on Model Context Protocol
- [Google Gemini](https://ai.google.dev/) - Multimodal AI for vision and text processing
- [Pydantic](https://docs.pydantic.dev/) - Data validation and structured outputs
