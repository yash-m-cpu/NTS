from typing import List, Dict

class DiarizationService:
    """
    Adapter for Speaker Diarization (e.g., PyAnnote).
    Currently implemented as a mock that assumes a single speaker or simple splits,
    as heavy PyAnnote models are omitted from this baseline container.
    """
    
    async def diarize(self, audio_path: str) -> List[Dict]:
        """
        Returns a list of diarization segments:
        [ {"start": 0.0, "end": 99999.0, "speaker": "speaker_0"}, ... ]
        """
        # Mock implementation: just return one giant segment for speaker_0
        # In a real implementation, this would run pyannote.audio
        return [{"start": 0.0, "end": 99999.0, "speaker": "speaker_0"}]

diarization_service = DiarizationService()
