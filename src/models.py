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
    title: Optional[str] = Field(None, description="Book title")
    author: Optional[str] = Field(None, description="Book author(s)")
    publisher: Optional[str] = Field(None, description="Publisher name")
    year: Optional[str] = Field(None, description="Publication year")
    city: Optional[str] = Field(None, description="City of publication")
    description: Optional[str] = Field(None, description="Book description (from web only)")
    categories: Optional[str] = Field(None, description="Book categories/genres")
    page_count: Optional[int] = Field(None, description="Number of pages")
    language: Optional[str] = Field(None, description="Book language")
    source: str = Field("photo", description="Data source: 'photo', 'web', or 'photo+web'")
    
    def __str__(self):
        parts = []
        if self.title:
            parts.append(f"Title: {self.title}")
        if self.author:
            parts.append(f"Author: {self.author}")
        if self.isbn:
            parts.append(f"ISBN: {self.isbn}")
        if self.publisher:
            parts.append(f"Publisher: {self.publisher}")
        if self.year:
            parts.append(f"Year: {self.year}")
        if self.city:
            parts.append(f"City: {self.city}")
        if self.language:
            parts.append(f"Language: {self.language}")
        if self.page_count:
            parts.append(f"Pages: {self.page_count}")
        if self.categories:
            parts.append(f"Categories: {self.categories}")
        if self.description:
            parts.append(f"Description: {self.description}")
        parts.append(f"Source: {self.source}")
        return "\n".join(parts)
