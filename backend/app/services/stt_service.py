from faster_whisper import WhisperModel
import asyncio
from concurrent.futures import ThreadPoolExecutor

class STTService:
    def __init__(self, model_size="tiny", compute_type="int8"):
        # run in thread so it doesn't block async init
        self.model_size = model_size
        self.compute_type = compute_type
        self._model = None
        self._executor = ThreadPoolExecutor(max_workers=1)

    def _get_model(self):
        if self._model is None:
            self._model = WhisperModel(self.model_size, device="cpu", compute_type=self.compute_type)
        return self._model

    def _transcribe_sync(self, audio_path: str):
        model = self._get_model()
        segments, info = model.transcribe(audio_path, beam_size=1, word_timestamps=True)
        return list(segments)

    async def transcribe(self, audio_path: str):
        loop = asyncio.get_event_loop()
        segments = await loop.run_in_executor(self._executor, self._transcribe_sync, audio_path)
        return segments

stt_service = STTService()
