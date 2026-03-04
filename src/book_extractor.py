import asyncio
import os
import json
import re
from pathlib import Path
import httpx
import xml.etree.ElementTree as ET

from firecrawl import AsyncV1FirecrawlApp
from firecrawl.v1.client import V1WaitAction, V1ClickAction, V1ScrapeAction

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
        return {"error": "GEMINI_API_KEY not set — cannot extract from photo"}

    image_file = Path(image_path)
    if not image_file.exists():
        return {"error": f"Image not found: {image_path}"}

    try:
        client = genai.Client(api_key=api_key)

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
            model="gemini-2.0-flash",
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
            return {"error": "Gemini returned empty response for photo"}

    except Exception as e:
        return {"error": f"Photo extraction failed: {str(e)}"}


@app.tool()
async def search_dnb_sru(isbn: str) -> dict:
    """
    Search Deutsche Nationalbibliothek (DNB) via SRU API using ISBN.
    PRIMARY web source - especially strong for German books.
    Parses MARC21 XML to extract: title, subtitle, author, publisher, location,
    year, edition, series, language, page_count, subjects, and notes/description.

    Args:
        isbn: The ISBN number to search for

    Returns:
        Dictionary with full bibliographic data from DNB
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

            def get_all_notes(tag):
                parts = []
                for field in record.findall(f".//marc:datafield[@tag='{tag}']", ns):
                    for sf in field.findall("marc:subfield", ns):
                        if sf.text:
                            parts.append(sf.text.strip())
                return ". ".join(parts) if parts else None

            title_a = get_subfield("245", "a") or ""
            title_b = get_subfield("245", "b") or ""
            subtitle = title_b.strip().rstrip("/: ").strip() or None
            title = title_a.strip().rstrip("/: ").strip() or None
            if not title and subtitle:
                title, subtitle = subtitle, None

            author = get_subfield("100", "a")
            if not author:
                author = get_subfield("700", "a")
            if author:
                author = re.sub(r",?\s*\d{4}-\d{0,4}$", "", author).strip()

            publisher = get_subfield("264", "b") or get_subfield("260", "b")
            location = get_subfield("264", "a") or get_subfield("260", "a")
            year = get_subfield("264", "c") or get_subfield("260", "c")
            if year:
                year_match = re.search(r"\d{4}", year)
                year = year_match.group(0) if year_match else year

            edition = get_subfield("250", "a")

            series_name = get_subfield("490", "a")
            series_vol = get_subfield("490", "v")
            series = None
            if series_name:
                series = f"{series_name.rstrip(';, ')} {series_vol}".strip() if series_vol else series_name.strip()

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
            ddc_codes = get_all_subfields("082", "a")

            description = get_all_notes("520") or get_all_notes("500")

            result = {
                "title": title,
                "subtitle": subtitle,
                "author": author,
                "publisher": publisher,
                "location": location,
                "published_year": year,
                "edition": edition,
                "series": series,
                "language": language,
                "page_count": page_count,
                "subjects": subjects,
                "source": "dnb",
            }
            if description:
                result["description"] = description
            if ddc_codes:
                result["ddc"] = ddc_codes

            return result

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
    Search the Karlsruher Virtueller Katalog (KVK) for book information using ISBN.
    KVK is a meta-catalog that queries many German-language library networks simultaneously
    (SWB, BVB, HEBIS, KOBV, GBV, DNB, Stabi Berlin).
    Uses Firecrawl browser automation to fill and submit the search form, then scrapes
    the rendered results.

    Best for: confirming holdings, finding edition/year variants, cross-library title data.

    Args:
        isbn: The ISBN number to search for

    Returns:
        Dictionary with merged book data from KVK results
    """
    if not isbn:
        return {"error": "No ISBN provided"}

    raw_key = os.environ.get("FIRECRAWL_API_KEY")
    if not raw_key:
        return {"error": "FIRECRAWL_API_KEY not set — cannot use KVK scraping"}
    api_key = raw_key if raw_key.startswith("fc-") else f"fc-{raw_key}"

    form_url = (
        f"https://kvk.bibliothek.kit.edu/"
        f"?SB={isbn}"
        f"&kataloge=SWB&kataloge=BVB&kataloge=NRW&kataloge=HEBIS"
        f"&kataloge=KOBV_SOLR&kataloge=GBV&kataloge=DDB&kataloge=STABI_BERLIN"
        f"&digitalOnly=0"
    )

    try:
        firecrawl = AsyncV1FirecrawlApp(api_key=api_key)
        result = await firecrawl.scrape_url(
            form_url,
            formats=["markdown"],
            actions=[
                V1WaitAction(type="wait", milliseconds=5000),
                V1ClickAction(type="click", selector="button#search-btn"),
                V1WaitAction(type="wait", milliseconds=25000),
                V1ScrapeAction(type="scrape"),
            ],
            timeout=90000,
            proxy="stealth",
            only_main_content=False,
        )

        markdown = result.markdown or ""
        if not markdown:
            return {"error": "KVK returned empty response"}

        if "keine Kataloge ausgewählt" in markdown:
            return {"error": "KVK form submission failed — no catalogs selected"}

        title = None
        subtitle = None
        author = None
        published_year = None

        def find_link_open(text: str, end: int) -> int:
            """Scan backwards from end, skipping \\[ and \\], to find the opening [."""
            i = end - 1
            while i >= 0:
                if text[i] == "[":
                    if i > 0 and text[i - 1] == "\\":
                        i -= 2
                        continue
                    return i
                i -= 1
            return -1

        # Anchor on the year+close-URL pattern that ends every book entry
        for m in re.finditer(r"[–\-](\d{4})\]\(https?://", markdown):
            year_val = m.group(1)
            open_pos = find_link_open(markdown, m.start())
            if open_pos < 0:
                continue

            entry_text = markdown[open_pos + 1 : m.start()].strip()

            # Strip browser-hint noise
            entry_text = re.sub(
                r"Ihr Browser zeigt an.*?besucht haben\.", "", entry_text, flags=re.DOTALL
            ).strip()

            # Remove escaped markdown brackets e.g. \[Verfasser\]
            entry_text = re.sub(r"\\\[.*?\\\]", "", entry_text).strip()

            # Split on \\\n or bare \n to separate title-line from author-line
            parts = re.split(r"\\\s*\n|\n", entry_text, maxsplit=1)
            title_line = parts[0].strip() if parts else entry_text
            author_line = parts[1].strip() if len(parts) > 1 else ""

            # Parse title line: "TITLE : SUBTITLE / credits"
            if not title:
                title_parts = re.split(r"\s*:\s*", title_line, maxsplit=1)
                raw_title = re.sub(r"\s*/.*", "", title_parts[0]).strip()
                if raw_title:
                    title = raw_title
                if len(title_parts) > 1 and not subtitle:
                    raw_sub = re.sub(r"\s*/.*", "", title_parts[1]).strip()
                    if raw_sub:
                        subtitle = raw_sub

            # Parse author line: "Lastname, Firstname [Verfasser]" or "Lastname, Firstname"
            if not author and author_line:
                au_m = re.search(
                    r"([\wäöüÄÖÜß][^\[,\n]{1,30},\s+[\wäöüÄÖÜß][^\[,\n]{1,20})",
                    author_line,
                )
                if au_m:
                    raw_au = au_m.group(1).strip().rstrip(",").strip()
                    name_parts = raw_au.split(", ", 1)
                    if len(name_parts) == 2:
                        author = f"{name_parts[1].strip()} {name_parts[0].strip()}"
                    else:
                        author = raw_au

            if not published_year:
                published_year = year_val

        total_hits_match = re.search(r"Treffer insgesamt:\s*(\d+)", markdown)
        total_hits = int(total_hits_match.group(1)) if total_hits_match else 0

        if not title and total_hits == 0:
            return {"error": f"No KVK results found for ISBN {isbn}"}

        data: dict = {"source": "kvk", "total_hits": total_hits}
        if title:
            data["title"] = title
        if subtitle:
            data["subtitle"] = subtitle
        if author:
            data["author"] = author
        if published_year:
            data["published_year"] = published_year

        return data

    except Exception as e:
        return {"error": f"KVK scraping error: {str(e)}"}


