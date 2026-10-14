from fastapi import FastAPI

import checkout

app = FastAPI()
app.include_router(checkout.router)