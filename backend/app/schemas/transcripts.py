from pydantic import BaseModel
from typing import List, Optional

class Word(BaseModel):
    word: str
    start: float
    end: float
    probability: float

class SpeakerTurn(BaseModel):
    speaker: str
    start: float
    end: float
    text: str
    words: List[Word]

class Transcript(BaseModel):
    turns: List[SpeakerTurn]