async def collect_book_data(image_path: str) -> Book:
    """
    Fully autonomous agent that collects complete book information.

    The agent autonomously:
    1. Calls extract_from_photo to get visible metadata
    2. Calls search_dnb_sru as primary web source (title, subtitle, edition, series, description, and more)
    3. Calls search_google_books for longer description and categories
    4. Falls back to search_open_library if fields still missing
    5. Falls back to Brave Search MCP if description still missing
    6. Falls back to search_kvk as final resort (Firecrawl browser, slowest)

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
        print(f"Tools: Gemini Vision | DNB SRU API | Google Books API | Open Library API | Brave Search ({brave_status}) | KVK (Firecrawl)\n")

        book_agent = Agent(
            name="book_collector",
            instruction=f"""You are a fully autonomous book data collector. Your goal is to build a COMPLETE Book object.

IMAGE PATH: {image_path}

YOUR AVAILABLE TOOLS (use in this order):
1. extract_from_photo(image_path) - Extract ISBN, title, author, publisher, year from book cover image
2. search_dnb_sru(isbn) - PRIMARY web source: DNB MARC21 XML API. Returns title, subtitle, author, publisher, location, year, edition, series, language, page_count, subjects, and description/notes
3. search_google_books(isbn) - Best source for longer description and genre categories. No API key needed
4. search_open_library(isbn) - FALLBACK: Open Library API. Use if above tools missing data
5. MCP Brave Search tools - Use if description still missing and BRAVE_API_KEY available
6. search_kvk(isbn) - FINAL RESORT: KVK meta-catalog via Firecrawl browser automation (slowest, ~30s). Only call if critical fields like title or author are still missing

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

