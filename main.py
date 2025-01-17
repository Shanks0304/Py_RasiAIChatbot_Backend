from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.common.exception_handler import custom_http_exception_handler

from app.router import auth as auth
from app.router import chatbot as chatbot
from app.router import messages as messages

import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

allowed_origins = [
    "http://localhost",
    "http://localhost:3000",  # Next.js development server
    "https://www.rasi.ai",
    "https://rasi.ai",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, tags=["auth"])
app.include_router(chatbot.router, tags=["chatbot"])
app.include_router(messages.router, tags=["messages"])
app.add_exception_handler(HTTPException, custom_http_exception_handler)

# define the route:
@app.get("/", tags=["root"])

def root():
    return {"message": "Hello World"}

# define the entry point. In the entry point, using uvicorn to run server
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)