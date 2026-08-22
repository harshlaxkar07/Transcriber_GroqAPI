from pathlib import Path

from pydub import AudioSegment

from config import (
    CHUNK_DURATION_MS,
    CHUNK_DIRECTORY,
)


class AudioSplitter:
    """
    Splits a large audio file into
    smaller chunks.
    """
    def split(
        self,
        audio_path: Path,
    ) -> list[Path]:
        """
        Split the audio into WAV chunks.
        """

        audio = AudioSegment.from_file(
            audio_path
        )

        total_duration = len(audio)

        chunk_paths = []

        chunk_directory = (
            CHUNK_DIRECTORY
            / audio_path.stem
        )

        chunk_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        chunk_number = 1

        for start in range(
            0,
            total_duration,
            CHUNK_DURATION_MS,
        ):

            end = min(
                start + CHUNK_DURATION_MS,
                total_duration,
            )

            chunk = audio[start:end]

            chunk_path = (
                chunk_directory
                / f"chunk_{chunk_number:03}.wav"
            )

            chunk.export(
                chunk_path,
                format="wav",
            )

            chunk_paths.append(
                chunk_path
            )

            chunk_number += 1

        return chunk_paths

audio_splitter = AudioSplitter()