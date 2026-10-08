from fastapi import FastAPI, APIRouter, Response, status
from pydantic import BaseModel
import checkout, frontend

app = FastAPI()

app.include_router(checkout.router)
app.include_router(frontend.router)

# Fastapi finds the 'app' variable and runs it when executing `fastapi run main.py`
