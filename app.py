"""
Microgeneration Readiness Advisor - MVP prototype
==================================================

A simple, early-stage decision-support tool that helps non-expert Alberta
users get a rough idea of whether a small solar or wind microgeneration
project seems suitable, BEFORE they start a formal utility interconnection
process.

This prototype does NOT approve projects, replace engineering review, or
talk to a real utility. It uses built-in sample weather data instead of a
live weather API.

How to run:
    pip install -r requirements.txt
    streamlit run app.py

------------------------------------------------------------------------
Object-oriented design used in this file
------------------------------------------------------------------------
- Abstraction      : SuitabilityScorer defines WHAT a scorer must do
                     (calculate_score, generate_reason) without saying HOW.
- Encapsulation    : MicrogenerationProject and WeatherProfile keep their
                     values "private" (leading underscore) and expose them
                     only through getter methods.
- Inheritance      : SolarSuitabilityScorer and WindSuitabilityScorer both
                     inherit from the abstract SuitabilityScorer.
- Polymorphism     : ReadinessAdvisor loops over a list of scorers and calls
                     the SAME methods on each, getting different results.
- Strategy Pattern : The two scorers are interchangeable "strategies" for
                     suitability scoring.
- Facade Pattern   : ReadinessAdvisor gives the UI a single, simple entry
                     point (assess) that hides all the steps behind it.
- Exception handling: InvalidProjectInputError is raised for bad input and
                     caught in the Streamlit UI so the app never crashes.
"""

from abc import ABC, abstractmethod
import streamlit as st


# =====================================================================
# 1. SAMPLE DATA
# =====================================================================
# Built-in sample weather profiles for each Alberta city.
# In a real version these numbers would come from a weather/solar API.
# Each value is a simplified 0-100 style indicator.
ALBERTA_WEATHER_DATA = {
    "Calgary":        {"solar_indicator": 78, "wind_indicator": 55, "cloud_cover": 30, "wind_consistency": 50},
    "Edmonton":       {"solar_indicator": 70, "wind_indicator": 48, "cloud_cover": 38, "wind_consistency": 45},
    "Lethbridge":     {"solar_indicator": 75, "wind_indicator": 80, "cloud_cover": 28, "wind_consistency": 72},
    "Red Deer":       {"solar_indicator": 68, "wind_indicator": 52, "cloud_cover": 40, "wind_consistency": 48},
    "Medicine Hat":   {"solar_indicator": 82, "wind_indicator": 62, "cloud_cover": 25, "wind_consistency": 58},
    "Grande Prairie": {"solar_indicator": 62, "wind_indicator": 58, "cloud_cover": 45, "wind_consistency": 52},
}


# =====================================================================
# 2. CUSTOM EXCEPTION (Exception handling)
# =====================================================================
class InvalidProjectInputError(Exception):
    """Raised when the user enters project details that do not make sense."""
    pass


# =====================================================================
# 3. HELPER FUNCTION - turn a numeric score into a word
# =====================================================================
def rating_label(score):
    """Convert a 0-100 score into Strong / Moderate / Weak."""
    if score >= 70:
        return "Strong"
    elif score >= 50:
        return "Moderate"
    else:
        return "Weak"


# =====================================================================
# 4. INPUT CLASS (Encapsulation + validation)
# =====================================================================
class MicrogenerationProject:
    """
    Stores and validates the user's project details.

    Encapsulation: the values are stored in "private" attributes
    (leading underscore) and read through getter methods, so other parts
    of the program cannot change them by accident.
    """

    def __init__(self, location, technology_type, annual_usage_kwh,
                 system_size_kw, customer_type):
        self._location = location
        self._technology_type = technology_type          # "solar", "wind" or "compare"
        self._annual_usage_kwh = annual_usage_kwh
        self._system_size_kw = system_size_kw
        self._customer_type = customer_type
        self.validate_inputs()                            # check the data right away

    def validate_inputs(self):
        """Raise InvalidProjectInputError if any input is invalid."""
        if not self._location:
            raise InvalidProjectInputError("Location is required.")
        if self._location not in ALBERTA_WEATHER_DATA:
            raise InvalidProjectInputError(
                "No sample weather data is available for '%s'." % self._location)
        if self._annual_usage_kwh <= 0:
            raise InvalidProjectInputError("Annual electricity usage must be greater than zero.")
        if self._system_size_kw <= 0:
            raise InvalidProjectInputError("Proposed system size must be greater than zero.")

    # --- getters (controlled access to the private values) ---
    def get_location(self):
        return self._location

    def get_technology_type(self):
        return self._technology_type

    def get_annual_usage(self):
        return self._annual_usage_kwh

    def get_system_size(self):
        return self._system_size_kw

    def get_customer_type(self):
        return self._customer_type


