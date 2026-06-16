import { useState } from 'react'
import { motion } from 'framer-motion'

export default function Step({ step, onAnswer, error }) {
  const [value, setValue] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    if (!value.trim()) return
    onAnswer(value.trim())
  }

  if (step.type === 'choice') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="rounded-2xl border border-slate-700/60 bg-slate-900/60 backdrop-blur-sm p-5"
      >
        <p className="text-white font-medium mb-1">{step.question}</p>
        {step.hint && <p className="text-slate-500 text-xs mb-4">{step.hint}</p>}
        <div className="flex flex-wrap gap-2 mt-3">
          {step.choices.map((choice) => (
            <button
              key={choice.value}
              onClick={() => onAnswer(choice.value)}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-700 bg-slate-800/80 text-slate-300 text-sm font-medium hover:border-indigo-500 hover:text-white hover:bg-indigo-600/10 transition-all duration-200 cursor-pointer"
            >
              <span>{choice.icon}</span>
              <span>{choice.label}</span>
            </button>
          ))}
        </div>
      </motion.div>
    )
  }

  return (
    <motion.form
      onSubmit={handleSubmit}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="rounded-2xl border border-slate-700/60 bg-slate-900/60 backdrop-blur-sm p-5"
    >
      <p className="text-white font-medium mb-1">{step.question}</p>
      {step.hint && <p className="text-slate-500 text-xs mb-4">{step.hint}</p>}

      <div className="flex gap-2 mt-3">
        <div className="relative flex-1">
          <input
            autoFocus
            type={step.type === 'number' ? 'number' : 'text'}
            placeholder={step.placeholder || 'Type your answer...'}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            min={step.type === 'number' ? 0.1 : undefined}
            step={step.type === 'number' ? 'any' : undefined}
            className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/50 transition-all"
          />
          {step.unit && (
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 text-xs">
              {step.unit}
            </span>
          )}
        </div>
        <button
          type="submit"
          className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors cursor-pointer"
        >
          Next →
        </button>
      </div>

      {error && (
        <p className="mt-3 text-red-400 text-xs">{error}</p>
      )}
    </motion.form>
  )
}
