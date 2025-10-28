"""
Example usage of the Book ISBN Extractor Agent

This demonstrates how to use the agent to extract book information from images.
"""

import asyncio
from pathlib import Path
from book_agent import extract_book_info_from_image


async def process_single_image(image_path: str):
    """Process a single book cover image"""
    print(f"\n{'='*60}")
    print(f"Processing: {image_path}")
    print(f"{'='*60}\n")
    
    try:
        book = await extract_book_info_from_image(image_path)
        
        print("📚 Extracted Book Information:")
        print("-" * 60)
        print(book)
        print("-" * 60)
        
        if book.isbn:
            print(f"\n✅ Successfully extracted ISBN: {book.isbn}")
        else:
            print("\n⚠️  No ISBN found in the image")
            
        return book
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return None


async def process_multiple_images(image_paths: list[str]):
    """Process multiple book cover images"""
    print("\n" + "="*60)
    print("BATCH PROCESSING MODE")
    print("="*60)
    
    results = []
    for image_path in image_paths:
        result = await process_single_image(image_path)
        results.append((image_path, result))
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    successful = sum(1 for _, book in results if book and book.isbn)
    print(f"\nTotal images processed: {len(results)}")
    print(f"Successfully extracted ISBN: {successful}")
    print(f"Failed or no ISBN: {len(results) - successful}")
    
    return results


async def main():
    """Main example function"""
    
    print("""
╔════════════════════════════════════════════════════════════╗
║         Book ISBN Extractor Agent - Example Usage         ║
╚════════════════════════════════════════════════════════════╝

This agent uses Gemini vision to extract:
  • ISBN numbers (ISBN-10 or ISBN-13)
  • Book title
  • Author name(s)
  • Publisher
  • Publication year
  • Brief description

For best results:
  • Use clear photos of book covers
  • Ensure ISBN is visible (usually on the back cover)
  • Good lighting and focus help accuracy
""")
    
    test_image = "test_book_cover.jpg"
    
    if not Path(test_image).exists():
        print(f"❌ Test image '{test_image}' not found.")
        print(f"\nTo test the agent:")
        print(f"1. Add a photo of a book cover to this directory")
        print(f"2. Name it '{test_image}' or update the image_path variable")
        print(f"3. Run this script again")
        return
    
    await process_single_image(test_image)


if __name__ == "__main__":
    asyncio.run(main())
