from pydantic import BaseModel, Field
from typing import Optional


class Book(BaseModel):
    """Book information extracted from cover image and other sources"""
    isbn: Optional[str] = Field(None, description="ISBN-10 or ISBN-13 number")
    title: Optional[str] = Field(None, description="Book title")
    author: Optional[str] = Field(None, description="Book author(s)")
    publisher: Optional[str] = Field(None, description="Publisher name")
    year: Optional[str] = Field(None, description="Publication year")
    description: Optional[str] = Field(None, description="Book description or summary")
    
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
        if self.description:
            parts.append(f"Description: {self.description}")
        return "\n".join(parts)
