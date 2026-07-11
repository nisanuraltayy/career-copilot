"""Auth endpoint şemaları."""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class KayitIstegi(BaseModel):
    email: str = Field(..., max_length=320)
    parola: str = Field(..., min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def _email_gecerli(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Geçerli bir e-posta adresi girin.")
        return v


class GirisIstegi(BaseModel):
    email: str
    parola: str

    @field_validator("email")
    @classmethod
    def _normalize(cls, v: str) -> str:
        return v.strip().lower()


class TokenYaniti(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class YenilemeIstegi(BaseModel):
    refresh_token: str


class ParolaDegistirIstegi(BaseModel):
    eski_parola: str
    yeni_parola: str = Field(..., min_length=8, max_length=128)


class KullaniciYaniti(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
