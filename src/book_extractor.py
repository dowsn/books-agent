import asyncio
import os
import json
import re
from pathlib import Path
import httpx
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

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
        return {"isbn": None, "title": None, "author": None, "publisher": None, "year": None}


@app.tool()
async def search_dnb(isbn: str) -> dict:
    """
    Search Deutsche Nationalbibliothek (DNB) via SRU API using ISBN.
    PRIMARY web source - especially strong for German books.
    Returns title, author, publisher, location, year, language, page_count.
    Note: DNB rarely includes descriptions - use search_google_books for that.

    Args:
        isbn: The ISBN number to search for

    Returns:
        Dictionary with bibliographic data from DNB
    """
    if not isbn:
        return {"error": "No ISBN provided"}

    url = (
        f"https://services.dnb.de/sru/dnb"
        f"?version=1.1&operation=searchRetrieve"
        f"&query=isbn%3D{isbn}"
        f"&maximumRecords=1&recordSchema=MARC21-xml"
    )

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=15.0)
            response.raise_for_status()

            root = ET.fromstring(response.text)
            ns = {
                "srw": "http://www.loc.gov/zing/srw/",
                "marc": "http://www.loc.gov/MARC21/slim",
            }

            records = root.findall(".//marc:record", ns)
            if not records:
                return {"error": "No results found in DNB"}

            record = records[0]

            def get_subfield(tag, code):
                field = record.find(f".//marc:datafield[@tag='{tag}']", ns)
                if field is not None:
                    sf = field.find(f"marc:subfield[@code='{code}']", ns)
                    if sf is not None:
                        return sf.text
                return None

            def get_all_subfields(tag, code):
                results = []
                for field in record.findall(f".//marc:datafield[@tag='{tag}']", ns):
                    sf = field.find(f"marc:subfield[@code='{code}']", ns)
                    if sf is not None and sf.text:
                        results.append(sf.text)
                return results

            title_a = get_subfield("245", "a") or ""
            title_b = get_subfield("245", "b") or ""
            title = (title_a + " " + title_b).strip().rstrip("/: ").strip() or None

            author = get_subfield("100", "a")
            if not author:
                author = get_subfield("700", "a")

            publisher = get_subfield("264", "b") or get_subfield("260", "b")
            location = get_subfield("264", "a") or get_subfield("260", "a")
            year = get_subfield("264", "c") or get_subfield("260", "c")
            if year:
                year_match = re.search(r"\d{4}", year)
                year = year_match.group(0) if year_match else year

            lang_field = record.find(".//marc:datafield[@tag='041']", ns)
            language = None
            if lang_field is not None:
                sf = lang_field.find("marc:subfield[@code='a']", ns)
                language = sf.text if sf is not None else None
            if not language:
                ctrl008 = record.find(".//marc:controlfield[@tag='008']", ns)
                if ctrl008 is not None and ctrl008.text and len(ctrl008.text) >= 38:
                    language = ctrl008.text[35:38].strip()

            page_raw = get_subfield("300", "a")
            page_count = None
            if page_raw:
                page_match = re.search(r"(\d+)", page_raw)
                page_count = page_match.group(1) if page_match else None

            subjects = get_all_subfields("650", "a") + get_all_subfields("689", "a")

            return {
                "title": title,
                "author": author,
                "publisher": publisher,
                "location": location,
                "published_year": year,
                "language": language,
                "page_count": page_count,
                "subjects": subjects,
                "source": "dnb",
            }

        except ET.ParseError as e:
            return {"error": f"DNB XML parse error: {str(e)}"}
        except Exception as e:
            return {"error": f"DNB API error: {str(e)}"}


@app.tool()
async def search_google_books(isbn: str) -> dict:
    """
    Search Google Books API for complete book information using ISBN.
    Best source for description, categories, and language.
    No API key required for basic ISBN lookups.

    Args:
        isbn: The ISBN number to search for

    Returns:
        Dictionary with book data from Google Books API
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

            return {
                "title": volume_info.get("title"),
                "authors": volume_info.get("authors", []),
                "publisher": volume_info.get("publisher"),
                "published_date": volume_info.get("publishedDate"),
                "description": volume_info.get("description"),
                "language": volume_info.get("language"),
                "categories": volume_info.get("categories", []),
                "page_count": volume_info.get("pageCount"),
                "source": "google_books",
            }

        except Exception as e:
            return {"error": f"Google Books API error: {str(e)}"}


@app.tool()
async def search_open_library(isbn: str) -> dict:
    """
    Search Open Library API directly for book information using ISBN.
    Used as fallback when DNB and Google Books don't have complete data.

    Args:
        isbn: The ISBN number to search for

    Returns:
        Dictionary with book data from Open Library
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

            description = details.get("description")
            if isinstance(description, dict):
                description = description.get("value")

            authors = details.get("authors", [])
            author_names = [a.get("name") for a in authors if isinstance(a, dict)]

            publishers = details.get("publishers", [])
            publisher = publishers[0] if publishers else None

            publish_places = details.get("publish_places", [])
            location = publish_places[0] if publish_places else None

            return {
                "title": details.get("title"),
                "authors": author_names,
                "publisher": publisher,
                "location": location,
                "published_date": details.get("publish_date"),
                "description": description,
                "subjects": details.get("subjects", []),
                "page_count": details.get("number_of_pages"),
                "source": "open_library",
            }

        except Exception as e:
            return {"error": f"Open Library API error: {str(e)}"}


