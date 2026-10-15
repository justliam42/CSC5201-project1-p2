from fastapi import FastAPI

import recommendation

app = FastAPI()
app.include_router(recommendation.router)
