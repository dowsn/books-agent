import asyncio
import os
import json
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types
from mcp_agent.app import MCPApp
from mcp_agent.config import MCPSettings, MCPServerSettings
from mcp_agent.agents.agent import Agent
from mcp_agent.workflows.llm.augmented_llm_google import GoogleAugmentedLLM

from models import Book, BookPhotoExtraction


app = MCPApp(
    name="book_extractor",
    description="Extract book information from ISBN images and enrich with web data"
)


@app.tool()
async def extract_isbn_from_image(image_path: str) -> BookPhotoExtraction:
    """
    Use Gemini vision to extract ISBN and visible metadata from a book cover image.
    Returns only information visible in the image (NO description).
    
    Args:
        image_path: Path to the book cover image
    
    Returns:
        BookPhotoExtraction with ISBN, title, author, publisher, year (no description)
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
    
1. ISBN number (ISBN-10 or ISBN-13)
2. Book title
3. Author name(s)
4. Publisher name (if visible)
5. Publication year (if visible)

IMPORTANT: Return ONLY what you can SEE. Do NOT include description.

Return JSON with these exact fields:
- isbn (string or null)
- title (string or null)
- author (string or null)
- publisher (string or null)
- year (string or null)"""
    
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
        data = json.loads(response.text)
        return BookPhotoExtraction(**data)
    else:
        return BookPhotoExtraction()


@app.tool()
async def process_book_image(image_path: str) -> str:
    """
    Main workflow: Extract book information from image, enrich with web data.
    
    This is the main entry point that:
    1. Extracts ISBN and metadata from the book cover image using Gemini vision
    2. Uses an intelligent agent to fetch additional data from Google Books API
    3. Falls back to web search if Google Books API doesn't find the book
    
    Args:
        image_path: Path to book cover image
    
    Returns:
        Complete book information with source attribution
    """
    async with app.run() as agent_app:
        logger = agent_app.logger
        context = agent_app.context
        
        print(f"📸 Step 1: Extracting visible data from image...")
        photo_data = await extract_isbn_from_image(image_path)
        
        if photo_data.isbn:
            print(f"   ✓ Found ISBN: {photo_data.isbn}")
        if photo_data.title:
            print(f"   ✓ Found Title: {photo_data.title}")
        if photo_data.author:
            print(f"   ✓ Found Author: {photo_data.author}")
        
        print(f"\n🌐 Step 2: Enriching with web data...")
        
        context.config.mcp = MCPSettings(
            servers={
                "fetch": MCPServerSettings(
                    command="uvx",
                    args=["mcp-server-fetch"],
                ),
            }
        )
        
        book_agent = Agent(
            name="book_researcher",
            instruction=f"""You are a book information researcher. You have access to the fetch tool to make HTTP requests.

From the photo, we extracted:
- ISBN: {photo_data.isbn or 'Not found'}
- Title: {photo_data.title or 'Not found'}
- Author: {photo_data.author or 'Not found'}
- Publisher: {photo_data.publisher or 'Not found'}
- Year: {photo_data.year or 'Not found'}

Your task:
1. First, try to fetch book data from Google Books API using the ISBN (if available)
   URL: https://www.googleapis.com/books/v1/volumes?q=isbn:{photo_data.isbn}
   
2. If no ISBN or Google Books returns no results, try searching by title and author:
   URL: https://www.googleapis.com/books/v1/volumes?q={photo_data.title}+{photo_data.author}

3. If Google Books still returns nothing, try a general web search for the book

Extract from the API response:
- description (CRITICAL: must be from web, never from photo)
- language
- categories
- pageCount
- publisher (if not in photo)
- publishedDate (if not in photo)

Return the enriched data as JSON with these fields:
- description (string or null)
- language (string or null)  
- categories (string or null - comma-separated)
- page_count (integer or null)
- publisher (string or null)
- year (string or null)
- source (string - "web" or "google_books")""",
            server_names=["fetch"],
        )
        
        async with book_agent:
            logger.info("book_researcher: Connected to fetch server")
            
            llm = await book_agent.attach_llm(GoogleAugmentedLLM)
            
            enrichment_query = f"""Find complete book information for:
ISBN: {photo_data.isbn or 'N/A'}
Title: {photo_data.title or 'N/A'}  
Author: {photo_data.author or 'N/A'}

Use the fetch tool to get data from Google Books API. If that fails, search the web.
Return JSON with description, language, categories, page_count, publisher, year, and source."""
            
            web_result = await llm.generate_str(message=enrichment_query)
            logger.info(f"Web enrichment result: {web_result}")
            
            try:
                web_data = json.loads(web_result)
            except json.JSONDecodeError:
                web_data = {}
            
            has_photo_data = any([
                photo_data.isbn,
                photo_data.title,
                photo_data.author,
                photo_data.publisher,
                photo_data.year
            ])
            
            if web_data:
                source = "photo+web" if has_photo_data else "web"
                print(f"   ✓ Web enrichment complete (source: {web_data.get('source', 'unknown')})")
            else:
                source = "photo" if has_photo_data else "unknown"
                print(f"   ⚠ No web data found")
            
            book = Book(
                isbn=photo_data.isbn or web_data.get("isbn"),
                title=photo_data.title or web_data.get("title"),
                author=photo_data.author or web_data.get("author"),
                publisher=photo_data.publisher or web_data.get("publisher"),
                year=photo_data.year or web_data.get("year"),
                description=web_data.get("description"),
                language=web_data.get("language"),
                categories=web_data.get("categories"),
                page_count=web_data.get("page_count"),
                source=source
            )
            
            print(f"\n📚 Complete Book Information:")
            print("=" * 60)
            print(book)
            print("=" * 60)
            
            return str(book)


async def main():
    """Test the book extractor"""
    test_image = "files/book.png"
    
    if not Path(test_image).exists():
        print(f"❌ Test image '{test_image}' not found.")
        print(f"📤 Please upload a book cover image to 'files/book.png'")
        return
    
    print(f"🔍 Processing book cover: {test_image}\n")
    
    try:
        result = await process_book_image(test_image)
        print(f"\n✅ Processing complete!")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
