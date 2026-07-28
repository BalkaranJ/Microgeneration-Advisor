"""
Unit tests for the FastAPI backend's scoring logic (advisor.py). Solar-only:
wind scoring was removed when the product pivoted to solar.
"""

import unittest
from advisor import (
    MicrogenerationProject,
    WeatherProfile,
    SolarSuitabilityScorer,
    InvalidProjectInputError,
)


class TestValidProjectInput(unittest.TestCase):
    """Test Case 1: Valid input is accepted without raising an error."""

    def test_valid_input_creates_project(self):
        project = MicrogenerationProject(
            location="Calgary, Alberta, Canada",
            annual_usage_kwh=9000,
            system_size_kw=8.0,
            customer_type="Residential",
        )
        self.assertEqual(project.get_location(), "Calgary, Alberta, Canada")
        self.assertEqual(project.get_annual_usage(), 9000)
        self.assertEqual(project.get_system_size(), 8.0)
        self.assertEqual(project.get_customer_type(), "Residential")


class TestInvalidSystemSize(unittest.TestCase):
    """Test Case 2: System size of 0 or negative raises InvalidProjectInputError."""

    def test_zero_system_size_raises_error(self):
        with self.assertRaises(InvalidProjectInputError):
            MicrogenerationProject(
                location="Calgary, Alberta, Canada",
                annual_usage_kwh=9000,
                system_size_kw=0,
                customer_type="Residential",
            )

    def test_negative_system_size_raises_error(self):
        with self.assertRaises(InvalidProjectInputError):
            MicrogenerationProject(
                location="Calgary, Alberta, Canada",
                annual_usage_kwh=9000,
                system_size_kw=-5,
                customer_type="Residential",
            )


class TestInvalidAnnualUsage(unittest.TestCase):
    """Test Case 3: Annual usage of 0 or negative raises InvalidProjectInputError."""

    def test_zero_annual_usage_raises_error(self):
        with self.assertRaises(InvalidProjectInputError):
            MicrogenerationProject(
                location="Calgary, Alberta, Canada",
                annual_usage_kwh=0,
                system_size_kw=8.0,
                customer_type="Residential",
            )

    def test_negative_annual_usage_raises_error(self):
        with self.assertRaises(InvalidProjectInputError):
            MicrogenerationProject(
                location="Calgary, Alberta, Canada",
                annual_usage_kwh=-100,
                system_size_kw=8.0,
                customer_type="Residential",
            )


class TestMissingLocation(unittest.TestCase):
    """Test Case 4: Blank location raises InvalidProjectInputError."""

    def test_empty_location_raises_error(self):
        with self.assertRaises(InvalidProjectInputError):
            MicrogenerationProject(
                location="",
                annual_usage_kwh=9000,
                system_size_kw=8.0,
                customer_type="Residential",
            )


class TestSolarScorer(unittest.TestCase):
    """Test Case 5: Solar scorer returns a score between 0 and 100 with a reason."""

    def setUp(self):
        self.scorer = SolarSuitabilityScorer()
        self.weather = WeatherProfile(
            location="Calgary",
            solar_indicator=78,
            cloud_cover=30,
        )

    def test_solar_score_in_range(self):
        score = self.scorer.calculate_score(self.weather)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_solar_reason_is_string(self):
        score = self.scorer.calculate_score(self.weather)
        reason = self.scorer.generate_reason(score)
        self.assertIsInstance(reason, str)
        self.assertGreater(len(reason), 0)

    def test_solar_reason_mentions_solar(self):
        score = self.scorer.calculate_score(self.weather)
        reason = self.scorer.generate_reason(score)
        self.assertIn("Solar", reason)


class TestScoreBoundary(unittest.TestCase):
    """Test Case 6: Extreme weather values are clamped and stay within 0 to 100."""

    def test_solar_score_does_not_exceed_100(self):
        scorer = SolarSuitabilityScorer()
        weather = WeatherProfile(
            location="Medicine Hat",
            solar_indicator=200,
            cloud_cover=0,
        )
        score = scorer.calculate_score(weather)
        self.assertLessEqual(score, 100)

    def test_solar_score_does_not_go_below_0(self):
        scorer = SolarSuitabilityScorer()
        weather = WeatherProfile(
            location="Medicine Hat",
            solar_indicator=0,
            cloud_cover=500,
        )
        score = scorer.calculate_score(weather)
        self.assertGreaterEqual(score, 0)


if __name__ == "__main__":
    unittest.main()
