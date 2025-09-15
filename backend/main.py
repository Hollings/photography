from fastapi import FastAPI

from api.photos import router as photos_router
from api.feed   import router as feed_router

app = FastAPI(title="Photo API")
app.include_router(photos_router)
app.include_router(feed_router)
