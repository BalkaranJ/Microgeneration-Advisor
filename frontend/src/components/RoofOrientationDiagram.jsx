const COMPASS = [
  { code: 'N', label: 'North', bearing: 0 },
  { code: 'NE', label: 'Northeast', bearing: 45 },
  { code: 'E', label: 'East', bearing: 90 },
  { code: 'SE', label: 'Southeast', bearing: 135 },
  { code: 'S', label: 'South', bearing: 180 },
  { code: 'SW', label: 'Southwest', bearing: 225 },
  { code: 'W', label: 'West', bearing: 270 },
  { code: 'NW', label: 'Northwest', bearing: 315 },
]

const CX = 100
const CY = 100
const RADIUS = 82

function point(bearingDeg, radius) {
  const rad = (bearingDeg * Math.PI) / 180
  return [CX + radius * Math.sin(rad), CY - radius * Math.cos(rad)]
}

function wedgePath(bearing) {
  const [x1, y1] = point(bearing - 22.5, RADIUS)
  const [x2, y2] = point(bearing + 22.5, RADIUS)
  return `M${CX},${CY} L${x1},${y1} A${RADIUS},${RADIUS} 0 0 1 ${x2},${y2} Z`
}

export default function RoofOrientationDiagram({ orientation }) {
  if (!orientation?.length) return null

  const byCode = Object.fromEntries(orientation.map(o => [o.direction, o]))
  const maxPanels = Math.max(...orientation.map(o => o.panels_count))

  return (
    <div className="roof-diagram-wrap">
      <svg className="roof-diagram-svg" viewBox="0 0 200 210" width="100%">
        <text x={CX} y="14" textAnchor="middle" fontSize="10" fill="var(--text-muted)">N</text>
        {COMPASS.map(({ code, bearing }) => {
          const entry = byCode[code]
          const opacity = entry ? 0.3 + 0.7 * (entry.panels_count / maxPanels) : 0
          return (
            <path
              key={code}
              d={wedgePath(bearing)}
              fill={entry ? 'var(--gold)' : 'var(--surface-2)'}
              fillOpacity={entry ? opacity : 1}
              stroke="var(--surface)"
              strokeWidth="2"
            >
              <title>
                {entry
                  ? `${code}: ${entry.panels_count} panels, ~${Math.round(entry.estimated_annual_production_kwh).toLocaleString()} kWh/yr`
                  : `${code}: no panels`}
              </title>
            </path>
          )
        })}
        {COMPASS.filter(({ code }) => byCode[code]).map(({ code, bearing }) => {
          const [x, y] = point(bearing, RADIUS * 0.62)
          return (
            <text key={code} x={x} y={y + 4} textAnchor="middle" fontSize="12" fill="#fff">
              {code}
            </text>
          )
        })}
      </svg>

      <div className="roof-diagram-legend">
        {orientation.map(o => (
          <div className="row" key={o.direction}>
            <span className="sw" style={{ opacity: 0.3 + 0.7 * (o.panels_count / maxPanels) }} />
            <span className="dir">{o.direction}</span>
            <span className="detail">
              {o.panels_count} panels &middot; ~{Math.round(o.estimated_annual_production_kwh).toLocaleString()} kWh/yr
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
