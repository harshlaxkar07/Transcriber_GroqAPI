# Call Transcriber

Transcribe long call recordings by splitting them into short chunks, sending each one to the **Groq** speech-to-text model, and stitching the results back into a single transcript. Then hand that transcript to a language model to pull out the details you care about.

Ships with a web console served by the API, and a batch command-line runner for folders of recordings.

---

## Highlights

| | |
|---|---|
| **Handles long calls** | Recordings are split into chunks so each request stays comfortably within limits |
| **Fast transcription** | Groq's `whisper-large-v3` returns text, the detected language and the duration |
| **Six audio formats** | MP3, WAV, M4A, OGG, FLAC and AAC |
| **Information extraction** | A second pass over the transcript pulls out structured details |
| **Two ways to run** | A web console for one call at a time, a CLI for a whole folder |
| **Transcripts kept** | Every run writes a text file you can reopen, copy or download |

---

## The console

The API serves its own front end — start the server and open the root URL.

**Transcribe** — drop in a recording and listen to it while the chunks are processed. The result is a stat row (language, duration, chunk count, word count), the full transcript with copy and download buttons, and a per-chunk breakdown you can expand to see exactly which part of the call produced which text.

**Transcripts** — every transcript written to the output directory, with its size and age. Open one to read it, copy it, or run information extraction over it.

**Pipeline** — the models and chunk length this build is running with, and the four stages laid out end to end.

---

## How it works

```
Recording
   │
   ├─ 1. Split       pydub cuts the audio into fixed-length WAV chunks
   ├─ 2. Transcribe  each chunk goes to Groq's whisper-large-v3
   ├─ 3. Merge       chunk transcripts are joined in order and written to a text file
   └─ 4. Extract     the merged transcript is passed to a language model for structured details
```

Chunking is what makes long recordings straightforward: a two-hour call becomes sixty short requests instead of one oversized one, and each chunk's text is kept so you can trace any line back to its position in the call.

---

## Tech stack

**API** FastAPI · Uvicorn · Pydantic v2
**Speech** Groq `whisper-large-v3`
**Extraction** Groq `llama-3.3-70b-versatile`
**Audio** pydub · FFmpeg · soundfile
**Front end** Vanilla HTML, CSS and JavaScript — no build step

---

## Getting started

### Prerequisites

- Python 3.12 or newer
- FFmpeg on your `PATH` (`sudo apt install ffmpeg` or `brew install ffmpeg`)
- A [Groq API key](https://console.groq.com)

### 1. Install

```bash
git clone https://github.com/harshlaxkar07/Transcriber_GroqAPI.git
cd Transcriber_GroqAPI

# with uv (recommended)
uv sync

# or with pip
python -m venv .venv && source .venv/bin/activate
pip install -e .

# for the web console
pip install "fastapi>=0.115" "uvicorn[standard]>=0.32" python-multipart
```

### 2. Configure

Create a `.env` file in the project root:

```ini
GROQ_API_KEY=your-groq-key
```

### 3. Run the console

```bash
uvicorn api:app --reload
```

| URL | What it is |
|---|---|
| `http://localhost:8000/` | The console |
| `http://localhost:8000/docs` | Interactive OpenAPI documentation |
| `http://localhost:8000/api/health` | Health probe with the active configuration |

### 4. Or run the batch CLI

Put recordings in `input/` and run:

```bash
python main.py
```

Every file is processed in turn, with progress printed per chunk, and the transcripts land in `output/transcripts/`.

---

## API reference

| Method | Path | What it does |
|---|---|---|
| `GET` | `/api/health` | Active models, chunk length, supported formats and transcript count |
| `GET` | `/api/transcripts` | Every transcript in the output directory |
| `GET` | `/api/transcripts/{name}` | Read one transcript |
| `POST` | `/api/transcribe` | Split, transcribe and merge an uploaded recording |
| `POST` | `/api/extract` | Pull structured details out of a transcript |

### Transcribing

```bash
curl -X POST http://localhost:8000/api/transcribe -F "file=@call.mp3"
```

```json
{
  "filename": "call.mp3",
  "transcript": "Hello, thanks for calling support ...",
  "language": "en",
  "duration": 412.8,
  "chunks": [
    { "index": 1, "name": "chunk_001.wav", "transcript": "Hello, thanks for calling support ...", "language": "en", "duration": 120.0 }
  ],
  "characters": 4820,
  "words": 861,
  "transcript_file": "call-3f9a2b17.txt"
}
```

### Extracting details

```bash
curl -X POST http://localhost:8000/api/extract \
  -H "Content-Type: application/json" \
  -d '{"transcript": "Hello, thanks for calling support ..."}'
```

The extraction instructions live in `prompts/extraction_prompt.txt`, so you can change what gets pulled out without touching any code.

---

## Configuration

Everything tunable lives in `config.py`:

| Setting | Default | What it controls |
|---|---|---|
| `GROQ_TRANSCRIPTION_MODEL` | `whisper-large-v3` | The speech-to-text model |
| `LLM_MODEL` | `llama-3.3-70b-versatile` | The extraction model |
| `CHUNK_DURATION_MINUTES` | `2` | How long each chunk is |
| `SUPPORTED_AUDIO_EXTENSIONS` | mp3, wav, m4a, ogg, flac, aac | Accepted input formats |
| `INPUT_DIR` | `input/` | Where the CLI looks for recordings |
| `OUTPUT_DIR` | `output/` | Where chunks and transcripts are written |

---

## Project structure

```
Transcriber_GroqAPI/
├── api.py                            FastAPI application and the static mount
├── main.py                           Batch CLI over the input directory
├── config.py                         Paths, models and chunking settings
├── services/
│   ├── audio_splitter.py             Cuts recordings into WAV chunks
│   ├── speech_to_text.py             Groq transcription client
│   └── information_extractor.py      Groq extraction client
├── models/model_loader.py            Model helpers
├── prompts/extraction_prompt.txt     What to pull out of a transcript
├── input/                            Drop recordings here for the CLI
├── output/
│   ├── chunks/                       Per-recording chunk directories
│   └── transcripts/                  Finished transcripts
└── frontend/                         The console
```
