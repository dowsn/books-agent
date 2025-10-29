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
    Autonomous agent that collects complete book information.
    
    The agent:
    1. Extracts visible data from photo
    2. Calls search_google_books for web enrichment
    3. Falls back to search_open_library if needed
    4. Falls back to Brave Search MCP if available and needed
    5. Merges all data and returns complete Book object
    
    Args:
        image_path: Path to book cover image
    
    Returns:
        Complete Book object with all available data
    """
    async with app.run() as agent_app:
        logger = agent_app.logger
        
        print(f"🤖 Starting autonomous book data collection...")
        print(f"📖 Image: {image_path}\n")
        
        # Step 1: Extract photo data
        print(f"📸 Step 1: Extracting visible metadata from image...")
        photo_data = await extract_from_photo(image_path)
        
        print(f"   ✓ Photo extraction complete")
        if photo_data.get("isbn"):
            print(f"   ✓ Found ISBN: {photo_data['isbn']}")
        if photo_data.get("title"):
            print(f"   ✓ Found Title: {photo_data['title']}")
        if photo_data.get("author"):
            print(f"   ✓ Found Author: {photo_data['author']}")
        
        # Check if Brave Search MCP is available
        has_brave = bool(os.environ.get("BRAVE_API_KEY"))
        brave_status = "✓ Brave Search available" if has_brave else "○ Brave Search not configured (optional)"
        print(f"\n🔧 Available tools:")
        print(f"   ✓ Google Books API")
        print(f"   ✓ Open Library API")
        print(f"   {brave_status}")
        
        print(f"\n🌐 Step 2: Enriching with web data using autonomous agent...")
        
        # Determine which MCP servers to use
        server_names = []
        if has_brave:
            server_names.append("brave-search")
        
        # Create autonomous agent with all tools
        book_agent = Agent(
            name="book_collector",
            instruction=f"""You are an autonomous book data collector. Your goal is to build a COMPLETE Book object by collecting data from multiple sources.

PHOTO DATA (already extracted):
{json.dumps(photo_data, indent=2)}

YOUR TOOLS:
1. search_google_books(isbn) - PRIMARY source, best for description/metadata
2. search_open_library(isbn) - FALLBACK source if Google Books missing data
3. brave_search (MCP) - LAST RESORT if both APIs fail (only if available)

REQUIRED BOOK FIELDS (your goal is to fill ALL of these):
- isbn: {photo_data.get('isbn', 'MISSING')}
- title: {photo_data.get('title', 'MISSING')}  
- author: {photo_data.get('author', 'MISSING')}
- publisher: {photo_data.get('publisher') or 'MISSING - get from web'}
- year: {photo_data.get('year') or 'MISSING - get from web'}
- description: MISSING - MUST get from web, NEVER from photo!
- language: MISSING - get from web
- categories: MISSING - get from web  
- page_count: MISSING - get from web

WATERFALL STRATEGY:

STEP 1: Call search_google_books('{photo_data.get('isbn', '')}')
- Parse the response
- Fill in: description, language, categories, page_count
- Also use: publisher, year if missing from photo

STEP 2: Check what's still MISSING
- If description is null → call search_open_library('{photo_data.get('isbn', '')}')
- If other fields null → call search_open_library for those too

STEP 3: If STILL missing critical data (especially description)
- Only if Brave Search is available
- Search for: "{photo_data.get('title', '')} {photo_data.get('author', '')} book"
- Extract missing information from search results

DATA MERGING RULES:
1. Keep photo data for: isbn, title, author (these are most reliable from image)
2. Prefer Google Books for: description, language, categories, page_count
3. Use Open Library to fill gaps
4. Prefer web sources over photo for: publisher, year (more accurate)
5. Source field:
   - "photo" if only photo data
   - "web" if only web data
   - "photo+web" if merged (most common)

OUTPUT: Return JSON with ALL fields filled:
{{
  "isbn": "978-...",
  "title": "Book Title",
  "author": "Author Name",
  "publisher": "Publisher",
  "year": "2023",
  "description": "Complete description from web API (NEVER from photo)",
  "language": "en",
  "categories": "Fiction, Mystery",
  "page_count": 300,
  "source": "photo+web"
}}

If a field is truly unavailable after trying all sources, use null (not "Not available").

START NOW: Call search_google_books first, then continue as needed.""",
            server_names=server_names,
        )
        
        async with book_agent:
            logger.info("book_collector: Agent initialized with all tools")
            
            # Attach LLM to agent
            llm = await book_agent.attach_llm(
                lambda agent: GoogleAugmentedLLM(model="gemini-2.0-flash-exp", agent=agent)
            )
            
            # Let agent autonomously collect and merge data
            response_text = await llm.generate_str(
                message="Collect complete book data following the waterfall strategy. Return only the final merged JSON."
            )
            
            logger.info("book_collector: Data collection complete")
            
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
                
                print(f"\n✅ Collection complete!")
                print(f"\n📚 Complete Book Information:")
                print("=" * 60)
                if book.title:
                    print(f"Title: {book.title}")
                if book.author:
                    print(f"Author: {book.author}")
                if book.isbn:
                    print(f"ISBN: {book.isbn}")
                if book.publisher:
                    print(f"Publisher: {book.publisher}")
                if book.year:
                    print(f"Year: {book.year}")
                if book.language:
                    print(f"Language: {book.language}")
                if book.categories:
                    print(f"Categories: {book.categories}")
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
                # Return book with just photo data
                return Book(
                    isbn=photo_data.get("isbn"),
                    title=photo_data.get("title"),
                    author=photo_data.get("author"),
                    publisher=photo_data.get("publisher"),
                    year=photo_data.get("year"),
                    source="photo"
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
