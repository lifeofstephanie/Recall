import os
import torch
import whisper
import tempfile

torch.set_num_threads(2)

class TranscriptionService:
    """
    Wraps the local OpenAI Whisper model for speech-to-text.

    Model sizes (trade-off between speed and accuracy):
    - tiny   → fastest, least accurate (~39MB)
    - base   → good balance for simple queries (~74MB)
    - small  → better accuracy, still fast (~244MB)  ← we use this
    - medium → very accurate, slower (~769MB)
    - large  → best accuracy, slowest (~1.5GB)

    For movie quote/scene descriptions, 'small' hits the sweet spot.
    Can be overridden via WHISPER_MODEL in .env
    """

    def __init__(self):
        model_size = os.getenv("WHISPER_MODEL", "small")
        print(f"   Loading Whisper '{model_size}' model...")
        self.model = whisper.load_model(model_size)

    def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        """
        Transcribe raw audio bytes to text.

        Writes audio to a temp file (Whisper requires a file path),
        transcribes it, then cleans up automatically.

        Returns the transcribed text string.
        """
        suffix = os.path.splitext(filename)[-1] or ".webm"

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()

            result = self.model.transcribe(
                tmp.name,
                language="en",         # Force English for faster inference
                fp16=False,            # fp16 can cause issues on CPU
                verbose=False,
            )

        transcript = result.get("text", "").strip()
        return transcript