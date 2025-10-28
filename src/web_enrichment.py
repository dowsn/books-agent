import httpx
import json
from typing import Optional
from models import Book, BookPhotoExtraction


async def fetch_book_info_from_web(photo_data: BookPhotoExtraction) -> Optional[dict]:
    """
    Fetch complete book information from web using ISBN or title+author.
    
    Args:
        photo_data: Book information extracted from photo
    
    Returns:
        Dictionary with enriched book data from Google Books API
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        if photo_data.isbn:
            query = f"isbn:{photo_data.isbn}"
        elif photo_data.title and photo_data.author:
            query = f"{photo_data.title} {photo_data.author}"
        elif photo_data.title:
            query = photo_data.title
        else:
            return None
        
        url = "https://www.googleapis.com/books/v1/volumes"
        params = {"q": query, "maxResults": 1}
        
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("totalItems", 0) == 0:
                return None
            
            book_info = data["items"][0]["volumeInfo"]
            return book_info
            
        except Exception as e:
            print(f"⚠️  Web search failed: {e}")
            return None


def merge_photo_and_web_data(photo_data: BookPhotoExtraction, web_data: Optional[dict]) -> Book:
    """
    Merge photo-extracted data with web-enriched data.
    Photo data takes precedence for ISBN, title, author, publisher, year.
    Web data provides description, city, categories, etc.
    
    Args:
        photo_data: Data extracted from photo
        web_data: Data from web API
    
    Returns:
        Complete Book object with accurate source tracking
    """
    has_photo_data = any([
        photo_data.isbn,
        photo_data.title,
        photo_data.author,
        photo_data.publisher,
        photo_data.year
    ])
    
    if not web_data:
        return Book(
            isbn=photo_data.isbn,
            title=photo_data.title,
            author=photo_data.author,
            publisher=photo_data.publisher,
            year=photo_data.year,
            source="photo"
        )
    
    authors_list = web_data.get("authors", [])
    authors = ", ".join(authors_list) if authors_list else None
    
    categories_list = web_data.get("categories", [])
    categories = ", ".join(categories_list) if categories_list else None
    
    published_date = web_data.get("publishedDate", "")
    web_year = published_date[:4] if len(published_date) >= 4 else None
    
    source = "photo+web" if has_photo_data else "web"
    
    return Book(
        isbn=photo_data.isbn or web_data.get("industryIdentifiers", [{}])[0].get("identifier"),
        title=photo_data.title or web_data.get("title"),
        author=photo_data.author or authors,
        publisher=photo_data.publisher or web_data.get("publisher"),
        year=photo_data.year or web_year,
        city=None,
        description=web_data.get("description"),
        categories=categories,
        page_count=web_data.get("pageCount"),
        language=web_data.get("language"),
        source=source
    )
