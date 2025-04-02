from fastapi import FastAPI, HTTPException  # type: ignore
from fastapi.staticfiles import StaticFiles  # type: ignore
from fastapi.responses import FileResponse  # type: ignore
from pathlib import Path  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from pydantic import BaseModel  # type: ignore
from motor.motor_asyncio import AsyncIOMotorClient  # type: ignore
import joblib  # type: ignore
from datetime import datetime
from dotenv import load_dotenv  # type: ignore
import os
import pymongo # type: ignore
import gspread # type: ignore
from google.oauth2 import service_account # type: ignore

# Load environment variables
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

MONGO_URI = os.getenv("MONGO_URI")  # MongoDB connection URI
client = AsyncIOMotorClient(MONGO_URI)
db = client["model_v0_1_1"]
collection = db["predictions"]

# Google Sheets API setup
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credentials = service_account.Credentials.from_service_account_file("lcsecurity-feb78c25475c.json", scope)
client_gs = gspread.authorize(creds)
sheet = client_gs.open("mongodb_export").sheet1

# Load model and vectorizer
model = joblib.load(os.path.join(BASE_DIR, "model1.pkl"))
vectorizer = joblib.load(os.path.join(BASE_DIR, "vectorizer1.pkl"))

# FastAPI app
app = FastAPI()

# ✅ Enable CORS for React frontend (localhost:3000 for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://lc-security-backend-d51e9de3f86b.herokuapp.com/", "http://127.0.0.1:8001/"],  # React dev server, heroku hosting
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Serve React frontend
frontend_build_path = Path(__file__) .parent .parent / "frontend" / "build"
print()
print(frontend_build_path)
print()

if frontend_build_path.exists():
    app.mount("/static", StaticFiles(directory=frontend_build_path / "static"), name="static")

@app.get("/")
async def serve_frontend():
    """Serves the React app's index.html file."""
    index_path = frontend_build_path / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"error": "Frontend build not found. Run npm run build in the frontend folder."}

# ✅ API Root
@app.get("/api")
def read_root():
    return {"message": "Welcome to the Scam/Ham Prediction API"}

# ✅ Predict Endpoint
class Message(BaseModel):
    message: str

@app.post("/predict")
async def predict(message: Message):
    try:
        # Transform input and make prediction
        message_bow = vectorizer.transform([message.message])
        prediction = model.predict(message_bow)[0]

        # Store prediction in MongoDB
        result = {
            "message": message.message,
            "prediction": prediction,
            "timestamp": datetime.now().isoformat()
        }
        await db.predictions.insert_one(result)
        
        # Update Google Sheet
        data = await collection.find({}, {"_id": 0, "message": 1, "prediction": 1}).to_list(length=None)
        formatted_data = [["Message", "Prediction"]]  # Header row
        new_row = [message.message, prediction]
        sheet.append_row(new_row)

        return {"prediction": prediction}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ Properly Close MongoDB on Shutdown
@app.on_event("shutdown")
async def shutdown():
    await client.close()

# ✅ Run FastAPI (for local development)
if __name__ == "__main__":
    import uvicorn  # type: ignore
    uvicorn.run(app, host="127.0.0.1", port=8001, reload=True)
