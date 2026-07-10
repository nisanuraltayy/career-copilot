"""Ortak/paylaşılan şemalar."""

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    durum: str
    surum: str
    ortam: str


class ReadinessResponse(BaseModel):
    durum: str
    veritabani: str
