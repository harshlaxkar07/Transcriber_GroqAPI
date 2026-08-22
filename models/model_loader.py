from faster_whisper import WhisperModel

from config import (
    WHISPER_MODEL,
    DEVICE,
    COMPUTE_TYPE,
)


class ModelLoader:
    """
    Loads and stores AI models used by the project.
    """

    def __init__(self):
        self.whisper_model = None

    def load_models(self):
        """
        Load all required AI models into memory.
        """

        if self.whisper_model is None:
            print(f"Loading Whisper model: {WHISPER_MODEL}")

            self.whisper_model = WhisperModel(
                model_size_or_path=WHISPER_MODEL,
                device=DEVICE,
                compute_type=COMPUTE_TYPE,
            )

            print("Whisper model loaded successfully.")

    def get_whisper_model(self):
        """
        Returns the loaded Whisper model.
        """

        if self.whisper_model is None:
            self.load_models()

        return self.whisper_model


model_loader = ModelLoader()