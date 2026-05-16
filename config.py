# config.py
from dotenv import load_dotenv
import os

load_dotenv()

class Settings:
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "180"))
    
    OCR_SPACE_API_KEY: str = os.getenv("OCR_SPACE_API_KEY")
    BASE_URL_FILES: str = "http://tekerapp.maxapex.net/FILES_PROD_TEKER_NEW/"
    
    PDF_MIN_CHARS: int = 80

settings = Settings()