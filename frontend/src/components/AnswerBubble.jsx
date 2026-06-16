import { motion } from 'framer-motion'

export default function AnswerBubble({ question, answer }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col gap-1"
    >
      <p className="text-xs text-slate-600 px-1">{question}</p>
      <div className="self-end bg-indigo-600/20 border border-indigo-500/30 text-indigo-300 text-sm font-medium px-4 py-2 rounded-2xl rounded-tr-sm backdrop-blur-sm">
        {answer}
      </div>
    </motion.div>
  )
}
