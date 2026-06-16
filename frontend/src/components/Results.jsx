import { motion } from 'framer-motion'

function ScoreRing({ score, label, color }) {
  const radius = 28
  const circumference = 2 * Math.PI * radius
  const filled = (score / 100) * circumference

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-20 h-20">
        <svg className="w-20 h-20 -rotate-90" viewBox="0 0 72 72">
          <circle cx="36" cy="36" r={radius} fill="none" stroke="#1e293b" strokeWidth="6" />
          <circle
            cx="36" cy="36" r={radius}
            fill="none"
            stroke={color}
            strokeWidth="6"
            strokeDasharray={`${filled} ${circumference}`}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-white font-bold text-sm">{score}</span>
        </div>
      </div>
      <span className="text-slate-400 text-xs font-medium">{label}</span>
    </div>
  )
}

function ChecklistItem({ text }) {
  return (
    <div className="flex items-start gap-2.5 py-2 border-b border-slate-800/80 last:border-0">
      <div className="mt-0.5 w-4 h-4 rounded-full border border-slate-600 flex-shrink-0" />
      <span className="text-slate-400 text-sm">{text}</span>
    </div>
  )
}

export default function Results({ results, onReset }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col gap-4"
    >
      <div className="rounded-2xl border border-slate-700/60 bg-slate-900/60 backdrop-blur-sm p-5">
        <p className="text-xs text-slate-500 mb-1">Location confirmed</p>
        <p className="text-white text-sm font-medium leading-snug">{results.location}</p>
        <p className="text-indigo-400 text-xs mt-1">{results.classification}</p>
      </div>

      <div className="rounded-2xl border border-slate-700/60 bg-slate-900/60 backdrop-blur-sm p-5">
        <p className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-5">
          Suitability scores
        </p>
        <div className="flex justify-around">
          <ScoreRing score={results.solar.score} label="Solar" color="#f59e0b" />
          <ScoreRing score={results.wind.score}  label="Wind"  color="#38bdf8" />
        </div>
        <div className="mt-5 grid grid-cols-2 gap-3">
          <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-3">
            <p className="text-amber-400 text-xs font-semibold mb-1">
              ☀️ Solar — {results.solar.rating}
            </p>
            <p className="text-slate-400 text-xs leading-relaxed">{results.solar.reason}</p>
          </div>
          <div className="bg-sky-500/5 border border-sky-500/20 rounded-xl p-3">
            <p className="text-sky-400 text-xs font-semibold mb-1">
              💨 Wind — {results.wind.rating}
            </p>
            <p className="text-slate-400 text-xs leading-relaxed">{results.wind.reason}</p>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-indigo-500/20 bg-indigo-500/5 backdrop-blur-sm p-5">
        <p className="text-indigo-400 text-xs font-medium uppercase tracking-wider mb-2">
          Recommendation
        </p>
        <p className="text-slate-300 text-sm leading-relaxed">{results.recommendation}</p>
      </div>

      <div className="rounded-2xl border border-slate-700/60 bg-slate-900/60 backdrop-blur-sm p-5">
        <p className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-3">
          Before you go further
        </p>
        {results.checklist.map((item, i) => (
          <ChecklistItem key={i} text={item} />
        ))}
      </div>

      <button
        onClick={onReset}
        className="text-slate-600 hover:text-slate-400 text-sm text-center py-2 transition-colors cursor-pointer"
      >
        Start over
      </button>
    </motion.div>
  )
}
