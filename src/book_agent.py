import asyncio
import os
import base64
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types
from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from mcp_agent.core.context import Context as AppContext

from models import Book, BookPhotoExtraction
from web_enrichment import fetch_book_info_from_web, merge_photo_and_web_data


app = MCPApp(name="book_isbn_extractor", description="Extract ISBN and book information from cover images")


async def extract_book_info_from_image(
    image_path: str,
    app_ctx: Optional[AppContext] = None
) -> Book:
    """
    Extract ISBN and book metadata from a book cover image using Gemini vision.
    
    Args:
        image_path: Path to the book cover image file
        app_ctx: Application context (optional)
    
    Returns:
        Book object with extracted information
    
    Raises:
        ValueError: If GEMINI_API_KEY is not set
        FileNotFoundError: If image file does not exist
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is not set. "
            "Please add your Gemini API key to Replit Secrets or set it as an environment variable."
        )
    
    client = genai.Client(api_key=api_key)
    
    image_file = Path(image_path)
    if not image_file.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    
    if image_path.lower().endswith(".png"):
        mime_type = "image/png"
    elif image_path.lower().endswith(".webp"):
        mime_type = "image/webp"
    elif image_path.lower().endswith((".jpg", ".jpeg")):
        mime_type = "image/jpeg"
    else:
        mime_type = "image/jpeg"
    
    prompt = """Analyze this book cover image and extract ONLY the following information that is visible:
    
1. ISBN number (ISBN-10 or ISBN-13) - Look for numbers prefixed with "ISBN" 
2. Book title
3. Author name(s)
4. Publisher name (if visible)
5. Publication year (if visible)

IMPORTANT: Return ONLY information visible in the image. DO NOT include description.

Return the information in JSON format with these exact fields:
- isbn (string or null)
- title (string or null)
- author (string or null)
- publisher (string or null)
- year (string or null)

If any information is not visible or unclear, use null for that field."""
    
    print("  Step 1: Extracting information from photo...")
    
    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=[
            types.Part.from_bytes(
                data=image_bytes,
                mime_type=mime_type,
            ),
            prompt,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=BookPhotoExtraction,
        ),
    )
    
    if response.text:
        import json
        data = json.loads(response.text)
        photo_data = BookPhotoExtraction(**data)
    else:
        photo_data = BookPhotoExtraction()
    
    print(f"  ✓ Photo extraction complete")
    if photo_data.isbn:
        print(f"    Found ISBN: {photo_data.isbn}")
    
    print("  Step 2: Enriching with web data...")
    web_data = await fetch_book_info_from_web(photo_data)
    
    if web_data:
        print(f"  ✓ Web enrichment complete")
    else:
        print(f"  ⚠ No additional web data found")
    
    final_book = merge_photo_and_web_data(photo_data, web_data)
    return final_book


async def main():
    """Test the book info extraction"""
    async with app.run() as agent_app:
        test_image = "files/book.png"
        
        if not Path(test_image).exists():
            print(f"❌ Test image '{test_image}' not found.")
            print(f"📤 Please upload your book cover image to the 'files' folder and name it 'book.png'")
            print(f"   You can also use .jpg or .jpeg format.")
            return
        
        print(f"🔍 Extracting book information from '{test_image}'...")
        print()
        
        try:
            book = await extract_book_info_from_image(test_image, agent_app.context)
            
            print("📚 Extracted Book Information:")
            print("=" * 50)
            print(book)
            print("=" * 50)
            
            if book.isbn:
                print(f"\n✅ Successfully extracted ISBN: {book.isbn}")
            else:
                print("\n⚠️  No ISBN found in the image")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
