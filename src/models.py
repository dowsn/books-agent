from pydantic import BaseModel, Field
from typing import Optional


class BookPhotoExtraction(BaseModel):
    """Book information extracted from photo OCR - never includes description"""
    isbn: Optional[str] = Field(None, description="ISBN-10 or ISBN-13 number from photo")
    title: Optional[str] = Field(None, description="Book title from photo")
    author: Optional[str] = Field(None, description="Book author(s) from photo")
    publisher: Optional[str] = Field(None, description="Publisher name from photo")
    year: Optional[str] = Field(None, description="Publication year from photo")


class Book(BaseModel):
    """Complete book information from photo + web enrichment"""
    isbn: Optional[str] = Field(None, description="ISBN-10 or ISBN-13 number")
    title: Optional[str] = Field(None, description="Book title (original title for foreign books)")
    authors: Optional[str] = Field(None, description="Book author(s)")
    publisher: Optional[str] = Field(None, description="Publisher name")
    published_year: Optional[str] = Field(None, description="Publication year")
    location: Optional[str] = Field(None, description="City/location of publication")
    description: Optional[str] = Field(None, description="Book description in German (from web only)")
    topic: Optional[str] = Field(None, description="Book topics/categories in German")
    genre: Optional[str] = Field(None, description="Book genre in German")
    page_count: Optional[str] = Field(None, description="Number of pages")
    language: Optional[str] = Field(None, description="Book language code")
    source: str = Field("photo", description="Data source: 'photo', 'web', or 'photo+web'")
    
    def __str__(self):
        parts = []
        if self.title:
            parts.append(f"Title: {self.title}")
        if self.authors:
            parts.append(f"Authors: {self.authors}")
        if self.isbn:
            parts.append(f"ISBN: {self.isbn}")
        if self.publisher:
            parts.append(f"Publisher: {self.publisher}")
        if self.published_year:
            parts.append(f"Year: {self.published_year}")
        if self.location:
            parts.append(f"Location: {self.location}")
        if self.language:
            parts.append(f"Language: {self.language}")
        if self.page_count:
            parts.append(f"Pages: {self.page_count}")
        if self.topic:
            parts.append(f"Topic: {self.topic}")
        if self.genre:
            parts.append(f"Genre: {self.genre}")
        if self.description:
            parts.append(f"Description: {self.description}")
        parts.append(f"Source: {self.source}")
        return "\n".join(parts)
