import { motion } from 'framer-motion'

export default function AnswerBubble({ question, answer }) {
  return (
    <motion.div
      className="bubble-wrap"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.25 }}
    >
      <span className="bubble-label">{question}</span>
      <div className="bubble">{answer}</div>
    </motion.div>
  )
}
