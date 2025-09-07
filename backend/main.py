import shutil
import os
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from verifier import classify_document 
import traceback

# Initialize the FastAPI app
app = FastAPI()

# Allow requests from your Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/upload")
async def upload_marksheet(file: UploadFile = File(...)):
    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{file.filename}"
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        result = classify_document(file_path)
    except Exception as e:
        traceback.print_exc()  # <-- prints full error in terminal
        return JSONResponse(content={"error": str(e)}, status_code=500)
    finally:
        os.remove(file_path)

    return JSONResponse(content=result)