# =====================================================================
# 5. WEATHER DATA CLASS (Encapsulation)
# =====================================================================
class WeatherProfile:
    """Stores the weather indicators used to score a location."""

    def __init__(self, location, solar_indicator, wind_indicator,
                 cloud_cover, wind_consistency):
        self._location = location
        self._solar_indicator = solar_indicator
        self._wind_indicator = wind_indicator
        self._cloud_cover = cloud_cover
        self._wind_consistency = wind_consistency

    def get_solar_indicator(self):
        return self._solar_indicator

    def get_wind_indicator(self):
        return self._wind_indicator

    def get_cloud_cover(self):
        return self._cloud_cover

    def get_wind_consistency(self):
        return self._wind_consistency


# =====================================================================
# 6. ABSTRACT SCORER (Abstraction + base of the Strategy Pattern)
# =====================================================================
class SuitabilityScorer(ABC):
    """
    Abstract base class. It defines the "shape" every scorer must have
    but does not say how the score is calculated. Each concrete scorer
    (solar, wind) is one interchangeable Strategy.
    """

    @abstractmethod
    def calculate_score(self, weather_profile):
        """Return a 0-100 suitability score for the given weather."""
        pass

    @abstractmethod
    def generate_reason(self, score):
        """Return a short plain-language explanation for the score."""
        pass

    @staticmethod
    def _clamp(value):
        """Keep any score inside the 0 to 100 range."""
        return max(0, min(100, value))


# =====================================================================
# 7. SOLAR SCORER (Inheritance + concrete Strategy)
# =====================================================================
class SolarSuitabilityScorer(SuitabilityScorer):
    """Scores solar suitability using sunlight minus a cloud penalty."""

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
        else:
            return "Solar conditions appear weak for this location."


# =====================================================================
# 8. WIND SCORER (Inheritance + concrete Strategy)
# =====================================================================
class WindSuitabilityScorer(SuitabilityScorer):
    """Scores wind suitability using wind speed and wind consistency."""

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
        else:
            return "Wind conditions appear weak for this location."


# =====================================================================
# 9. PROJECT CLASSIFIER
# =====================================================================
class ProjectClassifier:
    """Classifies a project by its proposed system size (in kW)."""

    def classify(self, project):
        """Return a short size category for the project."""
        size = project.get_system_size()
        if size <= 10:
            return "Small microgeneration concept"
        elif size <= 150:
            return "Medium microgeneration concept"
        else:
            return "Large or out-of-scope concept requiring deeper review"

    def describe(self, project):
        """Return a fuller label, e.g. 'Small residential solar concept'."""
        category = self.classify(project)
        # Large / out-of-scope keeps its own wording.
        if category.startswith("Large"):
            return category

        size_word = category.split()[0]                  # "Small" or "Medium"
        customer = project.get_customer_type().lower()
        tech_words = {
            "solar": "solar",
            "wind": "wind",
            "compare": "solar and wind",
        }
        tech = tech_words.get(project.get_technology_type(), "")
        return "%s %s %s microgeneration concept" % (size_word, customer, tech)


