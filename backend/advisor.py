"""
Core scoring logic — same OOP design as the MVP, decoupled from Streamlit.
Solar-only: wind scoring was removed when the product pivoted to solar.
"""

from abc import ABC, abstractmethod


class InvalidProjectInputError(Exception):
    pass


def rating_label(score):
    if score >= 70:
        return "Strong"
    elif score >= 50:
        return "Moderate"
    else:
        return "Weak"


class MicrogenerationProject:
    def __init__(self, location, annual_usage_kwh, system_size_kw, customer_type):
        self._location = location
        self._annual_usage_kwh = annual_usage_kwh
        self._system_size_kw = system_size_kw
        self._customer_type = customer_type
        self.validate_inputs()

    def validate_inputs(self):
        if not self._location:
            raise InvalidProjectInputError("Location is required.")
        if self._annual_usage_kwh <= 0:
            raise InvalidProjectInputError("Annual electricity usage must be greater than zero.")
        if self._system_size_kw <= 0:
            raise InvalidProjectInputError("Proposed system size must be greater than zero.")

    def get_location(self):      return self._location
    def get_annual_usage(self):  return self._annual_usage_kwh
    def get_system_size(self):   return self._system_size_kw
    def get_customer_type(self): return self._customer_type


class WeatherProfile:
    def __init__(self, location, solar_indicator, cloud_cover):
        self._location = location
        self._solar_indicator = solar_indicator
        self._cloud_cover = cloud_cover

    def get_solar_indicator(self): return self._solar_indicator
    def get_cloud_cover(self):     return self._cloud_cover


class SuitabilityScorer(ABC):
    @abstractmethod
    def calculate_score(self, weather_profile): pass

    @abstractmethod
    def generate_reason(self, score): pass

    @staticmethod
    def _clamp(value):
        return max(0, min(100, value))


class SolarSuitabilityScorer(SuitabilityScorer):
    def calculate_score(self, weather_profile):
        score = (weather_profile.get_solar_indicator()
                 - weather_profile.get_cloud_cover() * 0.2)
        return self._clamp(score)

    def generate_reason(self, score):
        rating = rating_label(score)
        if rating == "Strong":
            return "Solar conditions appear strong for this location."
        elif rating == "Moderate":
            return "Solar conditions appear moderate for this location."
        return "Solar conditions appear weak for this location."


class ProjectClassifier:
    def classify(self, project):
        size = project.get_system_size()
        if size <= 10:
            return "Small microgeneration concept"
        elif size <= 150:
            return "Medium microgeneration concept"
        return "Large or out-of-scope concept requiring deeper review"

    def describe(self, project):
        category = self.classify(project)
        if category.startswith("Large"):
            return category
        size_word = category.split()[0]
        customer = project.get_customer_type().lower()
        return "%s %s solar microgeneration concept" % (size_word, customer)


class ReadinessAdvisor:
    def __init__(self):
        self._scorer = SolarSuitabilityScorer()
        self._classifier = ProjectClassifier()

    def assess(self, project, weather):
        value = self._scorer.calculate_score(weather)
        solar = {
            "score":  round(value, 1),
            "rating": rating_label(value),
            "reason": self._scorer.generate_reason(value),
        }
        return {
            "classification":  self._classifier.describe(project),
            "size_category":   self._classifier.classify(project),
            "solar":           solar,
            "recommendation":  self._build_recommendation(solar),
            "checklist":       self._build_checklist(),
        }

    def _build_recommendation(self, solar):
        return ("For a solar project, this location scores %s/100 (%s). %s "
                "Consider reviewing the readiness checklist before going further."
                % (solar["score"], solar["rating"].lower(), solar["reason"]))

    def _build_checklist(self):
        return [
            "Confirm annual electricity usage from utility bills",
            "Confirm proposed system size with a qualified installer",
            "Review utility interconnection requirements",
            "Confirm equipment and safety requirements",
            "Confirm site details such as roof orientation and shading",
            "Understand that this result is only a pre-application estimate",
        ]
