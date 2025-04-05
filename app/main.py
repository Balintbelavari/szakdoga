import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
import joblib
from pathlib import Path
from dotenv import load_dotenv
import os
from cryptography.fernet import Fernet

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")
secret_key = os.getenv("SECRET_KEY")
encrypted_mongo_uri = os.getenv("MONGO_URI_ENCRYPTED")
if not secret_key or not encrypted_mongo_uri:
    raise ValueError("Missing SECRET_KEY or MONGO_URI_ENCRYPTED")

fernet = Fernet(secret_key.encode())
mongo_uri = fernet.decrypt(encrypted_mongo_uri.encode()).decode()
client = AsyncIOMotorClient(mongo_uri)
db = client["szakdolgozat"]

# Load models
try:
    model = joblib.load(BASE_DIR / "model.pkl")
    vectorizer = joblib.load(BASE_DIR / "vectorizer.pkl")
except FileNotFoundError as e:
    logger.critical(f"Model file not found: {e}")
    raise RuntimeError("Failed to load ML models")

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://szakdolgozat-nh9z.onrender.com"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    allow_credentials=True,
)

# Serve frontend
FRONTEND_BUILD_PATH = Path(__file__).parent.parent / "frontend" / "build"
if FRONTEND_BUILD_PATH.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_BUILD_PATH, html=True), name="frontend")

@app.get("/")
async def serve_frontend():
    index_path = FRONTEND_PATH / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"error": "Frontend build not found"}

@app.get("/api")
def read_root():
    return {"message": "Welcome to the Scam/Ham Prediction API"}

class Message(BaseModel):
    message: str

@app.post("/predict")
async def predict(message: Message):
    try:
        message_bow = vectorizer.transform([message.message])
        prediction = model.predict(message_bow)[0]
        result = {"message": message.message, "prediction": prediction}
        await db.predictions.insert_one(result)
        return {"prediction": prediction}
    except Exception as e:
        logger.error(f"Prediction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Prediction failed")

@app.on_event("startup")
async def startup():
    await client.admin.command("ping")
    logger.info("MongoDB connected")

@app.on_event("shutdown")
async def shutdown():
    await client.close()