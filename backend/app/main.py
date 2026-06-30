from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import fields, photos

app = FastAPI(title="GroundTruth API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "https://groundtruth.vercel.app",
        "https://groundtruth-1.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(fields.router)
app.include_router(photos.router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
