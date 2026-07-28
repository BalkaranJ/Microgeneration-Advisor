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
    """Test Case 7: ReadinessAdvisor is a lean classification+checklist facade now."""

    def test_assess_returns_classification_size_category_and_checklist_only(self):
        project = MicrogenerationProject(
            location="Calgary, Alberta, Canada",
            annual_usage_kwh=9000,
            system_size_kw=8.0,
        )
        result = ReadinessAdvisor().assess(project)
        self.assertEqual(set(result.keys()), {"classification", "size_category", "checklist"})

    def test_checklist_is_nonempty_list_of_strings(self):
        project = MicrogenerationProject(
            location="Calgary, Alberta, Canada",
            annual_usage_kwh=9000,
            system_size_kw=8.0,
        )
        checklist = ReadinessAdvisor().assess(project)["checklist"]
        self.assertGreater(len(checklist), 0)
        self.assertTrue(all(isinstance(item, str) for item in checklist))


if __name__ == "__main__":
    unittest.main()
