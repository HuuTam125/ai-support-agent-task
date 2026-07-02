"""
Gemini API client: handles auth, file upload
and chat with strict system instructions.
"""

import os
from dotenv import load_dotenv
from google import genai 
from google.genai import types

load_dotenv()

GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

SYSTEM_INSTRUCTION = """You are OptiBot, the customer-support bot for OptiSigns.com.
- Tone: helpful, factual, concise.
- Only answer using the uploaded docs.
- Max 5 bullet points; else link to the doc.
- Cite up to 3 'Article URL:' lines per reply."""

def get_gemini_client() -> genai.Client:
    """
    Initialize and return a Google GenAI Client.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY does not set. Check .env file or GitHub Secrets."
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

def ask(question: str, uploaded_files: list) -> str:
    """
    Sends a question to Gemini along with the uploaded knowledge-base files
    as grounding context, following the strict system instruction.
    """
    client = get_gemini_client()
    
    # Kết hợp các file đã upload và câu hỏi vào một list
    contents = [*uploaded_files, question]
    
    # Dùng client.models.generate_content và truyền system_instruction vào config
    response = client.models.generate_content(
        model=GEMINI_MODEL_NAME,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
        )
    )
    return response.text

if __name__ == "__main__":
    files = upload_markdown_files()
    if not files:
        print("No files uploaded, aborting test chat.")
    else:
        test_question = "How do I add a YouTube video?"
        print(f"\n🤖 Asking: {test_question}\n")
        answer = ask(test_question, files)
        print(answer)