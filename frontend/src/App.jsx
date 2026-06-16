import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import AnswerBubble from './components/AnswerBubble'
import Step from './components/Step'
import Results from './components/Results'
import './index.css'

const STEPS = [
  {
    id: 'address',
    question: "Where is your property?",
    hint: "Street address, city, or neighbourhood",
    type: 'text',
  },
  {
    id: 'technology_type',
    question: "What are you thinking about?",
    hint: null,
    type: 'choice',
    choices: [
      { label: 'Solar', value: 'solar', icon: '☀️' },
      { label: 'Wind', value: 'wind', icon: '💨' },
      { label: 'Compare both', value: 'compare', icon: '⚖️' },
    ],
  },
  {
    id: 'annual_usage_kwh',
    question: "How much electricity do you use in a year?",
    hint: "In kWh — check your utility bill, or take a rough guess",
    type: 'number',
    placeholder: '9000',
    unit: 'kWh',
  },
  {
    id: 'system_size_kw',
    question: "What size system are you thinking about?",
    hint: "In kW — not sure? A typical home solar setup is 5–10 kW",
    type: 'number',
    placeholder: '8',
    unit: 'kW',
  },
  {
    id: 'customer_type',
    question: "What best describes you?",
    hint: null,
    type: 'choice',
    choices: [
      { label: 'Residential', value: 'Residential', icon: '🏠' },
      { label: 'Farm', value: 'Farm', icon: '🌾' },
      { label: 'Business', value: 'Business', icon: '🏢' },
      { label: 'Municipality', value: 'Municipality', icon: '🏛️' },
    ],
  },
]

export default function App() {
  const [answers, setAnswers] = useState({})
  const [currentStep, setCurrentStep] = useState(0)
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const completedSteps = STEPS.slice(0, currentStep)
  const activeStep = STEPS[currentStep]

  function getDisplayValue(stepId, value) {
    const step = STEPS.find(s => s.id === stepId)
    if (step?.type === 'choice') {
      const choice = step.choices.find(c => c.value === value)
      return choice ? `${choice.icon} ${choice.label}` : value
    }
    if (step?.unit) return `${value} ${step.unit}`
    return value
  }

  async function handleAnswer(value) {
    const newAnswers = { ...answers, [activeStep.id]: value }
    setAnswers(newAnswers)
    setError(null)

    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1)
    } else {
      setLoading(true)
      try {
        const res = await fetch('http://localhost:8000/assess', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            address: newAnswers.address,
            technology_type: newAnswers.technology_type,
            annual_usage_kwh: parseFloat(newAnswers.annual_usage_kwh),
            system_size_kw: parseFloat(newAnswers.system_size_kw),
            customer_type: newAnswers.customer_type,
          }),
        })
        const data = await res.json()
        if (!res.ok) throw new Error(data.detail || 'Something went wrong.')
        setResults(data)
      } catch (e) {
        setError(e.message)
      } finally {
        setLoading(false)
      }
    }
  }

  function handleReset() {
    setAnswers({})
    setCurrentStep(0)
    setResults(null)
    setError(null)
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 py-16">

      <motion.div
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-12 text-center"
      >
        <div className="text-4xl mb-3">⚡</div>
        <h1 className="text-2xl font-semibold text-white tracking-tight">
          Microgeneration Readiness Advisor
        </h1>
        <p className="text-slate-500 text-sm mt-1">Alberta solar and wind, simplified</p>
      </motion.div>

      <div className="w-full max-w-xl flex flex-col gap-3">

        <AnimatePresence>
          {completedSteps.map((step) => (
            <AnswerBubble
              key={step.id}
              question={step.question}
              answer={getDisplayValue(step.id, answers[step.id])}
            />
          ))}
        </AnimatePresence>

        {!results && !loading && activeStep && (
          <Step
            key={activeStep.id}
            step={activeStep}
            onAnswer={handleAnswer}
            error={error}
          />
        )}

        {loading && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="rounded-2xl border border-slate-700/60 bg-slate-900/60 backdrop-blur-sm p-6 text-center"
          >
            <div className="flex items-center justify-center gap-2 text-slate-400">
              <span className="animate-spin inline-block text-xl">⚙️</span>
              <span className="text-sm">Pulling real weather data for your location...</span>
            </div>
          </motion.div>
        )}

        {results && (
          <Results results={results} onReset={handleReset} />
        )}
      </div>
    </div>
  )
}
