"""
Unit tests for the FastAPI backend's domain logic (advisor.py). Solar-only:
wind scoring was removed when the product pivoted to solar. Weather-based
suitability scoring was removed in favor of the roof-capacity verdict in
solar.py.
"""

import unittest
from advisor import (
    MicrogenerationProject,
    ProjectClassifier,
    ReadinessAdvisor,
    InvalidProjectInputError,
    estimate_target_system_size_kw,
)


class TestValidProjectInput(unittest.TestCase):
    """Test Case 1: Valid input is accepted without raising an error."""

    def test_valid_input_creates_project(self):
        project = MicrogenerationProject(
            location="Calgary, Alberta, Canada",
            annual_usage_kwh=9000,
            system_size_kw=8.0,
        )
        self.assertEqual(project.get_location(), "Calgary, Alberta, Canada")
        self.assertEqual(project.get_annual_usage(), 9000)
        self.assertEqual(project.get_system_size(), 8.0)


class TestInvalidSystemSize(unittest.TestCase):
    """Test Case 2: System size of 0 or negative raises InvalidProjectInputError."""

    def test_zero_system_size_raises_error(self):
        with self.assertRaises(InvalidProjectInputError):
            MicrogenerationProject(
                location="Calgary, Alberta, Canada",
                annual_usage_kwh=9000,
                system_size_kw=0,
            )

    def test_negative_system_size_raises_error(self):
        with self.assertRaises(InvalidProjectInputError):
            MicrogenerationProject(
                location="Calgary, Alberta, Canada",
                annual_usage_kwh=9000,
                system_size_kw=-5,
            )


class TestInvalidAnnualUsage(unittest.TestCase):
    """Test Case 3: Annual usage of 0 or negative raises InvalidProjectInputError."""

    def test_zero_annual_usage_raises_error(self):
        with self.assertRaises(InvalidProjectInputError):
            MicrogenerationProject(
                location="Calgary, Alberta, Canada",
                annual_usage_kwh=0,
                system_size_kw=8.0,
            )

    def test_negative_annual_usage_raises_error(self):
        with self.assertRaises(InvalidProjectInputError):
            MicrogenerationProject(
                location="Calgary, Alberta, Canada",
                annual_usage_kwh=-100,
                system_size_kw=8.0,
            )


class TestMissingLocation(unittest.TestCase):
    """Test Case 4: Blank location raises InvalidProjectInputError."""

    def test_empty_location_raises_error(self):
        with self.assertRaises(InvalidProjectInputError):
            MicrogenerationProject(
                location="",
                annual_usage_kwh=9000,
                system_size_kw=8.0,
            )


class TestProjectClassifier(unittest.TestCase):
    """Test Case 5: describe() no longer references a customer type."""

    def setUp(self):
        self.classifier = ProjectClassifier()

    def test_describe_small_has_no_customer_type_wording(self):
        project = MicrogenerationProject(
            location="Calgary, Alberta, Canada",
            annual_usage_kwh=9000,
            system_size_kw=5.5,
        )
        self.assertEqual(self.classifier.describe(project), "Small solar microgeneration concept")

    def test_describe_medium_has_no_customer_type_wording(self):
        project = MicrogenerationProject(
            location="Calgary, Alberta, Canada",
            annual_usage_kwh=9000,
            system_size_kw=50,
        )
        self.assertEqual(self.classifier.describe(project), "Medium solar microgeneration concept")

    def test_describe_large_returns_category_as_is(self):
        project = MicrogenerationProject(
            location="Calgary, Alberta, Canada",
            annual_usage_kwh=9000,
            system_size_kw=200,
        )
        self.assertEqual(self.classifier.describe(project), self.classifier.classify(project))


class TestEstimateTargetSystemSize(unittest.TestCase):
    """Test Case 6: fallback system-size estimate targets a conservative ~80% offset."""

    def test_estimate_uses_conservative_offset_of_default_yield(self):
        self.assertEqual(estimate_target_system_size_kw(9000), 5.54)

    def test_estimate_scales_with_custom_yield_and_offset(self):
        # 10,000 kWh usage, 100% offset target, 1000 kWh/kW yield -> 10 kW
        result = estimate_target_system_size_kw(10000, yield_kwh_per_kw=1000, offset_target=1.0)
        self.assertEqual(result, 10.0)

    def test_zero_annual_usage_raises_error(self):
        with self.assertRaises(InvalidProjectInputError):
            estimate_target_system_size_kw(0)

    def test_negative_annual_usage_raises_error(self):
        with self.assertRaises(InvalidProjectInputError):
            estimate_target_system_size_kw(-100)


