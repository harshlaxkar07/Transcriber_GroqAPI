from pathlib import Path

from config import (
    INPUT_DIR,
    OUTPUT_DIR,
    SUPPORTED_AUDIO_EXTENSIONS,
)

from services.audio_splitter import audio_splitter
from services.speech_to_text import speech_to_text_service


TRANSCRIPT_DIRECTORY = OUTPUT_DIR / "transcripts"
TRANSCRIPT_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)


def get_audio_files() -> list[Path]:
    """
    Returns all supported audio files
    inside the input directory.
    """

    audio_files = []

    for file in sorted(INPUT_DIR.iterdir()):

        if (
            file.is_file()
            and file.suffix.lower() in SUPPORTED_AUDIO_EXTENSIONS
        ):
            audio_files.append(file)

    if not audio_files:
        raise FileNotFoundError(
            "No supported audio files found."
        )

    return audio_files


def save_transcript(
    audio_file: Path,
    transcript: str,
) -> Path:
    """
    Save the merged transcript.
    """

    transcript_path = (
        TRANSCRIPT_DIRECTORY
        / f"{audio_file.stem}.txt"
    )

    transcript_path.write_text(
        transcript,
        encoding="utf-8",
    )

    return transcript_path


def process_audio(
    audio_file: Path,
) -> None:
    """
    Process one audio recording.
    """

    print("\n" + "=" * 70)
    print(f"Processing : {audio_file.name}")
    print("=" * 70)

    print("\nSplitting audio...")

    chunks = audio_splitter.split(
        audio_file
    )

    print(
        f"Created {len(chunks)} chunks."
    )

    transcripts = []

    total_chunks = len(chunks)

    for index, chunk in enumerate(
        chunks,
        start=1,
    ):

        print(
            f"[{index}/{total_chunks}] "
            f"Transcribing {chunk.name}"
        )

        result = speech_to_text_service.transcribe(
            chunk
        )

        transcripts.append(
            result["transcript"]
        )

    final_transcript = "\n\n".join(
        transcripts
    )

    transcript_file = save_transcript(
        audio_file,
        final_transcript,
    )

    print("\nCompleted Successfully")

    print(
        f"Language      : {result['language']}"
    )

    print(
        f"Duration      : {result['duration']} sec"
    )

    print(
        f"Chunks        : {total_chunks}"
    )

    print(
        f"Characters    : "
        f"{len(final_transcript)}"
    )

    print(
        f"Transcript    : "
        f"{transcript_file}"
    )


def main():
    """
    Project entry point.
    """

    print("=" * 70)
    print("CALL INFORMATION EXTRACTOR")
    print("=" * 70)

    audio_files = get_audio_files()

    print(
        f"\nFound {len(audio_files)} audio file(s).\n"
    )

    for audio_file in audio_files:
        process_audio(audio_file)

    print("\n" + "=" * 70)
    print("ALL AUDIO FILES PROCESSED")
    print("=" * 70)


if __name__ == "__main__":
    main()