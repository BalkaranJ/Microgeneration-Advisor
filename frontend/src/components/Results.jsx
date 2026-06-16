import { motion } from 'framer-motion'

function ScoreRing({ score, color, label }) {
  const r  = 30
  const cx = 42
  const circumference = 2 * Math.PI * r
  const filled = (score / 100) * circumference

  return (
    <div className="score-ring-wrap">
      <div className="score-ring">
        <svg width="84" height="84" viewBox="0 0 84 84">
          <circle cx={cx} cy={cx} r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="6" />
          <circle
            cx={cx} cy={cx} r={r}
            fill="none"
            stroke={color}
            strokeWidth="6"
            strokeDasharray={`${filled} ${circumference}`}
            strokeLinecap="round"
            transform={`rotate(-90 ${cx} ${cx})`}
          />
        </svg>
        <div className="score-value">{score}</div>
      </div>
      <span className="score-label">{label}</span>
    </div>
  )
}

function ChecklistItem({ text }) {
  return (
    <div className="checklist-item">
      <div className="checklist-circle" />
      <span className="checklist-text">{text}</span>
    </div>
  )
}

const fadeUp = (delay = 0) => ({
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.35, delay },
})

export default function Results({ results, onReset }) {
  return (
    <div className="results">
      <motion.div className="card" {...fadeUp(0)}>
        <p className="location-label">Location confirmed</p>
        <p className="location-name">{results.location}</p>
        <span className="classification-tag">{results.classification}</span>
      </motion.div>

      <motion.div className="card" {...fadeUp(0.08)}>
        <p className="section-label">Suitability scores</p>
        <div className="scores-row">
          <ScoreRing score={results.solar.score} color="#f59e0b" label="Solar" />
          <ScoreRing score={results.wind.score}  color="#38bdf8" label="Wind"  />
        </div>
        <div className="score-cards">
          <div className="score-card solar">
            <p className="score-card-title">☀️ Solar — {results.solar.rating}</p>
            <p className="score-card-reason">{results.solar.reason}</p>
          </div>
          <div className="score-card wind">
            <p className="score-card-title">💨 Wind — {results.wind.rating}</p>
            <p className="score-card-reason">{results.wind.reason}</p>
          </div>
        </div>
      </motion.div>

      <motion.div className="card recommendation-card" {...fadeUp(0.16)}>
        <p className="recommendation-label">Recommendation</p>
        <p className="recommendation-text">{results.recommendation}</p>
      </motion.div>

      <motion.div className="card" {...fadeUp(0.24)}>
        <p className="section-label">Before you go further</p>
        {results.checklist.map((item, i) => (
          <ChecklistItem key={i} text={item} />
        ))}
      </motion.div>

      <motion.button className="reset-btn" onClick={onReset} {...fadeUp(0.3)}>
        Start over
      </motion.button>
    </div>
  )
}