class TestReadinessAdvisorAssess(unittest.TestCase):
    """Test Case 7: ReadinessAdvisor is a classification + bottom-line facade."""

    def _project(self, system_size_kw=8.0, annual_usage_kwh=9000):
        return MicrogenerationProject(
            location="Calgary, Alberta, Canada",
            annual_usage_kwh=annual_usage_kwh,
            system_size_kw=system_size_kw,
        )

    def _roof(self, verdict, panels_count=18, offset_pct=105.5, imagery_date="2024-08-29"):
        return {
            "verdict": verdict,
            "panels_count": panels_count,
            "imagery_date": imagery_date,
            "comparison": {"offset_pct": offset_pct},
        }

    def test_assess_returns_classification_size_category_and_bottom_line_only(self):
        result = ReadinessAdvisor().assess(self._project())
        self.assertEqual(set(result.keys()), {"classification", "size_category", "bottom_line"})

    def test_bottom_line_has_tone_headline_body_and_action(self):
        bottom_line = ReadinessAdvisor().assess(self._project())["bottom_line"]
        self.assertEqual(set(bottom_line.keys()), {"tone", "headline", "body", "action"})
        self.assertEqual(set(bottom_line["action"].keys()), {"type", "label"})

    def test_bottom_line_always_cites_the_annual_usage_figure(self):
        bottom_line = ReadinessAdvisor().assess(self._project(annual_usage_kwh=12345))["bottom_line"]
        self.assertIn("12,345 kWh", bottom_line["body"])

    def test_bottom_line_for_no_roof_data(self):
        bottom_line = ReadinessAdvisor().assess(
            self._project(), roof_solar_potential=None, system_size_basis="usage_estimate"
        )["bottom_line"]
        self.assertEqual(bottom_line["tone"], "neutral")
        self.assertIn("regional average", bottom_line["body"])
        self.assertEqual(bottom_line["action"]["type"], "go")

    def test_bottom_line_for_full_coverage(self):
        bottom_line = ReadinessAdvisor().assess(
            self._project(),
            roof_solar_potential=self._roof("full_coverage"),
            system_size_basis="roof_matched",
        )["bottom_line"]
        self.assertEqual(bottom_line["tone"], "good")
        self.assertEqual(bottom_line["headline"], "Get quotes. This pencils out.")
        self.assertIn("18 panels", bottom_line["body"])
        self.assertIn("2024-08-29", bottom_line["body"])
        self.assertEqual(bottom_line["action"]["type"], "go")

    def test_bottom_line_for_partial_coverage(self):
        bottom_line = ReadinessAdvisor().assess(
            self._project(),
            roof_solar_potential=self._roof("partial_coverage", offset_pct=60.0),
            system_size_basis="roof_matched",
        )["bottom_line"]
        self.assertEqual(bottom_line["tone"], "warn")
        self.assertIn("won't cover everything", bottom_line["headline"])
        self.assertEqual(bottom_line["action"]["type"], "go")

    def test_bottom_line_for_too_small(self):
        bottom_line = ReadinessAdvisor().assess(
            self._project(),
            roof_solar_potential=self._roof("too_small", offset_pct=20.1),
            system_size_basis="roof_matched",
        )["bottom_line"]
        self.assertEqual(bottom_line["tone"], "bad")
        self.assertEqual(bottom_line["headline"], "Skip it, at least for this roof.")
        self.assertIn("not any other roof or ground space on the property", bottom_line["body"])
        self.assertEqual(bottom_line["action"]["type"], "skip")

    def test_bottom_line_flags_large_out_of_scope_systems(self):
        bottom_line = ReadinessAdvisor().assess(self._project(system_size_kw=200))["bottom_line"]
        self.assertIn("outside typical residential microgeneration", bottom_line["body"])


if __name__ == "__main__":
    unittest.main()
