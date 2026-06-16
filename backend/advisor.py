"""
Core scoring logic — same OOP design as the MVP, decoupled from Streamlit.
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
    def __init__(self, location, technology_type, annual_usage_kwh,
                 system_size_kw, customer_type):
        self._location = location
        self._technology_type = technology_type
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
    def get_technology_type(self): return self._technology_type
    def get_annual_usage(self):  return self._annual_usage_kwh
    def get_system_size(self):   return self._system_size_kw
    def get_customer_type(self): return self._customer_type


class WeatherProfile:
    def __init__(self, location, solar_indicator, wind_indicator,
                 cloud_cover, wind_consistency):
        self._location = location
        self._solar_indicator = solar_indicator
        self._wind_indicator = wind_indicator
        self._cloud_cover = cloud_cover
        self._wind_consistency = wind_consistency

    def get_solar_indicator(self):  return self._solar_indicator
    def get_wind_indicator(self):   return self._wind_indicator
    def get_cloud_cover(self):      return self._cloud_cover
    def get_wind_consistency(self): return self._wind_consistency


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


class WindSuitabilityScorer(SuitabilityScorer):
    def calculate_score(self, weather_profile):
        score = (weather_profile.get_wind_indicator() * 0.7
                 + weather_profile.get_wind_consistency() * 0.3)
        return self._clamp(score)

    def generate_reason(self, score):
        rating = rating_label(score)
        if rating == "Strong":
            return "Wind conditions appear strong for this location."
        elif rating == "Moderate":
            return "Wind conditions appear moderate for this location."
        return "Wind conditions appear weak for this location."


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
        tech_words = {"solar": "solar", "wind": "wind", "compare": "solar and wind"}
        tech = tech_words.get(project.get_technology_type(), "")
        return "%s %s %s microgeneration concept" % (size_word, customer, tech)


class ReadinessAdvisor:
    def __init__(self):
        self._scorers = {
            "solar": SolarSuitabilityScorer(),
            "wind":  WindSuitabilityScorer(),
        }
        self._classifier = ProjectClassifier()

    def assess(self, project, weather):
        scores = {}
        for name, scorer in self._scorers.items():
            value = scorer.calculate_score(weather)
            scores[name] = {
                "score":  round(value, 1),
                "rating": rating_label(value),
                "reason": scorer.generate_reason(value),
            }
        return {
            "classification":  self._classifier.describe(project),
            "size_category":   self._classifier.classify(project),
            "solar":           scores["solar"],
            "wind":            scores["wind"],
            "recommendation":  self._build_recommendation(project, scores),
            "checklist":       self._build_checklist(),
        }

    def _build_recommendation(self, project, scores):
        tech  = project.get_technology_type()
        solar = scores["solar"]
        wind  = scores["wind"]
        if tech == "solar":
            return ("For a solar project, this location scores %s/100 (%s). %s "
                    "Consider reviewing the readiness checklist before going further."
                    % (solar["score"], solar["rating"].lower(), solar["reason"]))
        if tech == "wind":
            return ("For a wind project, this location scores %s/100 (%s). %s "
                    "Consider reviewing the readiness checklist before going further."
                    % (wind["score"], wind["rating"].lower(), wind["reason"]))
        difference = solar["score"] - wind["score"]
        if abs(difference) < 5:
            lead = ("Solar and wind appear similarly suited at this location, "
                    "so other factors (cost, space, equipment) may decide it.")
        elif difference > 0:
            lead = ("This location appears better suited for solar than wind, "
                    "because solar conditions are stronger.")
        else:
            lead = ("This location appears better suited for wind than solar, "
                    "because wind conditions are stronger.")
        return ("%s Solar scores %s/100 (%s) and wind scores %s/100 (%s)."
                % (lead, solar["score"], solar["rating"].lower(),
                   wind["score"], wind["rating"].lower()))

    def _build_checklist(self):
        return [
            "Confirm annual electricity usage from utility bills",
            "Confirm proposed system size with a qualified installer",
            "Review utility interconnection requirements",
            "Confirm equipment and safety requirements",
            "Confirm site details such as roof, land, shading, or turbine placement",
            "Understand that this result is only a pre-application estimate",
        ]
