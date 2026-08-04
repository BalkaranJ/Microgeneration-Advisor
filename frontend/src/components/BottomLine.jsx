import { motion } from 'framer-motion'

const TONE_CLASS = {
  good: 'good',
  warn: 'warn',
  bad: 'bad',
  neutral: 'neutral',
}

export default function BottomLine({ bottomLine, fadeUp }) {
  if (!bottomLine) return null

  const { tone, headline, body, action } = bottomLine
  const toneClass = TONE_CLASS[tone] || 'neutral'

  return (
    <motion.div className="card" {...fadeUp}>
      <div className={`bottom-line ${toneClass}`}>
        <p className="bottom-line-eyebrow">Bottom line</p>
        <p className="bottom-line-headline">{headline}</p>
        <p className="bottom-line-body">{body}</p>
        {action.type === 'go' ? (
          <span className="bottom-line-action-go">{action.label} &rarr;</span>
        ) : (
          <span className="bottom-line-action-skip">{action.label}</span>
        )}
      </div>
    </motion.div>
  )
}
