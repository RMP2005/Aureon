"""Tests for simulation domain models."""

from src.models.city import CityState, CityZone, GeoCoordinate, ResourcePool, ZoneType
from src.models.emergency import (
    AffectedArea,
    EmergencyEvent,
    EmergencyType,
    SeverityLevel,
)
from src.models.environment import EnvironmentState, WeatherCondition, WeatherState
from src.scenarios.default import create_default_city, create_default_environment


def test_weather_state_defaults() -> None:
    weather = WeatherState()
    assert weather.condition == WeatherCondition.CLEAR
    assert weather.temperature_celsius == 22.0


def test_environment_advance_time() -> None:
    env = EnvironmentState(simulation_hour=6.0)
    env.advance_time(6.0)
    assert env.simulation_hour == 12.0
    assert env.time_of_day.value == "afternoon"


def test_environment_advance_time_wraps() -> None:
    env = EnvironmentState(simulation_hour=23.0)
    env.advance_time(3.0)
    assert env.simulation_hour == 2.0
    assert env.time_of_day.value == "night"


def test_city_zone_creation() -> None:
    zone = CityZone(
        id="test-zone",
        name="Test Zone",
        zone_type=ZoneType.RESIDENTIAL,
        center=GeoCoordinate(latitude=40.0, longitude=-74.0),
    )
    assert zone.id == "test-zone"
    assert zone.zone_type == ZoneType.RESIDENTIAL


def test_resource_pool_total() -> None:
    pool = ResourcePool(ambulances=5, fire_trucks=3, police_units=10, medical_teams=2)
    assert pool.total_units == 20


def test_city_state_defaults() -> None:
    city = CityState()
    assert city.name == "Aureon City"
    assert city.total_population == 500_000


def test_emergency_event() -> None:
    event = EmergencyEvent(
        id="evt-001",
        event_type=EmergencyType.FIRE,
        severity=SeverityLevel.HIGH,
        title="Warehouse Fire",
        affected_area=AffectedArea(
            center=GeoCoordinate(latitude=40.71, longitude=-74.01),
            radius_km=0.3,
            affected_population=500,
        ),
    )
    assert event.is_active
    assert event.severity_multiplier == 4.0


def test_default_city_scenario() -> None:
    city = create_default_city()
    assert len(city.zones) == 5
    assert city.resources.total_units > 0


def test_default_environment_scenario() -> None:
    env = create_default_environment()
    assert env.simulation_hour == 8.0
