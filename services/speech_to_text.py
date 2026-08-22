from pathlib import Path

from groq import Groq

from config import (
    GROQ_API_KEY,
    GROQ_TRANSCRIPTION_MODEL,
    SUPPORTED_AUDIO_EXTENSIONS,
)


class SpeechToTextService:
    """
    Speech-to-text using the Groq API.
    """

    def __init__(self):
        self.client = Groq(
            api_key=GROQ_API_KEY,
        )

    def validate_audio_file(
        self,
        audio_path: Path,
    ):

        if not audio_path.exists():
            raise FileNotFoundError(
                f"{audio_path} not found."
            )

        if audio_path.suffix.lower() not in SUPPORTED_AUDIO_EXTENSIONS:
            raise ValueError(
                f"Unsupported file: {audio_path.suffix}"
            )

    def transcribe(
        self,
        audio_path: Path,
    ) -> dict:

        self.validate_audio_file(audio_path)

        with open(audio_path, "rb") as audio:

            transcription = self.client.audio.transcriptions.create(
                file=audio,
                model=GROQ_TRANSCRIPTION_MODEL,
                response_format="verbose_json",
            )

        return {
            "transcript": transcription.text,
            "language": transcription.language,
            "duration": transcription.duration,
            "segments": transcription.segments,
        }


speech_to_text_service = SpeechToTextService()