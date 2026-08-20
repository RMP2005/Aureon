"""Default scenario configuration for initial city state."""

from ..models.city import (
    CityState,
    CityZone,
    GeoCoordinate,
    ResourcePool,
    TrafficState,
    ZoneType,
)
from ..models.environment import EnvironmentState, WeatherState


def create_default_city() -> CityState:
    """Create a default Bangalore city configuration for testing."""
    zones = [
        CityZone(
            id="zone-indiranagar",
            name="Indiranagar",
            zone_type=ZoneType.COMMERCIAL,
            center=GeoCoordinate(latitude=12.9719, longitude=77.6412),
            area_sq_km=5.2,
            population=95_000,
            population_density=18_269,
        ),
        CityZone(
            id="zone-koramangala",
            name="Koramangala",
            zone_type=ZoneType.MIXED_USE,
            center=GeoCoordinate(latitude=12.9352, longitude=77.6245),
            area_sq_km=7.1,
            population=150_000,
            population_density=21_127,
        ),
        CityZone(
            id="zone-whitefield",
            name="Whitefield",
            zone_type=ZoneType.COMMERCIAL,
            center=GeoCoordinate(latitude=12.9863, longitude=77.7342),
            area_sq_km=10.5,
            population=200_000,
            population_density=19_048,
        ),
        CityZone(
            id="zone-electronic-city",
            name="Electronic City",
            zone_type=ZoneType.INDUSTRIAL,
            center=GeoCoordinate(latitude=12.8399, longitude=77.6770),
            area_sq_km=8.0,
            population=80_000,
            population_density=10_000,
        ),
        CityZone(
            id="zone-hebbal",
            name="Hebbal",
            zone_type=ZoneType.TRANSPORT,
            center=GeoCoordinate(latitude=13.0358, longitude=77.5970),
            area_sq_km=4.5,
            population=60_000,
            population_density=13_333,
        ),
        CityZone(
            id="zone-yeshwanthpur",
            name="Yeshwanthpur",
            zone_type=ZoneType.COMMERCIAL,
            center=GeoCoordinate(latitude=13.0280, longitude=77.5408),
            area_sq_km=6.0,
            population=110_000,
            population_density=18_333,
        ),
    ]

    resources = ResourcePool(
        ambulances=14,
        fire_trucks=10,
        police_units=30,
        medical_teams=8,
        shelters_capacity=3_000,
    )

    return CityState(
        name="Bangalore",
        total_population=694_000,
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
