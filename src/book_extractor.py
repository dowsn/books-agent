import asyncio
import os
import json
from pathlib import Path
from typing import Optional
import httpx

from google import genai
from google.genai import types
from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from mcp_agent.workflows.llm.augmented_llm_google import GoogleAugmentedLLM

from models import Book, BookPhotoExtraction


app = MCPApp(
    name="book_extractor",
    description="Autonomous agent to extract and enrich book information"
)


@app.tool()
async def extract_from_photo(image_path: str) -> dict:
    """
    Extract visible metadata from a book cover image using Gemini vision.
    Returns ONLY information visible on the cover (ISBN, title, author, publisher, year).
    Does NOT return description - that must come from web sources.
    
    Args:
        image_path: Path to the book cover image
    
    Returns:
        Dictionary with extracted fields: isbn, title, author, publisher, year
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    
    client = genai.Client(api_key=api_key)
    
    image_file = Path(image_path)
    if not image_file.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    
    if image_path.lower().endswith(".png"):
        mime_type = "image/png"
    elif image_path.lower().endswith(".webp"):
        mime_type = "image/webp"
    else:
        mime_type = "image/jpeg"
    
    prompt = """Extract ONLY visible information from this book cover:
    
1. ISBN number (ISBN-10 or ISBN-13) - look on back cover or barcode area
2. Book title - main title text
3. Author name(s) - author byline
4. Publisher name - if visible (often on spine or back)
5. Publication year - if visible

CRITICAL: Do NOT include description or summary. Return ONLY what you can physically SEE.

Return JSON with these exact fields (use null if not visible):
{
  "isbn": "string or null",
  "title": "string or null", 
  "author": "string or null",
  "publisher": "string or null",
  "year": "string or null"
}"""
    
    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            prompt,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=BookPhotoExtraction,
        ),
    )
    
    if response.text:
        return json.loads(response.text)
    else:
        return {
            "isbn": None,
            "title": None,
            "author": None,
            "publisher": None,
            "year": None
        }


@app.tool()
async def search_google_books(isbn: str) -> dict:
    """
    Search Google Books API for complete book information using ISBN.
    Returns description, language, categories, page_count, and other metadata.
    Note: Agent should translate description/categories to German for non-German books.
    
    Args:
        isbn: The ISBN number to search for
    
    Returns:
        Dictionary with book data from Google Books API, or empty dict if not found
    """
    if not isbn:
        return {"error": "No ISBN provided"}
    
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            if data.get("totalItems", 0) == 0:
                return {"error": "No results found in Google Books"}
            
            volume_info = data["items"][0].get("volumeInfo", {})
            
            # Extract and structure the data
            result = {
                "title": volume_info.get("title"),
                "authors": volume_info.get("authors", []),
                "publisher": volume_info.get("publisher"),
                "published_date": volume_info.get("publishedDate"),
                "description": volume_info.get("description"),
                "language": volume_info.get("language"),
                "categories": volume_info.get("categories", []),
                "page_count": volume_info.get("pageCount"),
                "source": "google_books"
            }
            
            return result
            
        except Exception as e:
            return {"error": f"Google Books API error: {str(e)}"}


@app.tool()
async def search_open_library(isbn: str) -> dict:
    """
    Search Open Library API for book information using ISBN.
    Used as fallback when Google Books doesn't have complete data.
    Note: No MCP server available for Open Library, so using direct API call.
    Note: Agent should translate description/subjects to German for non-German books.
    
    Args:
        isbn: The ISBN number to search for
    
    Returns:
        Dictionary with book data from Open Library, or empty dict if not found
    """
    if not isbn:
        return {"error": "No ISBN provided"}
    
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=details"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()
            
            key = f"ISBN:{isbn}"
            if key not in data:
                return {"error": "No results found in Open Library"}
            
            details = data[key].get("details", {})
            
            # Extract and structure the data
            description = details.get("description")
            if isinstance(description, dict):
                description = description.get("value")
            
            authors = details.get("authors", [])
            author_names = [a.get("name") for a in authors if isinstance(a, dict)]
            
            result = {
                "title": details.get("title"),
                "authors": author_names,
                "publisher": details.get("publishers", [None])[0] if details.get("publishers") else None,
                "published_date": details.get("publish_date"),
                "description": description,
                "language": None,  # Open Library doesn't always have language
                "categories": details.get("subjects", []),
                "page_count": details.get("number_of_pages"),
                "source": "open_library"
            }
            
            return result
            
        except Exception as e:
            return {"error": f"Open Library API error: {str(e)}"}



async def collect_book_data(image_path: str) -> Book:
    """
    Fully autonomous agent that collects complete book information.
    
    The agent autonomously:
    1. Calls extract_from_photo to get visible metadata
    2. Calls search_google_books for web enrichment
    3. Falls back to search_open_library if needed
    4. Falls back to search_brave if available and needed
    5. Merges all data and returns complete Book object
    
    Args:
        image_path: Path to book cover image
    
    Returns:
        Complete Book object with all available data
    """
    async with app.run() as agent_app:
        logger = agent_app.logger
        
        print(f"🤖 Starting fully autonomous book data collection...")
        print(f"📖 Image: {image_path}\n")
        
        # Check if Brave Search is available
        has_brave = bool(os.environ.get("BRAVE_API_KEY"))
        brave_status = "✓ Brave Search available" if has_brave else "○ Brave Search not configured (optional)"
        print(f"🔧 Available tools:")
        print(f"   ✓ Gemini Vision (extract_from_photo)")
        print(f"   ✓ Google Books API")
        print(f"   ✓ Open Library API")
        print(f"   {brave_status}\n")
        
        print(f"🌐 Launching autonomous agent to orchestrate all tools...")
        
        # Create fully autonomous agent that calls ALL tools
        book_agent = Agent(
            name="book_collector",
            instruction=f"""You are a fully autonomous book data collector. Your goal is to build a COMPLETE Book object by orchestrating ALL available tools.