@app.tool()
async def search_kvk(isbn: str) -> dict:
    """
    Attempt to scrape KVK (Karlsruher Virtueller Katalog) for book data using ISBN.
    KVK aggregates many German library catalogs.
    NOTE: KVK uses bot protection - this may return empty results if blocked.

    Args:
        isbn: The ISBN number to search for

    Returns:
        Dictionary with scraped book data, or error if blocked
    """
    if not isbn:
        return {"error": "No ISBN provided"}

    url = (
        f"https://kvk.bibliothek.kit.edu/api/2.0/"
        f"?SB={isbn}"
        f"&kataloge=SWB&kataloge=BVB&kataloge=NRW&kataloge=HEBIS"
        f"&kataloge=KOBV_SOLR&kataloge=GBV&kataloge=DDB&kataloge=STABI_BERLIN"
        f"&digitalOnly=0&embedFulltitle=0"
    )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
        "Referer": "https://kvk.bibliothek.kit.edu/",
    }

    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(url, headers=headers, timeout=15.0)

            if "fast_challenge" in response.text or len(response.text) < 500:
                return {"error": "KVK blocked by bot protection - try Brave Search instead"}

            soup = BeautifulSoup(response.text, "lxml")

            results = []
            for item in soup.select(".result, .record, tr[class*='result']"):
                text = item.get_text(separator=" ", strip=True)
                if isbn.replace("-", "") in text.replace("-", ""):
                    results.append(text)

            if not results:
                all_text = soup.get_text(separator="\n", strip=True)
                lines = [l.strip() for l in all_text.split("\n") if l.strip()]
                relevant = [l for l in lines if any(
                    kw in l.lower() for kw in ["isbn", "titel", "autor", "verlag", "jahr"]
                )]
                if relevant:
                    return {"raw_data": "\n".join(relevant[:20]), "source": "kvk"}
                return {"error": "No results found in KVK"}

            return {"raw_data": "\n".join(results[:5]), "source": "kvk"}

        except Exception as e:
            return {"error": f"KVK scraping error: {str(e)}"}


