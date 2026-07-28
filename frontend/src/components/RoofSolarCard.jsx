import { motion } from 'framer-motion'

function StatTile({ value, label }) {
  return (
    <div className="roof-stat">
      <div className="roof-stat-value">{value}</div>
      <div className="roof-stat-label">{label}</div>
    </div>
  )
}

export default function RoofSolarCard({ roofSolarPotential: r, fadeUp }) {
  if (!r) return null

  // A deployment/config state, not something the user can act on — stay quiet.
  if (!r.available && r.reason === 'not_configured') return null

  if (!r.available) {
    return (
      <motion.div className="card roof-unavailable" {...fadeUp}>
        <p className="section-label">Roof & Solar Potential</p>
        <p className="roof-unavailable-note">
          {r.message || "Roof-level detail isn't available for this address."}
        </p>
      </motion.div>
    )
  }

  const { matched_config: cfg, comparison: cmp } = r
  const offsetPositive = cmp.offset_pct != null && cmp.offset_pct >= 100

  return (
    <motion.div className="card" {...fadeUp}>
      <p className="section-label">Roof & Solar Potential</p>
      <p className="roof-source-note">
        Based on Google aerial imagery{r.imagery_date ? ` from ${r.imagery_date}` : ''}
        {cfg.roof_capacity_exceeded ? ' — this roof may not fit your full requested system size.' : ''}
      </p>

      <div className="roof-stats-grid">
        <StatTile value={`${cfg.panels_count} panels`} label={`~${cfg.matched_system_size_kw} kW matched`} />
        <StatTile
          value={`${Math.round(cfg.estimated_annual_production_kwh).toLocaleString()} kWh`}
          label="Est. annual production"
        />
        {r.max_sunshine_hours_per_year != null && (
          <StatTile value={Math.round(r.max_sunshine_hours_per_year).toLocaleString()} label="Sunshine hrs/yr (max roof)" />
        )}
        {r.whole_roof_area_m2 != null && (
          <StatTile value={`${Math.round(r.whole_roof_area_m2)} m²`} label="Usable roof area" />
        )}
      </div>

      <div className={`offset-badge ${offsetPositive ? 'offset-positive' : 'offset-negative'}`}>
        {cmp.offset_pct != null ? `${cmp.offset_pct}% of your annual usage` : 'Offset unknown'}
        {cmp.surplus_kwh != null && (
          <span className="offset-detail">
            {cmp.surplus_kwh >= 0
              ? ` (+${Math.round(cmp.surplus_kwh).toLocaleString()} kWh surplus)`
              : ` (${Math.round(cmp.surplus_kwh).toLocaleString()} kWh short)`}
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
    </motion.div>
  )
}
