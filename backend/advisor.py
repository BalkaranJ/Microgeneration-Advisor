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
    Facade for classification + a single verdict-driven "bottom line." This
    app answers "will solar save you money, and is it worth pursuing," not
    "how do I install solar," so this isn't installer-readiness steps. It's
    one headline, one line of reasoning, and one action, built from the same
    roof/verdict data solar.py already computed.
    """
    def __init__(self):
        self._classifier = ProjectClassifier()

    def assess(self, project, roof_solar_potential=None, system_size_basis=None):
        return {
            "classification": self._classifier.describe(project),
            "size_category":  self._classifier.classify(project),
            "bottom_line":    self._build_bottom_line(project, roof_solar_potential, system_size_basis),
        }

    def _build_bottom_line(self, project, roof_solar_potential, system_size_basis):
        usage_kwh = format(project.get_annual_usage(), ",.0f")

        if system_size_basis == "usage_estimate":
            result = {
                "tone": "neutral",
                "headline": "We can't fully verify this yet.",
                "body": (
                    "No roof-specific data was available for this address, so the size and "
                    "cost above are a flat regional average, not tailored to your actual "
                    "roof. Confirm your %s kWh usage figure and get a real quote before "
                    "treating this as decision-ready." % usage_kwh
                ),
                "action": {"type": "go", "label": "Get 2-3 installer quotes"},
            }
        else:
            r = roof_solar_potential or {}
            verdict = r.get("verdict")
            panels = r.get("panels_count")
            offset_pct = (r.get("comparison") or {}).get("offset_pct")
            imagery_clause = "sized from %s imagery, " % r["imagery_date"] if r.get("imagery_date") else ""

            if verdict == "too_small":
                result = {
                    "tone": "bad",
                    "headline": "Skip it, at least for this roof.",
                    "body": (
                        "Even maxing out this roof's %s panels only reaches %s%% of your "
                        "reported %s kWh usage. That's this structure alone, not any other "
                        "roof or ground space on the property." % (panels, offset_pct, usage_kwh)
                    ),
                    "action": {
                        "type": "skip",
                        "label": "Worth another look if usage drops or roof access changes.",
                    },
                }
            else:
                result = {
                    "tone": "good" if verdict == "full_coverage" else "warn",
                    "headline": (
                        "Get quotes. This pencils out."
                        if verdict == "full_coverage"
                        else "Get quotes. This helps, but won't cover everything."
                    ),
                    "body": (
                        "%s panels on this roof, %scover %s%% of your reported %s kWh usage. "
                        "Worth confirming that usage figure and getting the roof itself "
                        "inspected before signing anything." % (panels, imagery_clause, offset_pct, usage_kwh)
                    ),
                    "action": {"type": "go", "label": "Get 2-3 installer quotes"},
                }

        if self._classifier.classify(project).startswith("Large"):
            result["body"] += (
                " A system this size also falls outside typical residential microgeneration "
                "rules and likely needs a different regulatory path."
            )

        return result
