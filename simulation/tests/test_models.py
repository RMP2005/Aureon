"""Tests for simulation domain models."""

import unittest

try:
    from simulation.src.models.city import CityState, CityZone, GeoCoordinate, ResourcePool, ZoneType
    from simulation.src.models.emergency import (
        AffectedArea,
        EmergencyEvent,
        EmergencyType,
        SeverityLevel,
    )
    from simulation.src.models.environment import EnvironmentState, WeatherCondition, WeatherState
    from simulation.src.scenarios.default import create_default_city, create_default_environment
except ImportError:
    from src.models.city import CityState, CityZone, GeoCoordinate, ResourcePool, ZoneType  # type: ignore
    from src.models.emergency import (  # type: ignore
        AffectedArea,
        EmergencyEvent,
        EmergencyType,
        SeverityLevel,
    )
    from src.models.environment import EnvironmentState, WeatherCondition, WeatherState  # type: ignore
    from src.scenarios.default import create_default_city, create_default_environment  # type: ignore


class TestModels(unittest.TestCase):
    def test_weather_state_defaults(self) -> None:
        weather = WeatherState()
        self.assertEqual(weather.condition, WeatherCondition.CLEAR)
        self.assertEqual(weather.temperature_celsius, 22.0)

    def test_environment_advance_time(self) -> None:
        env = EnvironmentState(simulation_hour=6.0)
        env.advance_time(6.0)
        self.assertEqual(env.simulation_hour, 12.0)
        self.assertEqual(env.time_of_day.value, "afternoon")

    def test_environment_advance_time_wraps(self) -> None:
        env = EnvironmentState(simulation_hour=23.0)
        env.advance_time(3.0)
        self.assertEqual(env.simulation_hour, 2.0)
        self.assertEqual(env.time_of_day.value, "night")

    def test_city_zone_creation(self) -> None:
        zone = CityZone(
            id="test-zone",
            name="Test Zone",
            zone_type=ZoneType.RESIDENTIAL,
            center=GeoCoordinate(latitude=40.0, longitude=-74.0),
        )
        self.assertEqual(zone.id, "test-zone")
        self.assertEqual(zone.zone_type, ZoneType.RESIDENTIAL)

    def test_resource_pool_total(self) -> None:
        pool = ResourcePool(ambulances=5, fire_trucks=3, police_units=10, medical_teams=2)
        self.assertEqual(pool.total_units, 20)

    def test_city_state_defaults(self) -> None:
        city = CityState()
        self.assertEqual(city.name, "Aureon City")
        self.assertEqual(city.total_population, 500_000)

    def test_emergency_event(self) -> None:
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
        self.assertTrue(event.is_active)
        self.assertEqual(event.severity_multiplier, 4.0)

    def test_default_city_scenario(self) -> None:
        city = create_default_city()
        self.assertEqual(len(city.zones), 6)
        self.assertGreater(city.resources.total_units, 0)

    def test_default_environment_scenario(self) -> None:
        env = create_default_environment()
        self.assertEqual(env.simulation_hour, 8.0)


if __name__ == "__main__":
    unittest.main()
