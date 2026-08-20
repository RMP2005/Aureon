"""Environment models for urban simulation.

Defines weather conditions, time of day, terrain, and environmental
factors that affect the simulation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


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


@dataclass
class WeatherState:
    """Current weather conditions in the simulation."""

    condition: WeatherCondition = WeatherCondition.CLEAR
    temperature_celsius: float = 22.0
    humidity_percent: float = 45.0
    wind_speed_kmh: float = 10.0
    wind_direction: WindDirection = WindDirection.N
    visibility_km: float = 10.0
    precipitation_mm_hr: float = 0.0


@dataclass
class EnvironmentState:
    """Complete environment state for the simulation."""

    weather: WeatherState = field(default_factory=WeatherState)
    time_of_day: TimeOfDay = TimeOfDay.MORNING
    simulation_hour: float = 8.0
    air_quality_index: int = 50
    noise_level_db: float = 55.0

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