async def collect_book_data(image_path: str) -> Book:
    """
    Fully autonomous agent that collects complete book information.

    The agent autonomously:
    1. Calls extract_from_photo to get visible metadata
    2. Calls search_dnb as primary web source (great for German books)
    3. Calls search_google_books for description and categories
    4. Falls back to search_open_library if fields still missing
    5. Falls back to search_kvk (web scraping, may be blocked)
    6. Falls back to Brave Search MCP as last resort

    Args:
        image_path: Path to book cover image

    Returns:
        Complete Book object with all available data
    """
    async with app.run() as agent_app:
        logger = agent_app.logger

        print(f"Starting book data collection...")
        print(f"Image: {image_path}\n")

        has_brave = bool(os.environ.get("BRAVE_API_KEY"))
        brave_status = "available" if has_brave else "not configured (optional)"
        print(f"Tools: Gemini Vision | DNB API | Google Books API | Open Library API | KVK scraping | Brave Search ({brave_status})\n")

        book_agent = Agent(
            name="book_collector",
            instruction=f"""You are a fully autonomous book data collector. Your goal is to build a COMPLETE Book object.

IMAGE PATH: {image_path}

YOUR AVAILABLE TOOLS (use in this order):
1. extract_from_photo(image_path) - Extract ISBN, title, author, publisher, year from book cover image
2. search_dnb(isbn) - PRIMARY web source: Deutsche Nationalbibliothek. Best for German books. Returns title, author, publisher, location, year, language, page_count
3. search_google_books(isbn) - Best source for description and categories. No API key needed
4. search_open_library(isbn) - FALLBACK: Direct Open Library API. Use if DNB or Google Books missing data
5. search_kvk(isbn) - FALLBACK: KVK catalog scraping (may be blocked by bot protection, try anyway)
6. MCP Brave Search tools - LAST RESORT only if description still missing and BRAVE_API_KEY available

REQUIRED BOOK FIELDS (fill ALL):
- isbn: ISBN-10 or ISBN-13 (STRING)
- title: Original title (STRING)
- authors: Author name(s) (STRING)
- publisher: Publisher name (STRING)
- published_year: Publication year (STRING, not integer!)
- location: City/location of publication (STRING)
- description: Book description IN GERMAN regardless of book language (STRING, MUST be from web!)
- topic: Book topics/categories IN GERMAN (STRING)
- genre: Book genre IN GERMAN (STRING)
- page_count: Number of pages (STRING, not integer!)
- language: Language code e.g. "de", "en", "cs" (STRING)
- source: "photo", "web", or "photo+web" (STRING)

AUTONOMOUS WORKFLOW:

STEP 1: Extract from photo
- Call: extract_from_photo("{image_path}")
- Get: isbn, title, author, publisher, year

STEP 2: DNB lookup (PRIMARY web source)
- Call: search_dnb(isbn)
- Get: publisher, location, published_year, language, page_count, subjects

STEP 3: Google Books (for description)
- Call: search_google_books(isbn)
- Get: description (TRANSLATE TO GERMAN!), categories (TRANSLATE TO GERMAN!), language

STEP 4: Open Library (if fields still missing)
- Call: search_open_library(isbn)
- Fill any remaining gaps

STEP 5: KVK scraping (if still missing)
- Call: search_kvk(isbn)
- May return "raw_data" string - extract what you can from it

STEP 6: Brave Search (last resort)
- Only if description is STILL missing and Brave is available
- Use MCP Brave Search tools

LANGUAGE REQUIREMENTS (CRITICAL):
- For GERMAN books (language: "de"): Keep title in German, description in German
- For FOREIGN books: Keep ORIGINAL title, but translate description/topics/genre to GERMAN

DATA MERGING RULES:
1. Prefer photo data for: isbn, title, authors
2. Prefer DNB data for: publisher, location, published_year, language, page_count
3. Prefer Google Books for: description, categories/topic, genre
4. Source: "photo+web" if merged, "photo" if only photo, "web" if only web

TYPE CONVERSION (CRITICAL):
- published_year: integer 2023 → string "2023"
- page_count: integer 300 → string "300"
- topic: array ["Fiction"] → string "Fiktion" (in German)
- authors: array ["Name1", "Name2"] → string "Name1, Name2"

OUTPUT JSON with ALL fields (null if unavailable after all attempts):
{{
  "isbn": "978-...",
  "title": "Title",
  "authors": "Author Name",
  "publisher": "Publisher",
  "published_year": "2023",
  "location": "City",
  "description": "Beschreibung auf Deutsch...",
  "topic": "Thema auf Deutsch",
  "genre": "Genre auf Deutsch",
  "page_count": "300",
  "language": "de",
  "source": "photo+web"
}}

START NOW: Call extract_from_photo first, then proceed with all web sources.""",
        )

        async with book_agent:
            logger.info("book_collector: Agent initialized")

            llm = await book_agent.attach_llm(
                lambda agent: GoogleAugmentedLLM(model="gemini-2.0-flash-exp", agent=agent)
            )

            response_text = await llm.generate_str(
                message="Collect complete book data by calling all necessary tools. Start with extract_from_photo, then enrich with DNB, Google Books, Open Library, and KVK. Return only the final merged JSON."
            )

            logger.info("book_collector: Collection complete")

            response_text = response_text.strip()
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

                print(f"\n Complete Book Information:")
                print("=" * 60)
                if book.title:
                    print(f"Title:       {book.title}")
                if book.authors:
                    print(f"Authors:     {book.authors}")
                if book.isbn:
                    print(f"ISBN:        {book.isbn}")
                if book.publisher:
                    print(f"Publisher:   {book.publisher}")
                if book.published_year:
                    print(f"Year:        {book.published_year}")
                if book.location:
                    print(f"Location:    {book.location}")
                if book.language:
                    print(f"Language:    {book.language}")
                if book.topic:
                    print(f"Topic:       {book.topic}")
                if book.genre:
                    print(f"Genre:       {book.genre}")
                if book.page_count:
                    print(f"Pages:       {book.page_count}")
                if book.description:
                    desc_preview = book.description[:200] + "..." if len(book.description) > 200 else book.description
                    print(f"Description: {desc_preview}")
                print(f"Source:      {book.source}")
                print("=" * 60)

                return book

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse agent response: {e}")
                logger.error(f"Response was: {response_text}")
                return Book(source="error")


async def main():
    """Main entry point for the book extractor"""
    image_path = "files/book.png"

    if not Path(image_path).exists():
        print(f"Error: Image not found at {image_path}")
        return

    print(f"Processing book cover: {image_path}")
    await collect_book_data(image_path)


if __name__ == "__main__":
    asyncio.run(main())
