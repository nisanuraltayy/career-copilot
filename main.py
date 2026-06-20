from fastapi import FastAPI

from routers import cv, ilan, uyum, mektup

app = FastAPI(title="Career Copilot", version="0.2.0")

app.include_router(cv.router)
app.include_router(ilan.router)
app.include_router(uyum.router)
app.include_router(mektup.router)


@app.get("/")
def ana_sayfa():
    return {"mesaj": "Career Copilot calisiyor!"}


@app.get("/saglik")
def saglik_kontrolu():
    return {"durum": "iyi"}