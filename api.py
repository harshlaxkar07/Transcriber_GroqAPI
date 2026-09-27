"""
HTTP layer for the call transcription and information extraction pipeline.

Wraps the audio splitter, the Groq speech-to-text service and the
information extractor in a FastAPI application, and serves the console
from ``frontend/``.

Run with::

    uvicorn api:app --reload
"""

import shutil
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import (
    CHUNK_DURATION_MINUTES,
    GROQ_TRANSCRIPTION_MODEL,
    INPUT_DIR,
    LLM_MODEL,
    OUTPUT_DIR,
    SUPPORTED_AUDIO_EXTENSIONS,
)
from services.audio_splitter import audio_splitter
from services.speech_to_text import speech_to_text_service


BASE_DIR = Path(__file__).resolve().parent

FRONTEND_DIR = BASE_DIR / "frontend"

TRANSCRIPT_DIR = OUTPUT_DIR / "transcripts"

TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# Schemas
# ============================================================

class Chunk(BaseModel):
    index: int
    name: str
    transcript: str
    language: str | None = None
    duration: float | None = None


class TranscriptionResponse(BaseModel):
    filename: str
    transcript: str
    language: str | None = None
    duration: float | None = None
    chunks: list[Chunk]
    characters: int
    words: int
    transcript_file: str


class ExtractionResponse(BaseModel):
    report: str


class ExtractionRequest(BaseModel):
    transcript: str


class TranscriptSummary(BaseModel):
    name: str
    characters: int
    modified: float


# ============================================================
# Application
# ============================================================

app = FastAPI(
    title="Call Transcriber",
    version="1.0.0",
    description=(
        "Split long call recordings into chunks, transcribe them with the "
        "Groq speech-to-text model, and pull structured information out of "
        "the result. The console is served at /ui."
    ),
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Routes
# ============================================================

@app.get("/api/health", tags=["Health"])
def health() -> dict[str, object]:
    """
    Liveness probe that also reports the active configuration.
    """

    return {
        "status": "healthy",
        "transcription_model": GROQ_TRANSCRIPTION_MODEL,
        "extraction_model": LLM_MODEL,
        "chunk_minutes": CHUNK_DURATION_MINUTES,
        "formats": sorted(extension.lstrip(".") for extension in SUPPORTED_AUDIO_EXTENSIONS),
        "transcripts": len(list(TRANSCRIPT_DIR.glob("*.txt"))),
    }


@app.get("/api/transcripts", response_model=list[TranscriptSummary], tags=["Transcripts"])
def list_transcripts() -> list[TranscriptSummary]:
    """
    Transcripts already written to the output directory.
    """

    summaries = []

    for path in sorted(TRANSCRIPT_DIR.glob("*.txt")):
        summaries.append(
            TranscriptSummary(
                name=path.name,
                characters=len(path.read_text(encoding="utf-8", errors="replace")),
                modified=path.stat().st_mtime,
            )
        )

    return summaries


@app.get("/api/transcripts/{name}", tags=["Transcripts"])
def read_transcript(name: str) -> dict[str, str]:
    """
    Read one stored transcript by filename.
    """

    path = TRANSCRIPT_DIR / Path(name).name

    if not path.is_file():
        raise HTTPException(status_code=404, detail="Transcript not found.")

    return {
        "name": path.name,
        "transcript": path.read_text(encoding="utf-8", errors="replace"),
    }


@app.post("/api/transcribe", response_model=TranscriptionResponse, tags=["Transcribe"])
async def transcribe(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> TranscriptionResponse:
    """
    Split an uploaded recording, transcribe every chunk and merge the result.
    """

    suffix = Path(file.filename or "").suffix.lower()

    if suffix not in SUPPORTED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported audio format. Supported: "
                + ", ".join(sorted(SUPPORTED_AUDIO_EXTENSIONS))
            ),
        )

    INPUT_DIR.mkdir(parents=True, exist_ok=True)

    stem = Path(file.filename).stem or "recording"

    audio_path = INPUT_DIR / f"{stem}-{uuid.uuid4().hex[:8]}{suffix}"

    audio_path.write_bytes(await file.read())

    background_tasks.add_task(_cleanup, audio_path)

    try:
        chunk_paths = audio_splitter.split(audio_path)

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Could not split the recording: {error}",
        ) from error

    chunks: list[Chunk] = []

    language = None
    duration = 0.0

    try:
        for index, chunk_path in enumerate(chunk_paths, start=1):
            result = speech_to_text_service.transcribe(chunk_path)

            language = result.get("language") or language
            duration += float(result.get("duration") or 0)

            chunks.append(
                Chunk(
                    index=index,
                    name=chunk_path.name,
                    transcript=result["transcript"],
                    language=result.get("language"),
                    duration=result.get("duration"),
                )
            )

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Transcription failed: {error}",
        ) from error

    finally:
        background_tasks.add_task(_cleanup_chunks, chunk_paths)

    transcript = "\n\n".join(chunk.transcript for chunk in chunks)

    transcript_file = TRANSCRIPT_DIR / f"{audio_path.stem}.txt"

    transcript_file.write_text(transcript, encoding="utf-8")

    return TranscriptionResponse(
        filename=file.filename or audio_path.name,
        transcript=transcript,
        language=language,
        duration=round(duration, 2),
        chunks=chunks,
        characters=len(transcript),
        words=len(transcript.split()),
        transcript_file=transcript_file.name,
    )


@app.post("/api/extract", response_model=ExtractionResponse, tags=["Extract"])
def extract(request: ExtractionRequest) -> ExtractionResponse:
    """
    Pull structured information out of a transcript with the language model.
    """

    if not request.transcript.strip():
        raise HTTPException(
            status_code=400,
            detail="The transcript is empty.",
        )

    try:
        from services.information_extractor import information_extractor

        report = information_extractor.extract(request.transcript)

    except FileNotFoundError as error:
        raise HTTPException(
            status_code=503,
            detail=(
                "The extraction prompt is not available. Add "
                "prompts/extraction_prompt.txt to enable this step."
            ),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Extraction failed: {error}",
        ) from error

    return ExtractionResponse(report=report)


# ============================================================
# Helpers
# ============================================================

def _cleanup(path: Path) -> None:
    """
    Remove an uploaded recording once the response has been sent.
    """

    if path.is_file():
        path.unlink(missing_ok=True)


def _cleanup_chunks(paths: list[Path]) -> None:
    """
    Remove the per-recording chunk directory once the response has been sent.
    """

    if not paths:
        return

    directory = paths[0].parent

    if directory.is_dir():
        shutil.rmtree(directory, ignore_errors=True)


# ============================================================
# Console
# ============================================================

if FRONTEND_DIR.is_dir():

    app.mount(
        "/ui",
        StaticFiles(directory=FRONTEND_DIR, html=True),
        name="ui",
    )

    @app.get("/", include_in_schema=False)
    def console() -> RedirectResponse:
        """
        Send the application root to the console.
        """

        return RedirectResponse(url="/ui/")


__all__ = ["app"]
