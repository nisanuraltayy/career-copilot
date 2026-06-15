import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class CVKaydi(Base):
    __tablename__ = "cv_kayitlari"

    id = Column(Integer, primary_key=True, index=True)
    dosya_adi = Column(String(255), nullable=False)
    karakter_sayisi = Column(Integer, nullable=False)
    sayfa_sayisi = Column(Integer, nullable=False)
    analiz = Column(JSON, nullable=False)
    yukleme_tarihi = Column(DateTime, default=datetime.utcnow)


class IsIlani(Base):
    __tablename__ = "is_ilanlari"

    id = Column(Integer, primary_key=True, index=True)
    pozisyon_adi = Column(String(255), nullable=False)
    sirket_adi = Column(String(255), nullable=True)
    deneyim_yili = Column(String(100), nullable=True)
    ham_metin = Column(String, nullable=False)
    analiz = Column(JSON, nullable=False)
    eklenme_tarihi = Column(DateTime, default=datetime.utcnow)

class MotivasyonMektubu(Base):
    __tablename__ = "motivasyon_mektuplari"

    id = Column(Integer, primary_key=True, index=True)
    cv_id = Column(Integer, nullable=False)
    is_ilani_id = Column(Integer, nullable=False)
    mektup_metni = Column(String, nullable=False)
    olusturma_tarihi = Column(DateTime, default=datetime.utcnow)  


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()