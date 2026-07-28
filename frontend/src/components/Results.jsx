import { motion } from 'framer-motion'
import RoofSolarCard from './RoofSolarCard'
import VendorsNextSteps from './VendorsNextSteps'
import ChecklistItem from './ChecklistItem'

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
        <div className="tag-row">
          <span className="classification-tag">{results.classification}</span>
          <span className="classification-tag">
            ~{results.recommended_system_size_kw} kW recommended
            {results.system_size_basis === 'roof_matched' ? ' · roof-matched' : ' · estimated'}
          </span>
        </div>
      </motion.div>

      <RoofSolarCard
        roofSolarPotential={results.roof_solar_potential}
        recommendedSystemSizeKw={results.recommended_system_size_kw}
        fadeUp={fadeUp(0.08)}
      />

      <motion.div className="card" {...fadeUp(0.16)}>
        <p className="section-label">Before you go further</p>
        {results.checklist.map((item, i) => (
          <ChecklistItem key={i} text={item} />
        ))}
      </motion.div>

      <VendorsNextSteps fadeUp={fadeUp(0.24)} />

      <motion.button className="reset-btn" onClick={onReset} {...fadeUp(0.32)}>
        Start over
      </motion.button>
    </div>
  )
}
