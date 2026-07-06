from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import cv, ilan, uyum, mektup, oneri
from database import Base, engine
app = FastAPI(title="Career Copilot", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
Base.metadata.create_all(bind=engine)
app.include_router(cv.router)
app.include_router(ilan.router)
app.include_router(uyum.router)
app.include_router(mektup.router)
app.include_router(oneri.router)
@app.get("/")
def ana_sayfa():
    return {"mesaj": "Career Copilot calisiyor!"}
@app.get("/saglik")
def saglik_kontrolu():
    return {"durum": "iyi"}