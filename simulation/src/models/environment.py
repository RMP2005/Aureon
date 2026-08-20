"""Environment models for urban simulation.

Defines weather conditions, time of day, terrain, and environmental
factors that affect the simulation.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class WeatherCondition(str, Enum):
    """Weather condition types."""

    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    STORM = "storm"
    SNOW = "snow"
    FOG = "fog"
    EXTREME_HEAT = "extreme_heat"


class TimeOfDay(str, Enum):
    """Time period categories."""

    DAWN = "dawn"
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"


class WindDirection(str, Enum):
    """Cardinal wind directions."""

    N = "N"
    NE = "NE"
    E = "E"
    SE = "SE"
    S = "S"
    SW = "SW"
    W = "W"
    NW = "NW"


class WeatherState(BaseModel):
    """Current weather conditions in the simulation."""

    condition: WeatherCondition = WeatherCondition.CLEAR
    temperature_celsius: float = Field(default=22.0, ge=-50.0, le=60.0)
    humidity_percent: float = Field(default=45.0, ge=0.0, le=100.0)
    wind_speed_kmh: float = Field(default=10.0, ge=0.0, le=400.0)
    wind_direction: WindDirection = WindDirection.N
    visibility_km: float = Field(default=10.0, ge=0.0, le=100.0)
    precipitation_mm_hr: float = Field(default=0.0, ge=0.0)


class EnvironmentState(BaseModel):
    """Complete environment state for the simulation."""

    weather: WeatherState = Field(default_factory=WeatherState)
    time_of_day: TimeOfDay = TimeOfDay.MORNING
    simulation_hour: float = Field(default=8.0, ge=0.0, lt=24.0)
    air_quality_index: int = Field(default=50, ge=0, le=500)
    noise_level_db: float = Field(default=55.0, ge=0.0, le=200.0)

    def advance_time(self, hours: float) -> None:
        """Advance simulation clock and update time of day."""
        self.simulation_hour = (self.simulation_hour + hours) % 24.0
        if 5.0 <= self.simulation_hour < 7.0:
            self.time_of_day = TimeOfDay.DAWN
        elif 7.0 <= self.simulation_hour < 12.0:
            self.time_of_day = TimeOfDay.MORNING
        elif 12.0 <= self.simulation_hour < 17.0:
            self.time_of_day = TimeOfDay.AFTERNOON
        elif 17.0 <= self.simulation_hour < 21.0:
            self.time_of_day = TimeOfDay.EVENING
        else:
            self.time_of_day = TimeOfDay.NIGHT
