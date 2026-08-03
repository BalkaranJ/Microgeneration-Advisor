const PLOT_H = 150
const HEADROOM = 16
const X_PAD = 20

function formatMonth(monthStr) {
  const [year, month] = (monthStr || '').split('-')
  if (!year || !month) return monthStr || '—'
  const d = new Date(Number(year), Number(month) - 1, 1)
  return d.toLocaleDateString('en-US', { month: 'short' })
}

function formatMoney(value) {
  return value != null ? `$${value.toFixed(2)}` : '—'
}

function niceStep(rough) {
  if (rough <= 0) return 1
  const magnitude = Math.pow(10, Math.floor(Math.log10(rough)))
  const normalized = rough / magnitude
  const step = normalized < 1.5 ? 1 : normalized < 3.5 ? 2 : normalized < 7.5 ? 5 : 10
  return step * magnitude
}

function LineAreaChart({ months, seriesA, seriesB, formatValue, formatTick }) {
  const rawMax = Math.max(1, ...months.flatMap(m => [seriesA.value(m) || 0, seriesB.value(m) || 0]))
  const step = niceStep(rawMax / 3)
  const top = step * 3
  const width = 400
  const xStep = months.length > 1 ? (width - X_PAD * 2) / (months.length - 1) : 0

  const x = i => X_PAD + i * xStep
  const y = v => PLOT_H - (v / top) * (PLOT_H - HEADROOM)

  function buildSeries(series) {
    const pts = months
      .map((m, i) => ({ i, v: series.value(m) }))
      .filter(p => p.v != null)
    return pts.map(p => ({ x: x(p.i), y: y(p.v), v: p.v, month: months[p.i].month }))
  }

  const ptsA = buildSeries(seriesA)
  const ptsB = buildSeries(seriesB)
  const peak = ptsA.reduce((best, p) => (!best || p.v > best.v ? p : best), null)

  const linePoints = pts => pts.map(p => `${p.x},${p.y}`).join(' ')
  const areaPath = pts => {
    if (!pts.length) return ''
    const line = pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ')
    const last = pts[pts.length - 1]
    const first = pts[0]
    return `${line} L${last.x},${PLOT_H} L${first.x},${PLOT_H} Z`
  }

  const ticks = [0, step, step * 2, step * 3]

  return (
    <div className="chart-block">
      <div className="plot">
        <div className="plot-yaxis">
          {ticks.map(t => (
            <span key={t} style={{ top: `${y(t)}px` }}>{formatTick(t)}</span>
          ))}
        </div>
        <div className="plot-area">
          {ticks.map(t => (
            <div key={t} className={`gridline${t === 0 ? ' baseline' : ''}`} style={{ top: `${y(t)}px` }} />
          ))}
          <svg viewBox={`0 0 ${width} ${PLOT_H}`} width="100%" height={PLOT_H} style={{ position: 'absolute', inset: 0, overflow: 'visible' }}>
            <path d={areaPath(ptsA)} fill="var(--gold)" opacity="0.1" />
            <polyline points={linePoints(ptsA)} fill="none" stroke="var(--gold)" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
            <polyline points={linePoints(ptsB)} fill="none" stroke="var(--sky)" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
            {ptsA.map(p => (
              <circle key={`a-${p.month}`} cx={p.x} cy={p.y} r="4" fill="var(--gold)" stroke="var(--surface)" strokeWidth="2">
                <title>{`${formatMonth(p.month)}: ${seriesA.label} ${formatValue(p.v)}`}</title>
              </circle>
            ))}
            {ptsB.map(p => (
              <circle key={`b-${p.month}`} cx={p.x} cy={p.y} r="4" fill="var(--sky)" stroke="var(--surface)" strokeWidth="2">
                <title>{`${formatMonth(p.month)}: ${seriesB.label} ${formatValue(p.v)}`}</title>
              </circle>
            ))}
            {peak && (
              <text x={peak.x} y={Math.max(9, peak.y - 8)} textAnchor="middle" fontSize="10" fontWeight="700" fill="var(--text)">
                {formatValue(peak.v)}
              </text>
            )}
          </svg>
        </div>
      </div>
      <div className="month-axis">
        {months.map(m => <span key={m.month}>{formatMonth(m.month)}</span>)}
      </div>
      <div className="chart-legend">
        <span className="key"><span className="swatch-line" style={{ background: 'var(--gold)' }} />{seriesA.label}</span>
        <span className="key"><span className="swatch-line" style={{ background: 'var(--sky)' }} />{seriesB.label}</span>
      </div>
    </div>
  )
}

export default function MonthlyBreakdownChart({ months }) {
  if (!months?.length) return null

  const hasCostData = months.some(m => m.actual_cost_cad != null && m.estimated_production_value_cad != null)

  return (
    <div className="monthly-chart">
      <LineAreaChart
        months={months}
        seriesA={{ label: 'Est. production', value: m => m.estimated_production_kwh }}
        seriesB={{ label: 'Your usage', value: m => m.actual_usage_kwh }}
        formatValue={v => `${Math.round(v).toLocaleString()} kWh`}
        formatTick={v => v.toLocaleString()}
      />

      {hasCostData && (
        <LineAreaChart
          months={months}
          seriesA={{ label: 'Value of production', value: m => m.estimated_production_value_cad }}
          seriesB={{ label: 'Your bill', value: m => m.actual_cost_cad }}
          formatValue={formatMoney}
          formatTick={v => `$${v.toLocaleString()}`}
        />
      )}

      <details className="monthly-history">
        <summary>Monthly figures ({months.length} months)</summary>
        <div className="monthly-history-list">
          {months.map(m => (
            <div key={m.month} className="monthly-history-row monthly-history-row-4col">
              <span>{formatMonth(m.month)}</span>
              <span>{Math.round(m.estimated_production_kwh).toLocaleString()} kWh</span>
              <span>{m.actual_usage_kwh != null ? `${m.actual_usage_kwh} kWh` : '—'}</span>
              <span>{formatMoney(m.actual_cost_cad)}</span>
            </div>
          ))}
        </div>
      </details>
    </div>
  )
}
