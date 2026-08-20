"""Default scenario configuration for initial city state."""

from src.models.city import (
    CityState,
    CityZone,
    GeoCoordinate,
    ResourcePool,
    TrafficState,
    ZoneType,
)
from src.models.environment import EnvironmentState, WeatherState


def create_default_city() -> CityState:
    """Create a default city configuration for testing."""
    zones = [
        CityZone(
            id="zone-downtown",
            name="Downtown Core",
            zone_type=ZoneType.COMMERCIAL,
            center=GeoCoordinate(latitude=40.7128, longitude=-74.0060),
            area_sq_km=4.5,
            population=85_000,
            population_density=18_889,
        ),
        CityZone(
            id="zone-residential-north",
            name="North Residential",
            zone_type=ZoneType.RESIDENTIAL,
            center=GeoCoordinate(latitude=40.7300, longitude=-74.0000),
            area_sq_km=8.0,
            population=120_000,
            population_density=15_000,
        ),
        CityZone(
            id="zone-industrial-east",
            name="East Industrial",
            zone_type=ZoneType.INDUSTRIAL,
            center=GeoCoordinate(latitude=40.7100, longitude=-73.9800),
            area_sq_km=6.0,
            population=15_000,
            population_density=2_500,
        ),
        CityZone(
            id="zone-park-central",
            name="Central Park District",
            zone_type=ZoneType.PARK,
            center=GeoCoordinate(latitude=40.7200, longitude=-73.9950),
            area_sq_km=3.5,
            population=5_000,
            population_density=1_429,
        ),
        CityZone(
            id="zone-mixed-south",
            name="South Mixed Use",
            zone_type=ZoneType.MIXED_USE,
            center=GeoCoordinate(latitude=40.7000, longitude=-74.0100),
            area_sq_km=5.5,
            population=75_000,
            population_density=13_636,
        ),
    ]

    resources = ResourcePool(
        ambulances=25,
        fire_trucks=18,
        police_units=40,
        medical_teams=12,
        shelters_capacity=5_000,
    )

    return CityState(
        name="Aureon City",
        total_population=300_000,
        zones=zones,
        resources=resources,
        traffic=TrafficState(),
    )


def create_default_environment() -> EnvironmentState:
    """Create a default environment configuration."""
    return EnvironmentState(
        weather=WeatherState(),
        time_of_day="morning",
        simulation_hour=8.0,
    )
