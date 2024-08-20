import glob
import os
import io
import shutil
import zipfile
import time
from fastapi import BackgroundTasks
from typing import List
from fastapi import FastAPI, UploadFile, File, Form
from starlette.requests import Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse, StreamingResponse
from AFM import (
    clean_and_process_excel_files,
    expected_header_names,
    unwanted_header_elements,
)

app = FastAPI()


app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="tempAPI")

# Define these variables globally to store their values
temp_min = temp_max = relH_min = relH_max = None
# Flag
processing_complete = False


# Clear temporary files folders: these functions will remove all .png files in the static and temp_files folder
# after serving the plots

def clear_static_folder():
    for file_name in os.listdir("static"):
        if file_name.endswith(".png") or file_name.endswith(".zip"):
            file_path = os.path.join("static", file_name)
            try:
                os.remove(file_path)
                print(f"Successfully removed {file_path}")
            except Exception as e:
                print(f"Error removing {file_path}: {e}")

def clear_temp_files_contents():
    folder = "temp_files"
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Failed to delete {file_path}. Reason: {e}")

def delayed_cleanup():
    time.sleep(10)  # wait for 10 seconds
    clear_static_folder()
    if os.path.exists("temp_files"):
        shutil.rmtree("temp_files")



@app.get("/")
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/upload")
def redirect_to_home():
    return FileResponse("tempAPI/index.html")

@app.get("/test/")
def test_endpoint():
    return {"message": "Test successful"}

@app.post("/upload")
async def upload_files(
    background_tasks: BackgroundTasks,
    request: Request,
    files: List[UploadFile] = File(...),
    plot_option: str = Form("combined"),
    dpi: int = Form(500),
    timestamp_count: int = Form(10),
    temp_range: str = Form("10,30"),
    relH_range: str = Form("25,70")
):
    global temp_min, temp_max, relH_min, relH_max, processing_complete

    if plot_option == "combined" and len(files) == 1:
        error_message = "For the 'combined' option, you need to upload more than one file."
        return templates.TemplateResponse("index.html", {"request": request, "error_message": error_message})

    temp_dir = "temp_files"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    temp_files = []

    for file in files:
        temp_file = os.path.join(temp_dir, file.filename)
        with open(temp_file, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        temp_files.append(temp_file)

    # Split ranges and convert them to integers
    temp_min, temp_max = map(int, temp_range.split(','))
    relH_min, relH_max = map(int, relH_range.split(','))



    # Outside the loop to avoid processing the same data multiple times

    clean_and_process_excel_files(temp_files, expected_header_names, unwanted_header_elements, dpi, timestamp_count,
        combined_plot=plot_option == "combined", temp_range=(temp_min, temp_max),
        relH_range=(relH_min, relH_max))


    print(os.listdir(temp_dir))


    processing_complete = True

    if plot_option == "combined":
        file_path = os.path.join("static", "Plots.png")
        response = FileResponse(file_path, headers={"Content-Disposition": "attachment; filename=Plots.png"})
        #return response
    else:
        # Get a list of all the plot files
        plot_files = glob.glob(os.path.join("static", "*_plot.png"))

        # If uploaded file is only 1, then serve it directly instead of zipping it

        if len(plot_files) == 1:
            file_path = plot_files[0]
            response = FileResponse(file_path, headers={
                "Content-Disposition": f"attachment; filename={os.path.basename(file_path)}"})
        elif plot_files:

            # Create a temporary ZIP file on disk

            zip_file_path = os.path.join("static", "plots.zip")
            with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file_path in plot_files:
                    zip_file.write(file_path, os.path.basename(file_path))
            response = FileResponse(zip_file_path, headers={"Content-Disposition": "attachment; filename=plots.zip"})
        else:
            return {"error": "No plot files found to be zipped"}

    background_tasks.add_task(clear_static_folder)
    background_tasks.add_task(clear_temp_files_contents)

    return response


# Define the /upload/result endpoint to return processing results

@app.get("/upload/result")
def get_upload_result():
    global temp_min, temp_max, relH_min, relH_max, processing_complete

    # Check if processing is complete

    if not processing_complete:
        return {"message": "Processing is not yet complete. Please wait."}

    # If processing is complete, return the results

    result_data = {
        "temp_min": temp_min,
        "temp_max": temp_max,
        "relH_min": relH_min,
        "relH_max": relH_max,

    }

    return result_data

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
