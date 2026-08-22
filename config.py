from pathlib import Path

# ==========================================================
# Project Directories
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent

INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"

INPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# ==========================================================
# AI Models
# ==========================================================

WHISPER_MODEL = "base"

# Replace this later with the model you decide to use
# LLM_MODEL = ""

# ==========================================================
# Input / Output Files
# ==========================================================

TRANSCRIPT_FILE = OUTPUT_DIR / "transcript.txt"
REPORT_JSON_FILE = OUTPUT_DIR / "report.json"
REPORT_MARKDOWN_FILE = OUTPUT_DIR / "report.md"

# ==========================================================
# Supported Audio Formats
# ==========================================================

SUPPORTED_AUDIO_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".ogg",
    ".flac",
    ".aac",
}

# ==========================================================
# Whisper Configuration
# ==========================================================

DEVICE = "cpu"
COMPUTE_TYPE = "int8"
BEAM_SIZE = 5

# ==========================================================
# Groq
# ==========================================================

import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# whisper-large-v3 is recommended
GROQ_TRANSCRIPTION_MODEL = "whisper-large-v3"


# ==========================================================
# Audio Splitter
# ==========================================================

CHUNK_DURATION_MINUTES = 2

CHUNK_DURATION_MS = (
    CHUNK_DURATION_MINUTES
    * 60
    * 1000
)

CHUNK_DIRECTORY = OUTPUT_DIR / "chunks"

CHUNK_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)



LLM_MODEL = "llama-3.3-70b-versatile"