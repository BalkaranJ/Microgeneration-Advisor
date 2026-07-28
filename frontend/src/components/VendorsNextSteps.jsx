import { motion } from 'framer-motion'
import ChecklistItem from './ChecklistItem'

const NEXT_STEPS = [
  "Get quotes from two or three licensed solar installers in your area.",
  "Ask installers to validate this roof's actual shading, structural capacity, and exact panel layout on-site.",
  "Confirm your utility's net-metering / export-credit terms — savings above only assume self-consumption.",
]

export default function VendorsNextSteps({ fadeUp }) {
  return (
    <motion.div className="card" {...fadeUp}>
      <p className="section-label">Vendors & Next Steps</p>
      <div className="vendors-placeholder">
        <span className="vendors-placeholder-title">Vendor list coming soon</span>
        <span className="vendors-placeholder-note">We're not recommending specific installers yet. In the meantime:</span>
      </div>
      {NEXT_STEPS.map((text, i) => (
        <ChecklistItem key={i} text={text} />
      ))}
    </motion.div>
  )
}
