"""
Core domain logic — same OOP design as the MVP, decoupled from Streamlit.
Solar-only: wind scoring was removed when the product pivoted to solar.
Weather-based suitability scoring was removed in favor of the roof-capacity
verdict in solar.py, which is strictly more concrete (real panel count,
real production estimate, real offset) than a generic weather score.
"""


class InvalidProjectInputError(Exception):
    pass


ALBERTA_YIELD_KWH_PER_KW = 1300   # conservative Alberta-wide fallback yield (kWh/kW/year)
CONSERVATIVE_OFFSET_TARGET = 0.8  # target ~80% offset of usage, not 100% net-zero


def estimate_target_system_size_kw(annual_usage_kwh, yield_kwh_per_kw=ALBERTA_YIELD_KWH_PER_KW,
                                    offset_target=CONSERVATIVE_OFFSET_TARGET):
    """
    Rule-of-thumb system size (kW) to offset ~80% of annual usage, assuming a
    flat kWh/kW/year yield. Used only as a fallback recommendation when
    roof-level data isn't available (solar.py's roof-capacity sizing is
    preferred whenever it is).
    """
    if annual_usage_kwh <= 0:
        raise InvalidProjectInputError("Annual electricity usage must be greater than zero.")
    return round((annual_usage_kwh * offset_target) / yield_kwh_per_kw, 2)


class MicrogenerationProject:
    def __init__(self, location, annual_usage_kwh, system_size_kw):
        self._location = location
        self._annual_usage_kwh = annual_usage_kwh
        self._system_size_kw = system_size_kw
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
        return "%s solar microgeneration concept" % size_word


class ReadinessAdvisor:
    """
    Facade for classification + the readiness checklist. The actual
    production/offset verdict lives in solar.py's roof-capacity report;
    this class no longer needs external data to do its job.
    """
    def __init__(self):
        self._classifier = ProjectClassifier()

    def assess(self, project):
        return {
            "classification": self._classifier.describe(project),
            "size_category":  self._classifier.classify(project),
            "checklist":      self._build_checklist(),
        }

    def _build_checklist(self):
        return [
            "Confirm annual electricity usage from utility bills",
            "Confirm the recommended system size with a qualified installer",
            "Review utility interconnection requirements",
            "Confirm equipment and safety requirements",
            "Confirm site details such as roof orientation and shading",
            "Understand that this result is only a pre-application estimate",
        ]
