const BAR_WIDTH = 14
const BAR_GAP = 2       // surface gap between the two bars in a month's group
const GROUP_GAP = 14
const CHART_HEIGHT = 120

function formatMonth(monthStr) {
  const [year, month] = (monthStr || '').split('-')
  if (!year || !month) return monthStr || '—'
  const d = new Date(Number(year), Number(month) - 1, 1)
  return d.toLocaleDateString('en-US', { month: 'short' })
}

function formatMoney(value) {
  return value != null ? `$${value.toFixed(2)}` : '—'
}

function niceMax(max) {
  if (max <= 0) return 1
  const magnitude = Math.pow(10, Math.floor(Math.log10(max)))
  const normalized = max / magnitude
  const step = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10
  return step * magnitude
}

function BarPairChart({ months, seriesA, seriesB, unit, formatValue }) {
  const maxValue = niceMax(Math.max(1, ...months.flatMap(m => [seriesA.value(m) || 0, seriesB.value(m) || 0])))
  const groupWidth = BAR_WIDTH * 2 + BAR_GAP
  const width = months.length * groupWidth + Math.max(0, months.length - 1) * GROUP_GAP
  const scale = v => (v / maxValue) * (CHART_HEIGHT - 20)

  return (
    <div className="monthly-chart-scroll">
      <svg
        className="monthly-chart-svg"
        width={width}
        height={CHART_HEIGHT + 24}
        viewBox={`0 0 ${width} ${CHART_HEIGHT + 24}`}
        role="img"
        aria-label={`Monthly ${unit} comparison: ${seriesA.label} vs ${seriesB.label}`}
      >
        <line
          x1="0" y1={CHART_HEIGHT} x2={width} y2={CHART_HEIGHT}
          className="monthly-chart-baseline"
        />
        {months.map((m, i) => {
          const groupX = i * (groupWidth + GROUP_GAP)
          const aValue = seriesA.value(m)
          const bValue = seriesB.value(m)
          const aHeight = aValue != null ? scale(aValue) : 0
          const bHeight = bValue != null ? scale(bValue) : 0
          return (
            <g key={m.month}>
              {aValue != null && (
                <rect
                  x={groupX} y={CHART_HEIGHT - aHeight}
                  width={BAR_WIDTH} height={Math.max(aHeight, 1)}
                  rx="4" className="monthly-chart-bar-a"
                >
                  <title>{`${formatMonth(m.month)}: ${seriesA.label} ${formatValue(aValue)}`}</title>
                </rect>
              )}
              {bValue != null && (
                <rect
                  x={groupX + BAR_WIDTH + BAR_GAP} y={CHART_HEIGHT - bHeight}
                  width={BAR_WIDTH} height={Math.max(bHeight, 1)}
                  rx="4" className="monthly-chart-bar-b"
                >
                  <title>{`${formatMonth(m.month)}: ${seriesB.label} ${formatValue(bValue)}`}</title>
                </rect>
              )}
              <text x={groupX + (BAR_WIDTH * 2 + BAR_GAP) / 2} y={CHART_HEIGHT + 16} className="monthly-chart-tick">
                {formatMonth(m.month)}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

export default function MonthlyBreakdownChart({ months }) {
  if (!months?.length) return null

  const hasCostData = months.some(m => m.actual_cost_cad != null && m.estimated_production_value_cad != null)

  return (
    <div className="monthly-chart">
      <div className="monthly-chart-legend">
        <span className="legend-item"><span className="legend-swatch legend-swatch-a" />Est. production</span>
        <span className="legend-item"><span className="legend-swatch legend-swatch-b" />Your usage</span>
      </div>
      <BarPairChart
        months={months}
        seriesA={{ label: 'Est. production', value: m => m.estimated_production_kwh }}
        seriesB={{ label: 'Actual usage', value: m => m.actual_usage_kwh }}
        unit="kWh"
        formatValue={v => `${Math.round(v).toLocaleString()} kWh`}
      />

      {hasCostData && (
        <>
          <div className="monthly-chart-legend">
            <span className="legend-item"><span className="legend-swatch legend-swatch-a" />Value of production</span>
            <span className="legend-item"><span className="legend-swatch legend-swatch-b" />Your bill</span>
          </div>
          <BarPairChart
            months={months}
            seriesA={{ label: 'Value of production', value: m => m.estimated_production_value_cad }}
            seriesB={{ label: 'Actual bill', value: m => m.actual_cost_cad }}
            unit="$"
            formatValue={formatMoney}
          />
        </>
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
