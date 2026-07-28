import { motion } from 'framer-motion'
import ChecklistItem from './ChecklistItem'

function StatTile({ value, label }) {
  return (
    <div className="roof-stat">
      <div className="roof-stat-value">{value}</div>
      <div className="roof-stat-label">{label}</div>
    </div>
  )
}

const VERDICT_CLASS = {
  full_coverage: 'offset-positive',
  partial_coverage: 'offset-negative',
  too_small: 'offset-toosmall',
}

export default function RoofSolarCard({ roofSolarPotential: r, recommendedSystemSizeKw, fadeUp }) {
  if (!r) return null

  if (!r.available) {
    return (
      <motion.div className="card roof-unavailable" {...fadeUp}>
        <p className="section-label">Roof & Solar Potential</p>
        <p className="roof-unavailable-note">
          {r.message || "Roof-level detail isn't available for this address."}
        </p>
        {recommendedSystemSizeKw != null && (
          <p className="savings-note-text">
            Rough estimate without roof data: ~{recommendedSystemSizeKw} kW, sized to offset about 80% of your
            annual usage. This is a general rule of thumb, not specific to your roof.
          </p>
        )}
      </motion.div>
    )
  }

  const cmp = r.comparison
  const verdictClass = VERDICT_CLASS[r.verdict] || 'offset-toosmall'

  return (
    <motion.div className="card" {...fadeUp}>
      <p className="section-label">Roof & Solar Potential</p>
      <p className="roof-source-note">
        Based on Google aerial imagery{r.imagery_date ? ` from ${r.imagery_date}` : ''}
      </p>

      <div className="roof-stats-grid">
        <StatTile value={`${r.panels_count} panels`} label={`~${r.system_size_kw} kW system`} />
        <StatTile
          value={`${Math.round(r.estimated_annual_production_kwh).toLocaleString()} kWh`}
          label="Est. annual production"
        />
        <StatTile
          value={`${r.panel_watts_assumed}W panel`}
          label={`assumed (vs. Google's ${r.google_panel_capacity_watts}W)`}
        />
        {r.max_sunshine_hours_per_year != null && (
          <StatTile value={Math.round(r.max_sunshine_hours_per_year).toLocaleString()} label="Sunshine hrs/yr (max roof)" />
        )}
        {r.whole_roof_area_m2 != null && (
          <StatTile value={`${Math.round(r.whole_roof_area_m2)} m²`} label="Usable roof area" />
        )}
      </div>

      <div className={`offset-badge ${verdictClass}`}>
        {r.verdict_message}
        {cmp.offset_pct != null && (
          <span className="offset-detail">
            {' '}({cmp.offset_pct}% offset
            {cmp.surplus_kwh != null && (
              cmp.surplus_kwh >= 0
                ? `, +${Math.round(cmp.surplus_kwh).toLocaleString()} kWh surplus`
                : `, ${Math.round(cmp.surplus_kwh).toLocaleString()} kWh short`
            )})
          </span>
        )}
      </div>

      {cmp.estimated_annual_savings_cad != null ? (
        <p className="roof-savings">
          Estimated savings: <strong>${cmp.estimated_annual_savings_cad.toLocaleString()}/yr</strong>
          <span className="savings-note-text">{cmp.savings_note}</span>
        </p>
      ) : (
        <p className="savings-note-text">
          Upload a bill photo with visible charges to estimate $/yr savings.
        </p>
      )}

      <p className="subsection-label">Assumptions</p>
      {r.assumptions.map((text, i) => (
        <ChecklistItem key={i} text={text} />
      ))}

      <p className="disclaimer-text">{r.disclaimer}</p>
    </motion.div>
  )
}
