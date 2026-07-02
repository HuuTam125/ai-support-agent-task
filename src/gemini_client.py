"""
Gemini API client: handles auth, file upload
and chat with strict system instructions.
"""

import os
from dotenv import load_dotenv
from google import genai 

load_dotenv()

GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

def get_gemini_client() -> genai.Client:
    """
    Khởi tạo và trả về Google GenAI Client.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY chưa được set. Kiểm tra file .env hoặc GitHub Secrets."
        )
    return genai.Client(api_key=api_key)

def upload_markdown_files(directory: str = "data/articles") -> list:
    """
    Uploads every .md file in `directory` to Gemini File API.
    Returns list of successfully uploaded file objects.
    """
    client = get_gemini_client()

    md_files = sorted(f for f in os.listdir(directory) if f.endswith(".md"))
    uploaded = []

    for i, filename in enumerate(md_files, start=1):
        filepath = os.path.join(directory, filename)
        try:
            gfile = client.files.upload(
                file=filepath,
                config={
                    "mime_type": "text/markdown",
                    "display_name": filename
                }
            )
            uploaded.append(gfile)
            print(f"[{i}/{len(md_files)}] Uploaded: {filename} -> {gfile.name}")
        except Exception as e:
            print(f"[{i}/{len(md_files)}] FAILED: {filename} ({e})")

    print(f"\n Successfully uploaded {len(uploaded)}/{len(md_files)} files to Gemini File API.")
    return uploaded

if __name__ == "__main__":
    upload_markdown_files()