IMAGE PATH: {image_path}

YOUR AVAILABLE TOOLS:
1. extract_from_photo(image_path) - Extract ISBN, title, author, publisher, year from book cover image
2. search_google_books(isbn) - PRIMARY web source for description/metadata
3. search_open_library(isbn) - FALLBACK web source for book metadata
4. MCP Brave Search tools - LAST RESORT web search (via Model Context Protocol, if API key available)

REQUIRED BOOK FIELDS (fill ALL):
- isbn: ISBN-10 or ISBN-13 (STRING)
- title: Original title (for German books keep German, for foreign books keep original language title) (STRING)
- authors: Author name(s) (STRING)
- publisher: Publisher name (STRING)
- published_year: Publication year (STRING, not integer!)
- location: City/location of publication (STRING)
- description: Book description IN GERMAN regardless of book language (STRING, MUST be from web, NEVER from photo!)
- topic: Book topics/categories IN GERMAN (STRING)
- genre: Book genre IN GERMAN (STRING)
- page_count: Number of pages (STRING, not integer!)
- language: Language code (e.g., "de", "en", "cs") (STRING)
- source: "photo", "web", or "photo+web" (STRING)

AUTONOMOUS WORKFLOW:

STEP 1: Extract from photo
- Call: extract_from_photo("{image_path}")
- Get: isbn, title, author, publisher, year (if visible on cover)

STEP 2: Enrich with Google Books
- Call: search_google_books(isbn_from_step1)
- Get: description (translate to German!), language, categories (translate to German!), page_count, publisher, published_date
- IMPORTANT: If book is not German, you MUST translate description and categories to German

STEP 3: Fill gaps with Open Library (if needed)
- If critical fields still missing, call: search_open_library(isbn)
- Fill any remaining gaps
- IMPORTANT: Translate description/subjects to German if needed

STEP 4: Last resort - Brave Search (if needed and available)
- If description still missing AND BRAVE_API_KEY is available, use MCP Brave Search tools
- Extract missing info from search results
- IMPORTANT: Translate to German if needed
- NOTE: Brave Search MCP server is available but requires valid API key

