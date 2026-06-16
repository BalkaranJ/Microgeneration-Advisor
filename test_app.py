"""
Unit tests for Microgeneration Readiness Advisor
Covers all 8 planned test cases from Phase 2 Part D.
"""

import unittest
from app import (
    MicrogenerationProject,
    WeatherProfile,
    SolarSuitabilityScorer,
    WindSuitabilityScorer,
    InvalidProjectInputError,
)


class TestValidProjectInput(unittest.TestCase):
    """Test Case 1: Valid input is accepted without raising an error."""

    def test_valid_input_creates_project(self):
        project = MicrogenerationProject(
            location="Calgary",
            technology_type="solar",
            annual_usage_kwh=9000,
            system_size_kw=8.0,
            customer_type="Residential",
        )
        self.assertEqual(project.get_location(), "Calgary")
        self.assertEqual(project.get_technology_type(), "solar")
        self.assertEqual(project.get_annual_usage(), 9000)
        self.assertEqual(project.get_system_size(), 8.0)
        self.assertEqual(project.get_customer_type(), "Residential")


class TestInvalidSystemSize(unittest.TestCase):
    """Test Case 2: System size of 0 or negative raises InvalidProjectInputError."""

    def test_zero_system_size_raises_error(self):
        with self.assertRaises(InvalidProjectInputError):
            MicrogenerationProject(
                location="Calgary",
                technology_type="solar",
                annual_usage_kwh=9000,
                system_size_kw=0,
                customer_type="Residential",
            )

    def test_negative_system_size_raises_error(self):
        with self.assertRaises(InvalidProjectInputError):
            MicrogenerationProject(
                location="Calgary",
                technology_type="solar",
                annual_usage_kwh=9000,
                system_size_kw=-5,
                customer_type="Residential",
            )


class TestInvalidAnnualUsage(unittest.TestCase):
    """Test Case 3: Annual usage of 0 or negative raises InvalidProjectInputError."""

    def test_zero_annual_usage_raises_error(self):
        with self.assertRaises(InvalidProjectInputError):
            MicrogenerationProject(
                location="Calgary",
                technology_type="solar",
                annual_usage_kwh=0,
                system_size_kw=8.0,
                customer_type="Residential",
            )

    def test_negative_annual_usage_raises_error(self):
        with self.assertRaises(InvalidProjectInputError):
            MicrogenerationProject(
                location="Calgary",
                technology_type="solar",
                annual_usage_kwh=-100,
                system_size_kw=8.0,
                customer_type="Residential",
            )


class TestMissingLocation(unittest.TestCase):
    """Test Case 4: Blank or unknown location raises InvalidProjectInputError."""

    def test_empty_location_raises_error(self):
        with self.assertRaises(InvalidProjectInputError):
            MicrogenerationProject(
                location="",
                technology_type="solar",
                annual_usage_kwh=9000,
                system_size_kw=8.0,
                customer_type="Residential",
            )

    def test_unknown_location_raises_error(self):
        with self.assertRaises(InvalidProjectInputError):
            MicrogenerationProject(
                location="Atlantis",
                technology_type="solar",
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
            wind_indicator=55,
            cloud_cover=30,
            wind_consistency=50,
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


class TestWindScorer(unittest.TestCase):
    """Test Case 6: Wind scorer returns a score between 0 and 100 with a reason."""

    def setUp(self):
        self.scorer = WindSuitabilityScorer()
        self.weather = WeatherProfile(
            location="Lethbridge",
            solar_indicator=75,
            wind_indicator=80,
            cloud_cover=28,
            wind_consistency=72,
        )

    def test_wind_score_in_range(self):
        score = self.scorer.calculate_score(self.weather)
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    def test_wind_reason_is_string(self):
        score = self.scorer.calculate_score(self.weather)
        reason = self.scorer.generate_reason(score)
        self.assertIsInstance(reason, str)
        self.assertGreater(len(reason), 0)

    def test_wind_reason_mentions_wind(self):
        score = self.scorer.calculate_score(self.weather)
        reason = self.scorer.generate_reason(score)
        self.assertIn("Wind", reason)


class TestPolymorphism(unittest.TestCase):
    """Test Case 7: Both scorers work through the same loop using identical method calls."""

    def test_both_scorers_respond_to_same_methods(self):
        weather = WeatherProfile(
            location="Edmonton",
            solar_indicator=70,
            wind_indicator=48,
            cloud_cover=38,
            wind_consistency=45,
        )
        scorers = [SolarSuitabilityScorer(), WindSuitabilityScorer()]
        results = []

        for scorer in scorers:
            score = scorer.calculate_score(weather)
            reason = scorer.generate_reason(score)
            results.append((score, reason))

        self.assertEqual(len(results), 2)
        solar_score, solar_reason = results[0]
        wind_score, wind_reason = results[1]

        self.assertNotEqual(solar_score, wind_score)
        self.assertIn("Solar", solar_reason)
        self.assertIn("Wind", wind_reason)


class TestScoreBoundary(unittest.TestCase):
    """Test Case 8: Extreme weather values are clamped and stay within 0 to 100."""

    def test_solar_score_does_not_exceed_100(self):
        scorer = SolarSuitabilityScorer()
        weather = WeatherProfile(
            location="Medicine Hat",
            solar_indicator=200,
            wind_indicator=0,
            cloud_cover=0,
            wind_consistency=0,
        )
        score = scorer.calculate_score(weather)
        self.assertLessEqual(score, 100)

    def test_solar_score_does_not_go_below_0(self):
        scorer = SolarSuitabilityScorer()
        weather = WeatherProfile(
            location="Medicine Hat",
            solar_indicator=0,
            wind_indicator=0,
            cloud_cover=500,
            wind_consistency=0,
        )
        score = scorer.calculate_score(weather)
        self.assertGreaterEqual(score, 0)

    def test_wind_score_does_not_exceed_100(self):
        scorer = WindSuitabilityScorer()
        weather = WeatherProfile(
            location="Medicine Hat",
            solar_indicator=0,
            wind_indicator=200,
            cloud_cover=0,
            wind_consistency=200,
        )
        score = scorer.calculate_score(weather)
        self.assertLessEqual(score, 100)

    def test_wind_score_does_not_go_below_0(self):
        scorer = WindSuitabilityScorer()
        weather = WeatherProfile(
            location="Medicine Hat",
            solar_indicator=0,
            wind_indicator=0,
            cloud_cover=0,
            wind_consistency=0,
        )
        score = scorer.calculate_score(weather)
        self.assertGreaterEqual(score, 0)


if __name__ == "__main__":
    unittest.main()
