from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse
from parser import convert_scoresheet
import os
import uuid

app = FastAPI()

@app.post("/convert")
async def convert(file: UploadFile = File(...), formats: list[str] = Form(["csv"])):
    # Save uploaded file
    temp_filename = f"/tmp/{uuid.uuid4()}.pdf"
    with open(temp_filename, "wb") as f:
        f.write(await file.read())

    # Run conversion
    output_paths = convert_scoresheet(temp_filename, formats)

    # Return the first selected file as download
    first_format = formats[0]
    return FileResponse(output_paths[first_format], filename=os.path.basename(output_paths[first_format]))
