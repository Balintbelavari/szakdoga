from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
import joblib
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from datetime import datetime
import os
from pathlib import Path
import logging

app = FastAPI()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

frontend_build_path = Path(os.getenv("FRONTEND_BUILD_PATH")) # Default to "../frontend/build" if not set
secret_key = os.getenv("SECRET_KEY")
encrypted_mongo_uri = os.getenv("MONGO_URI_ENCRYPTED")

# Check if the environment variables are set
if not secret_key or not encrypted_mongo_uri or not frontend_build_path:
    raise ValueError("Missing SECRET_KEY or MONGO_URI_ENCRYPTED or FRONTEND_BUILD_PATH in .env file")

fernet = Fernet(secret_key.encode()) # Fernet key must be bytes
mongo_uri = fernet.decrypt(encrypted_mongo_uri.encode()).decode()
client = AsyncIOMotorClient(mongo_uri)
db = client["szakdolgozat"]
collection = db["predictions"]

# Load models
try:
    model = joblib.load(BASE_DIR / "model.pkl")
    vectorizer = joblib.load(BASE_DIR / "vectorizer.pkl")
except FileNotFoundError as e:
    logger.critical(f"Model file not found: {e}")
    raise RuntimeError("Failed to load ML models")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://szakdolgozat-nh9z.onrender.com", "http://127.0.0.1:8000"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,
)

class Message(BaseModel):
    message: str
    
@app.get("/")
async def serve_frontend():
    index_path = frontend_build_path / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"error": "Frontend build not found"}

@app.post("/predict")
async def predict(message: Message):
    try:
        message_bow = vectorizer.transform([message.message])
        prediction = model.predict(message_bow)[0]
        result = {"message": message.message, "prediction": prediction, "timestamp": datetime.now().isoformat()}
        await db.predictions.insert_one(result)
        return {"prediction": prediction}
    except Exception as e:
        logger.error(f"Prediction failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Prediction failed")
    
if frontend_build_path.exists():
    app.mount("/", StaticFiles(directory=frontend_build_path, html=True), name="root")

@app.on_event("startup")
async def startup():
    await client.admin.command("ping")
    logger.info("MongoDB connected")

@app.on_event("shutdown")
async def shutdown():
    await client.close()