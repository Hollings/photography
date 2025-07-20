from fastapi import FastAPI

from api.photos import router as photos_router

app = FastAPI(title="Photo API")
app.include_router(photos_router)