STEP 2: DNB SRU lookup (PRIMARY)
- Call: search_dnb_sru(isbn)
- Get: title, subtitle, author, publisher, location, published_year, edition, series, language, page_count, subjects, description
- If description is returned and in German, use it directly

STEP 3: Google Books (for longer description and genre)
- Call: search_google_books(isbn)
- Get: description (TRANSLATE TO GERMAN!), categories (TRANSLATE TO GERMAN!), language
- Prefer this description only if DNB returned none or a very short note

STEP 4: Open Library (if fields still missing)
- Call: search_open_library(isbn)
- Fill any remaining gaps

STEP 5: Brave Search (if description still missing)
- Only if description is STILL missing and Brave is available
- Use MCP Brave Search tools

STEP 6: KVK meta-catalog (FINAL RESORT — only if title or author still missing)
- Call: search_kvk(isbn)
- This uses a real browser (Firecrawl) and takes ~30 seconds — only call it if earlier steps left critical fields empty
- Get: title, subtitle, author, published_year, total_hits

ERROR RECOVERY (CRITICAL):
- If any tool returns a dict containing an "error" key, it has failed — DO NOT use its data
- Simply skip the failed tool and continue immediately to the next tool in the list
- NEVER stop the workflow because a tool failed — always try the remaining tools
- If extract_from_photo fails: try search_dnb_sru with any visible ISBN from the image
- If ALL tools except Brave have been tried and description is still null: use Brave Search
- Only return null for a field if every tool failed to provide it

LANGUAGE REQUIREMENTS (CRITICAL):
- For GERMAN books (language: "de"): Keep title in German, description in German
- For FOREIGN books: Keep ORIGINAL title, but translate description/topics/genre to GERMAN
- DNB description/notes are usually already in German — prefer them over Google Books

DATA MERGING RULES:
1. Prefer photo data for: isbn, title, authors
2. Prefer DNB data for: publisher, location, published_year, language, page_count, edition, series, subtitle
3. Prefer Google Books for: categories/topic, genre; longer description if DNB had none or only a short note
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
                lambda agent: GoogleAugmentedLLM(model="gemini-2.0-flash", agent=agent)
            )

            try:
                response_text = await llm.generate_str(
                    message=(
                        "Collect complete book data by calling all tools in order. "
                        "Start with extract_from_photo, then enrich with search_dnb_sru, "
                        "search_google_books, search_open_library. "
                        "If any tool returns an error field, skip it and continue to the next. "
                        "Use Brave Search if description is still missing. "
                        "Only call search_kvk as a last resort if title or author are still missing after all other tools. "
                        "Return only the final merged JSON."
                    )
                )
            except Exception as e:
                logger.error(f"book_collector: LLM call failed: {e}")
                print(f"\n[ERROR] Agent failed: {e}")
                print("Returning partial Book with error source.")
                return Book(source="error")

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
                print(f"\n[ERROR] Could not parse agent JSON output. Returning empty Book.")
                return Book(source="error")
            except Exception as e:
                logger.error(f"Unexpected error building Book: {e}")
                print(f"\n[ERROR] Unexpected error: {e}. Returning empty Book.")
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
