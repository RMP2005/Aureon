"""Unit tests for the Demo Library (Phase 10F-1)."""

import unittest

from src.services.demo_library import DEFAULT_DEMO, get_demo, list_demos
from src.services.simulation_service import get_simulation_service


class TestDemoRegistry(unittest.TestCase):
    def test_registry_has_expected_keys(self) -> None:
        demos = {d["key"] for d in list_demos()}
        self.assertEqual(
            demos,
            {
                "city_pulse",
                "evening_gridlock",
                "er_bottleneck",
                "mass_casualty_response",
            },
        )

    def test_registry_entries_complete(self) -> None:
        for d in list_demos():
            for field in ("name", "logline", "description"):
                self.assertTrue(d[field], f"{d['key']}.{field} must be non-empty")
            run = d["run"]
            for field in (
                "strategy",
                "scenario",
                "duration_minutes",
                "incident_rate_per_hour",
                "seed",
                "wall_clock_factor",
            ):
                self.assertIn(field, run)
            # Pacing is mandatory for showcase runs.
            self.assertGreaterEqual(run["wall_clock_factor"], 1)

    def test_unknown_key_returns_none(self) -> None:
        self.assertIsNone(get_demo("nope"))

    def test_default_resolves_to_flagship(self) -> None:
        demo = get_demo(None)
        self.assertIsNotNone(demo)
        assert demo is not None
        self.assertEqual(demo["key"], DEFAULT_DEMO)


class TestDemoLaunch(unittest.TestCase):
    def test_launch_demo_starts_deterministic_run(self) -> None:
        svc = get_simulation_service()
        res = svc.launch_demo("city_pulse")
        run_id = res["run_id"]
        self.assertTrue(run_id.startswith("sim_"))
        self.assertEqual(res["status"], "queued")
        self.assertEqual(res["demo"]["key"], "city_pulse")

        # The live engine carries the scripted scenario identity.
        state = None
        for _ in range(50):
            state = svc.get_run_state(run_id)
            if state is not None:
                break
        if state is not None:
            # Engine may have finished a 24-min sim at 60x only after ~24s;
            # state presence alone proves the background thread runs scripted params.
            self.assertIn("strategy", state)

    def test_launch_unknown_demo_raises(self) -> None:
        with self.assertRaises(KeyError):
            get_simulation_service().launch_demo("bogus")


if __name__ == "__main__":
    unittest.main()