# =====================================================================
# 10. FACADE CLASS (Facade Pattern + Polymorphism)
# =====================================================================
class ReadinessAdvisor:
    """
    The Facade. The user interface only ever calls assess().
    Behind that single method, this class:
       1. loads the weather profile,
       2. runs both scoring strategies (polymorphism),
       3. classifies the project,
       4. builds a recommendation,
       5. builds a readiness checklist.
    """

    def __init__(self):
        # The two interchangeable strategies, stored by name.
        self._scorers = {
            "solar": SolarSuitabilityScorer(),
            "wind": WindSuitabilityScorer(),
        }
        self._classifier = ProjectClassifier()

    def assess(self, project):
        """Run the full assessment and return a result dictionary."""
        weather = self._load_weather(project.get_location())

        # --- Polymorphism: same two method calls on different objects ---
        scores = {}
        for name, scorer in self._scorers.items():
            value = scorer.calculate_score(weather)
            scores[name] = {
                "score": round(value, 1),
                "rating": rating_label(value),
                "reason": scorer.generate_reason(value),
            }

        return {
            "classification": self._classifier.describe(project),
            "size_category": self._classifier.classify(project),
            "solar": scores["solar"],
            "wind": scores["wind"],
            "recommendation": self._build_recommendation(project, scores),
            "checklist": self._build_checklist(),
        }

    # ----- private helper steps hidden behind the facade -----
    def _load_weather(self, location):
        data = ALBERTA_WEATHER_DATA[location]
        return WeatherProfile(location, **data)

    def _build_recommendation(self, project, scores):
        tech = project.get_technology_type()
        solar = scores["solar"]
        wind = scores["wind"]

        if tech == "solar":
            return ("For a solar project, this location scores %s/100 (%s). %s "
                    "Consider reviewing the readiness checklist before going further."
                    % (solar["score"], solar["rating"].lower(), solar["reason"]))

        if tech == "wind":
            return ("For a wind project, this location scores %s/100 (%s). %s "
                    "Consider reviewing the readiness checklist before going further."
                    % (wind["score"], wind["rating"].lower(), wind["reason"]))

        # tech == "compare"
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


# =====================================================================
# 11. STREAMLIT USER INTERFACE
# =====================================================================
def main():
    st.set_page_config(page_title="Microgeneration Readiness Advisor", page_icon="\u26a1")

    st.title("\u26a1 Microgeneration Readiness Advisor")
    st.caption(
        "An early-stage decision-support tool for Alberta solar and wind projects. "
        "This is only a pre-application estimate, not an approval or engineering review."
    )

    # ---------------- Input section ----------------
    st.header("1. Enter your project details")

    col1, col2 = st.columns(2)
    with col1:
        location = st.selectbox(
            "Location",
            list(ALBERTA_WEATHER_DATA.keys()),
        )
        technology_label = st.selectbox(
            "Technology type",
            ["Solar", "Wind", "Compare Both"],
        )
        customer_type = st.selectbox(
            "Customer type",
            ["Residential", "Farm", "Business", "Municipality"],
        )
    with col2:
        annual_usage = st.number_input(
            "Annual electricity usage (kWh)",
            value=9000, step=100,
            help="Try entering 0 to see input validation in action.",
        )
        system_size = st.number_input(
            "Proposed system size (kW)",
            value=8.0, step=0.5,
        )

    # Map the friendly labels to the internal codes used by the classes.
    technology_map = {"Solar": "solar", "Wind": "wind", "Compare Both": "compare"}
    technology_type = technology_map[technology_label]

    run = st.button("Run assessment", type="primary")

    # ---------------- Results section ----------------
    if run:
        try:
            # Build and validate the project (may raise our custom exception).
            project = MicrogenerationProject(
                location=location,
                technology_type=technology_type,
                annual_usage_kwh=annual_usage,
                system_size_kw=system_size,
                customer_type=customer_type,
            )

            # One simple call to the facade does all the work.
            advisor = ReadinessAdvisor()
            result = advisor.assess(project)

            # --- Project classification ---
            st.header("2. Project classification")
            st.success(result["classification"])
            st.write("Size category: **%s**" % result["size_category"])

            # --- Suitability scores ---
            st.header("3. Suitability scores")
            score_col1, score_col2 = st.columns(2)
            with score_col1:
                st.metric("Solar score", "%s / 100" % result["solar"]["score"],
                          result["solar"]["rating"])
                st.caption(result["solar"]["reason"])
            with score_col2:
                st.metric("Wind score", "%s / 100" % result["wind"]["score"],
                          result["wind"]["rating"])
                st.caption(result["wind"]["reason"])

            # --- Recommendation ---
            st.header("4. Recommendation")
            st.info(result["recommendation"])

            # --- Readiness checklist ---
            st.header("5. Readiness checklist")
            st.write("Work through these before any formal application:")
            for item in result["checklist"]:
                st.checkbox(item, value=False)

        except InvalidProjectInputError as error:
            # Exception handling: show a friendly message instead of crashing.
            st.error("Input error: %s" % error)


if __name__ == "__main__":
    main()
