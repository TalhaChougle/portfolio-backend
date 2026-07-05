from pydantic import BaseModel
from typing import Optional, List


class CertificationOut(BaseModel):
    id: int
    title: str
    issuer: str
    category: str
    date: str
    description: str
    credential_url: str
    file_url: str
    media_type: str
    modules: List[str]

    class Config:
        from_attributes = True


class CertificationUpdate(BaseModel):
    title: Optional[str] = None
    issuer: Optional[str] = None
    category: Optional[str] = None
    date: Optional[str] = None
    description: Optional[str] = None
    credential_url: Optional[str] = None
    modules: Optional[List[str]] = None


class ResumeOut(BaseModel):
    id: int
    file_url: str
    media_type: str

    class Config:
        from_attributes = True


class DocOut(BaseModel):
    id: int
    title: str
    description: str
    file_url: str
    media_type: str

    class Config:
        from_attributes = True