LANGUAGE REQUIREMENTS (CRITICAL):
- For GERMAN books (language: "de"): Keep title in German, description in German, topics in German
- For FOREIGN books (language: anything else): Keep ORIGINAL title, but translate description/topics/genre to GERMAN
- Example: English book "The Great Gatsby" → title: "The Great Gatsby", description: "Roman über..." (in German)
- Example: Czech book "Bílá Voda" → title: "Bílá Voda", description: "..." (in German if available, or translate)

DATA MERGING RULES:
1. Prefer photo data for: isbn, title (original title), authors
2. Prefer web data for: publisher, published_year, location, description, topic, genre, page_count, language
3. Source attribution:
   - "photo" if only photo data
   - "web" if only web data  
   - "photo+web" if merged (most common)

TYPE CONVERSION RULES (CRITICAL):
- published_year: Convert integer 2023 → string "2023"
- page_count: Convert integer 300 → string "300"
- topic: Join array ["Fiction", "Mystery"] → string "Fiction, Mystery" (in German!)
- genre: Derive from categories/topics (in German)

OUTPUT: Return JSON with ALL fields:
{{
  "isbn": "978-...",
  "title": "Original Title",
  "authors": "Author Name",
  "publisher": "Publisher",
  "published_year": "2023",
  "location": "City",
  "description": "Beschreibung auf Deutsch...",
  "topic": "Fiktion, Mysterium",
  "genre": "Roman",
  "page_count": "300",
  "language": "en",
  "source": "photo+web"
}}

If a field is unavailable after all attempts, use null.

START NOW: Call extract_from_photo first, then proceed with web enrichment.""",
        )
        
        async with book_agent:
            logger.info("book_collector: Fully autonomous agent initialized")
            
            # Attach LLM to agent
            llm = await book_agent.attach_llm(
                lambda agent: GoogleAugmentedLLM(model="gemini-2.0-flash-exp", agent=agent)
            )
            
            # Let agent autonomously orchestrate ALL tools
            response_text = await llm.generate_str(
                message="Collect complete book data by calling all necessary tools. Start with extract_from_photo, then enrich with web sources. Return only the final merged JSON with all fields."
            )
            
            logger.info("book_collector: Autonomous collection complete")
            
            # Parse response
            response_text = response_text.strip()
            
            # Strip markdown code fences if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            elif response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            try:
                book_data = json.loads(response_text)
                book = Book(**book_data)
                
                print(f"\n✅ Autonomous collection complete!")
                print(f"\n📚 Complete Book Information:")
                print("=" * 60)
                if book.title:
                    print(f"Title: {book.title}")
                if book.authors:
                    print(f"Authors: {book.authors}")
                if book.isbn:
                    print(f"ISBN: {book.isbn}")
                if book.publisher:
                    print(f"Publisher: {book.publisher}")
                if book.published_year:
                    print(f"Year: {book.published_year}")
                if book.location:
                    print(f"Location: {book.location}")
                if book.language:
                    print(f"Language: {book.language}")
                if book.topic:
                    print(f"Topic: {book.topic}")
                if book.genre:
                    print(f"Genre: {book.genre}")
                if book.page_count:
                    print(f"Pages: {book.page_count}")
                if book.description:
                    desc_preview = book.description[:200] + "..." if len(book.description) > 200 else book.description
                    print(f"Description: {desc_preview}")
                print(f"Source: {book.source}")
                print("=" * 60)
                
                return book
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse agent response: {e}")
                logger.error(f"Response was: {response_text}")
                # Return minimal book object
                return Book(
                    isbn=None,
                    title=None,
                    authors=None,
                    publisher=None,
                    published_year=None,
                    location=None,
                    description=None,
                    topic=None,
                    genre=None,
                    page_count=None,
                    language=None,
                    source="error"
                )


async def main():
    """Main entry point for the book extractor"""
    image_path = "files/book.png"
    
    if not Path(image_path).exists():
        print(f"❌ Error: Image not found at {image_path}")
        print(f"Please place a book cover image at this location.")
        return
    
    print(f"🔍 Processing book cover: {image_path}")
    book = await collect_book_data(image_path)
    print(f"\n✅ Processing complete!")


if __name__ == "__main__":
    asyncio.run(main())
