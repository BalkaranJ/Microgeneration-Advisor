import { motion } from 'framer-motion'
import RoofOrientationDiagram from './RoofOrientationDiagram'
import MonthlyBreakdownChart from './MonthlyBreakdownChart'

function StatTile({ value, label }) {
  return (
    <div className="roof-stat">
      <div className="roof-stat-value">{value}</div>
      <div className="roof-stat-label">{label}</div>
    </div>
  )
}

const VERDICT_CLASS = {
  full_coverage: 'full_coverage',
  partial_coverage: 'partial_coverage',
  too_small: 'too_small',
}

export default function RoofSolarCard({ roofSolarPotential: r, recommendedSystemSizeKw, fallbackCostEstimateCad, startDelay = 0 }) {
  if (!r) return null

  const fadeUp = delay => ({
    initial: { opacity: 0, y: 16 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.35, delay },
  })
  const step = 0.06
  const delayAt = i => startDelay + i * step

  if (!r.available) {
    return (
      <motion.div className="card" {...fadeUp(startDelay)}>
        <p className="section-label">Analysis Report</p>
        <p className="roof-unavailable-note">
          {r.message || "Roof-level detail isn't available for this address."}
        </p>
        {recommendedSystemSizeKw != null && (
          <p className="savings-note-text">
            Rough estimate without roof data: ~{recommendedSystemSizeKw} kW, sized to offset about 80% of your
            annual usage. This is a general rule of thumb, not specific to your roof.
            {fallbackCostEstimateCad != null && (
              <> Rough installed cost: ~${Math.round(fallbackCostEstimateCad).toLocaleString()} CAD, before any grants/rebates.</>
            )}
          </p>
        )}
      </motion.div>
    )
  }

  const cmp = r.comparison
  const verdictClass = VERDICT_CLASS[r.verdict] || 'too_small'

  return (
    <>
      <motion.div className="card hero-card" {...fadeUp(delayAt(0))}>
        <div className="verdict-row">
          <span className={`verdict-pill ${verdictClass}`}>{r.verdict_message}</span>
        </div>
        <div className="verdict-num">{r.system_size_kw} kW</div>
        <div className="verdict-sub">
          {r.panels_count} panels
          {cmp.offset_pct != null && (
            <>
              , {cmp.offset_pct}% of annual usage covered
              {cmp.surplus_kwh != null && (
                cmp.surplus_kwh >= 0
                  ? ` (+${Math.round(cmp.surplus_kwh).toLocaleString()} kWh surplus)`
                  : ` (${Math.round(cmp.surplus_kwh).toLocaleString()} kWh short)`
              )}
            </>
          )}
        </div>

        {cmp.estimated_annual_savings_cad != null ? (
          <p className="roof-savings">
            Estimated savings: <strong>${cmp.estimated_annual_savings_cad.toLocaleString()}/yr</strong>
            <span className="savings-note-text">{cmp.savings_note}</span>
          </p>
        ) : (
          <p className="savings-note-text" style={{ marginTop: 12 }}>
            Upload a bill photo with visible charges to estimate $/yr savings.
          </p>
        )}
      </motion.div>

      <motion.div className="card" {...fadeUp(delayAt(1))}>
        <p className="section-label">Roof capacity</p>
        <p className="roof-source-note">
          Based on Google aerial imagery{r.imagery_date ? ` from ${r.imagery_date}` : ''}
        </p>
        <div className="roof-stats-grid">
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
      </motion.div>

      {r.roof_orientation?.length > 0 && (
        <motion.div className="card" {...fadeUp(delayAt(2))}>
          <p className="section-label">Panels by roof side</p>
          <RoofOrientationDiagram orientation={r.roof_orientation} />
          {!r.recommended_meets_target ? (
            <p className="savings-note-text" style={{ marginTop: 12 }}>
              Even using this roof's entire buildable area ({r.max_roof_capacity.panels_count} panels), it can't
              fully offset your usage — the numbers above already reflect the whole roof.
            </p>
          ) : r.max_roof_capacity.panels_count > r.panels_count && (
            <p className="savings-note-text" style={{ marginTop: 12 }}>
              Sized to your usage using this roof's best-facing side(s) first — a real installer typically
              wouldn't build out the whole roof if it isn't needed. This roof could hold up to{' '}
              {r.max_roof_capacity.panels_count} panels (~{r.max_roof_capacity.system_size_kw} kW) if you wanted
              to build out further.
            </p>
          )}
        </motion.div>
      )}

      {r.financials && (
        <motion.div className="card" {...fadeUp(delayAt(3))}>
          <p className="section-label">Estimated cost &amp; payback</p>
          <div className="roof-stats-grid">
            <StatTile
              value={`$${Math.round(r.financials.estimated_installed_cost_cad).toLocaleString()}`}
              label={`Est. installed cost (~$${r.financials.cost_per_watt_cad_assumed}/W)`}
            />
            <StatTile
              value={r.financials.payback_period_years != null ? `${r.financials.payback_period_years} yrs` : '—'}
              label="Payback period"
            />
            <StatTile
              value={
                r.financials.lifetime_net_savings_cad != null
                  ? `$${Math.round(r.financials.lifetime_net_savings_cad).toLocaleString()}`
                  : '—'
              }
              label={`Net savings over ${r.financials.panel_lifespan_years} yrs`}
            />
          </div>
          <p className="savings-note-text" style={{ marginTop: 12 }}>{r.financials.note}</p>
        </motion.div>
      )}

      {r.carbon_offset && (
        <motion.div className="card" {...fadeUp(delayAt(4))}>
          <p className="section-label">Environmental impact</p>
          <div className="roof-stats-grid">
            <StatTile
              value={`${Math.round(r.carbon_offset.annual_co2_offset_kg).toLocaleString()} kg`}
              label="CO₂ offset per year"
            />
            <StatTile
              value={`${r.carbon_offset.lifetime_co2_offset_tonnes.toLocaleString()} t`}
              label={`Over ${r.financials?.panel_lifespan_years ?? 25} yrs`}
            />
          </div>
          <p className="savings-note-text" style={{ marginTop: 12 }}>
            Based on your local grid's carbon intensity ({r.carbon_offset.carbon_offset_factor_kg_per_mwh} kg
            CO₂/MWh), from Google's Solar API.
          </p>
        </motion.div>
      )}

      {r.monthly_breakdown?.length > 0 && (
        <motion.div className="card" {...fadeUp(delayAt(5))}>
          <p className="section-label">Monthly production vs. usage</p>
          <MonthlyBreakdownChart months={r.monthly_breakdown} />
        </motion.div>
      )}

      <motion.div className="card" {...fadeUp(delayAt(6))}>
        <p className="disclaimer-text">{r.disclaimer}</p>
      </motion.div>
    </>
  )
}
