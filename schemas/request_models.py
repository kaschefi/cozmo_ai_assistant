from pydantic import BaseModel, Field
from typing import Optional

class MoveRequest(BaseModel):
    distance: float = Field(
        ...,
        description="The distance in millimeters to drive forward (positive) or backward (negative)."
    )
    speed: float = Field(
        default=50.0,
        ge=10,
        le=200,
        description="The speed to drive in mm/s. Default is 50."
    )

class SpeakRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=250,
        description="The text you want Cozmo to say out loud."
    )
    play_animation: bool = Field(
        default=True,
        description="If true, Cozmo will act out the speech with animations."
    )
    language: str = Field(
        default="fa",
        description="The language of the speech. Default is persian."
    )

class HeadRequest(BaseModel):
    angle: float = Field(
        ...,
        ge=-25,
        le=44.5,
        description="The angle in degrees to move the head. Range is approx -25 (down) to 45 (up)."
    )

class LiftRequest(BaseModel):
    height: float = Field(
        ...,
        ge=0,
        le=1,
        description="The height of the lift from 0.0 (bottom) to 1.0 (top)."
    )