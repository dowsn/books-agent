# How to Use the Book ISBN Extractor

## Quick Start

1. **Replace the test image** with your own book cover:
   - Take a photo of a book cover (back cover usually has the ISBN)
   - Name it `test_book_cover.jpg` and place it in the root directory
   - Or update the filename in `src/book_agent.py`

2. **Run the agent**:
   - Click the "Run" button in Replit, or
   - The workflow will automatically process the image

3. **View results**:
   - Check the console output for extracted information
   - The agent will show: ISBN, title, author, publisher, year, and description

## Tips for Best Results

- **ISBN visibility**: Make sure the ISBN barcode/number is clearly visible
- **Good lighting**: Well-lit photos work better
- **Focus**: Ensure the image is not blurry
- **Back cover**: ISBNs are typically on the back cover near the barcode

## What the Agent Extracts

The agent uses Google Gemini's vision AI to identify:
- **ISBN**: The 10 or 13-digit book identifier
- **Title**: The book's title
- **Author**: Author name(s)
- **Publisher**: Publishing company (if visible)
- **Year**: Publication year (if visible)
- **Description**: Brief description from cover text

## Testing with Your Own Images

You can process multiple images by modifying `src/example_usage.py`:

```python
# Add your image paths to this list
image_paths = [
    "book1.jpg",
    "book2.jpg",
    "book3.jpg"
]

await process_multiple_images(image_paths)
```

## Note About Test Image

The included `test_book_cover.jpg` is a stock photo and may not contain a real ISBN number. Replace it with an actual book cover photo to see the full extraction capabilities.

## Future Enhancements

This is a proof-of-concept. Potential next steps:
- Web search integration to fetch complete book data using the extracted ISBN
- Support for image URLs (not just local files)
- Batch processing interface
- Export results to CSV/JSON
