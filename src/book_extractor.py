import asyncio
import os
import json
from pathlib import Path
from typing import Optional

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
async def extract_from_photo(image_path: str) -> str:
    """
    Extract visible metadata from a book cover image using Gemini vision.
    Returns ONLY information visible on the cover (ISBN, title, author, publisher, year).
    Does NOT return description - that must come from web sources.
    
    Args:
        image_path: Path to the book cover image
    
    Returns:
        JSON string with extracted fields: isbn, title, author, publisher, year
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
        return response.text
    else:
        return json.dumps({
            "isbn": None,
            "title": None,
            "author": None,
            "publisher": None,
            "year": None
        })


@app.tool()
async def collect_book_data(image_path: str) -> str:
    """
    Autonomous agent that collects complete book information using a waterfall strategy.
    
    The agent will:
    1. Extract visible data from photo using extract_from_photo tool
    2. Try Google Books API for missing fields
    3. Try Open Library API if still missing data  
    4. Try Brave Search as last resort (if API key available)
    
    Args:
        image_path: Path to book cover image
    
    Returns:
        Complete book information as JSON with source attribution
    """
    async with app.run() as agent_app:
        logger = agent_app.logger
        
        print(f"🤖 Starting autonomous book data collection...")
        print(f"📖 Image: {image_path}\n")
        
        # First, extract photo data that agent will use
        print(f"📸 Extracting visible metadata from image...")
        photo_json = await extract_from_photo(image_path)
        photo_data = json.loads(photo_json)
        
        print(f"   ✓ Photo extraction complete")
        if photo_data.get("isbn"):
            print(f"   ✓ Found ISBN: {photo_data['isbn']}")
        if photo_data.get("title"):
            print(f"   ✓ Found Title: {photo_data['title']}")
        if photo_data.get("author"):
            print(f"   ✓ Found Author: {photo_data['author']}")
        
        print(f"\n🌐 Enriching with web data using autonomous agent...")
        
        # Check if Brave Search is available
        has_brave = bool(os.environ.get("BRAVE_API_KEY"))
        brave_note = "Brave Search API key detected - use as last resort." if has_brave else "No Brave API key - skip Brave Search."
        
        # Create fully autonomous agent with web tools
        book_agent = Agent(
            name="book_collector",
            instruction=f"""You are an autonomous book information collector. Your goal is to enrich the photo data with complete book information using web APIs.

PHOTO DATA ALREADY EXTRACTED:
{json.dumps(photo_data, indent=2)}

NOTE: {brave_note}

REQUIRED FIELDS FOR FINAL OUTPUT:
- isbn (string) - from photo
- title (string) - from photo
- author (string) - from photo
- publisher (string) - from photo or web
- year (string) - from photo or web
- description (string) - MUST be from web, NEVER from photo!
- language (string) - from web
- categories (string) - from web
- page_count (integer) - from web

=== WATERFALL STRATEGY ===

STEP 1: You already have photo data (see above)
The photo provided: isbn, title, author, publisher (maybe), year (maybe)
Note: Photo data does NOT include description - that's intentional!

STEP 2: Google Books API (if any fields still missing)
Use fetch tool to call:
URL: https://www.googleapis.com/books/v1/volumes?q=isbn:{{isbn}}

Parse JSON response structure:
{{
  "totalItems": 0 or 1+,
  "items": [
    {{
      "volumeInfo": {{
        "title": "...",
        "authors": ["..."],
        "publisher": "...",
        "publishedDate": "YYYY-MM-DD",
        "description": "...",  <-- CRITICAL for description!
        "pageCount": 123,
        "categories": ["Fiction", "Mystery"],
        "language": "en"
      }}
    }}
  ]
}}

Extract from items[0].volumeInfo:
- description: volumeInfo.description (required!)
- language: volumeInfo.language
- categories: join volumeInfo.categories with ", "
- page_count: volumeInfo.pageCount
- Also fill any missing: publisher, year (from publishedDate)

STEP 3: Open Library API (if Google Books fails or fields still missing)
Try these Open Library endpoints:

A) By ISBN:
URL: https://openlibrary.org/api/books?bibkeys=ISBN:{{isbn}}&format=json&jscmd=details

Response structure:
{{
  "ISBN:XXX": {{
    "details": {{
      "title": "...",
      "authors": [{{"name": "..."}}],
      "publishers": ["..."],
      "publish_date": "...",
      "description": "..." or {{"value": "..."}},
      "number_of_pages": 123,
      "subjects": ["Fiction", "Mystery"]
    }}
  }}
}}

B) By title+author search (if ISBN lookup fails):
URL: https://openlibrary.org/search.json?title={{title}}&author={{author}}

STEP 4: Brave Search (LAST RESORT - only if BRAVE_API_KEY available and description still missing)
If Brave API key is available and description is still null, search for book info:
This is a last resort - only use if both Google Books and Open Library failed to provide description.

=== DATA MERGING RULES ===

1. Keep photo data for: isbn, title, author, publisher, year
2. Web data fills missing fields and adds: description, language, categories, page_count
3. Description MUST come from web (Google Books or Open Library)
4. Prefer Google Books over Open Library for description quality
5. Source attribution:
   - "photo" if all data from photo only
   - "web" if all data from web only  
   - "photo+web" if merged from both

=== OUTPUT FORMAT ===

Return JSON with ALL fields filled:
{{
  "isbn": "978-...",
  "title": "Book Title",
  "author": "Author Name",
  "publisher": "Publisher",
  "year": "2023",
  "description": "Complete description from web API",
  "language": "en",
  "categories": "Fiction, Mystery",
  "page_count": 300,
  "source": "photo+web"
}}

If a field is truly unavailable from all sources, use null.
NEVER use placeholder text like "Not available" - use null instead.

BEGIN COLLECTION NOW.""",
            server_names=["fetch"],
        )
        
        async with book_agent:
            logger.info("book_collector: Agent started with fetch tool for web APIs")
            
            # Attach LLM to agent  
            llm = await book_agent.attach_llm(
                lambda agent: GoogleAugmentedLLM(model="gemini-2.0-flash-exp", agent=agent)
            )
            
            # Let agent autonomously collect data
            response_text = await llm.generate_str(
                message="Collect complete book data using the waterfall strategy described in your instructions."
            )
            
            logger.info(f"book_collector: Agent completed collection")
            
            # Strip markdown code fences if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
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
                
                return response_text
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse agent response as JSON: {e}")
                logger.error(f"Response was: {response_text}")
                return json.dumps({"error": "Failed to parse agent response"})


async def main():
    """Main entry point for the book extractor"""
    image_path = "files/book.png"
    
    if not Path(image_path).exists():
        print(f"❌ Error: Image not found at {image_path}")
        print(f"Please place a book cover image at this location.")
        return
    
    print(f"🔍 Processing book cover: {image_path}")
    result = await collect_book_data(image_path)
    print(f"\n✅ Processing complete!")


if __name__ == "__main__":
    asyncio.run(main())
