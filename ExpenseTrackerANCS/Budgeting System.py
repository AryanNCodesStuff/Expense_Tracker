"""
Import all modules
Agent Email:expensetrackerancs@expense-tracker-513307.iam.gserviceaccount.com
"""
from PIL import Image # Image processing
import pytesseract # OCR (extract text from images)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
import gspread  # Google Sheets integration
from google.oauth2.service_account import Credentials
import os  # File and folder handling
from datetime import datetime  # Date formatting
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import os
from googleapiclient.http import MediaIoBaseDownload

"""
Sheets and Drive Connection
"""
sheet_url = "https://docs.google.com/spreadsheets/d/1BKfITC0J0NKeiDhHC_C3AUpexOgrC7YZ-asnnT8YG5o/edit?usp=sharing"
spreadsheet_id = sheet_url.split("/d/")[1].split("/")[0]
gc = gspread.service_account(filename="credentials.json")   # Authenticate with your service account
gc.http_client.set_timeout(60)
spreadsheet = gc.open_by_url(sheet_url)     # Open your existing spreadsheet
worksheet = spreadsheet.worksheet("November 2026")      # Select your worksheet tab
print("Connected to Google Sheets successfully!")       #Testing Connection
print("Spreadsheet:", spreadsheet.title)
print("Worksheet:", worksheet.title)

SCOPES = ["https://www.googleapis.com/auth/drive"]      # Google Drive API permission
credentials = Credentials.from_service_account_file("credentials.json",scopes=SCOPES)   # Authenticate
drive_service = build("drive","v3",credentials=credentials)     # Connect to Google Drive
print("Connected to Google Drive successfully!")

def read_records():                         # Read all existing records
    data = worksheet.get_all_records()
    return data

# Folder IDs from Google Drive
pending_folder_id = "1sZKQ0aRT0GyOdzYxdxbhF6EGJYE-a3wk"
processed_folder_id = "1yVM5yVUGju8mZgI-iOPZhynQ9F7J-dWg"

def get_files(folder_id):
    results = drive_service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields="files(id, name, mimeType)"
    ).execute()

    return results.get("files", [])

def download_file(file_id, file_name):
    if not file_name.lower().endswith((".png", ".jpg", ".jpeg")):
        raise ValueError("Unsupported image format")
    request = drive_service.files().get_media(fileId=file_id)
    file_path = os.path.join("Downloaded", file_name)
    os.makedirs("Downloaded", exist_ok=True)
    with open(file_path, "wb") as f:
        downloader = MediaIoBaseDownload(f, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        if status:
            print(f"Download progress: {int(status.progress() * 100)}%")
    return file_path

def OCR(image_path):                                                #OCR
    image_path = image_path # Path to your screenshot
    img = Image.open(image_path)    # Open the image
    transaction_data = pytesseract.image_to_string(img) # Extract text
    lines=transaction_data.strip().splitlines()
    print(lines)
    for i in lines:
        if i=='': 
            lines.pop(lines.index(i))
    print(lines)
    amount=lines[1][1:]
    print("Amount: ", amount)
    data=lines[2]
    try:
        code, detail = data.split("0", 1)
    except ValueError:
        try:
            code, detail = data.split("O", 1)
        except ValueError:
            code, detail = "_", data
    print("Code:", code)
    print("Details:", detail)

    def extract_date(lines,index=4):
        x=lines[index]
        x=x.split()
        x=''.join(x)
        try:
            date = datetime.strptime(x, "%d%b%Y,%I:%M%p")
        except:
            return extract_date(lines,index+1)
        else:
            formatted_date = date.strftime("%d-%m-%Y")
            return formatted_date
    print(extract_date(lines))
    return (extract_date(lines),amount,code,detail) 

def add_transaction(inp):
    # Find the last filled row in column A (Date)
    dates = worksheet.col_values(1)
    last_row = len(dates)
    # Insert the transaction in the next row
    worksheet.update(
        range_name=f"A{last_row + 1}:D{last_row + 1}",
        values=[inp]
    )

def move_to_processed(file_id):
    drive_service.files().update(
        fileId=file_id,
        addParents=processed_folder_id,
        removeParents=pending_folder_id,
        fields="id, name, parents"
    ).execute()
    print("File moved to Processed successfully!")

def Process_Transaction():
    pending_files = get_files(pending_folder_id)
    if not pending_files:
        print("No files found in Pending folder.")
        return
    print("Files waiting to be processed:")
    for file in pending_files:
        if not file["mimeType"].startswith("image/"):
            continue
        try:
            print("\nProcessing:", file["name"])
            imgpath = download_file(file["id"], file["name"])
            inp = OCR(imgpath)
            add_transaction(inp)
            move_to_processed(file["id"])
        except Exception as e:
            print("Error processing", file["name"], ":", e)
            print("Leaving file in Pending folder.")
Process_Transaction()