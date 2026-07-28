import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import AnswerBubble from './components/AnswerBubble'
import Step from './components/Step'
import Results from './components/Results'

const STEPS = [
  {
    id: 'address',
    question: "Where is your property?",
    hint: "Street address, city, or neighbourhood — anywhere in Canada",
    type: 'text',
    placeholder: 'e.g. 123 Main St, Calgary, AB',
  },
  {
    id: 'annual_usage_kwh',
    question: "How much electricity do you use in a year?",
    hint: "Upload a photo of your Enmax, Atco, or Epcor bill and we'll read it for you",
    type: 'bill-upload',
    unit: 'kWh',
  },
  {
    id: 'system_size_kw',
    question: "What size system are you thinking about?",
    hint: "A typical home solar setup is 5–10 kW",
    type: 'number',
    placeholder: '8',
    unit: 'kW',
  },
  {
    id: 'customer_type',
    question: "What best describes you?",
    type: 'choice',
    choices: [
      { label: 'Residential', value: 'Residential', icon: '🏠' },
      { label: 'Farm',        value: 'Farm',        icon: '🌾' },
      { label: 'Business',    value: 'Business',    icon: '🏢' },
      { label: 'Municipality',value: 'Municipality',icon: '🏛️' },
    ],
  },
]

function getDisplayValue(stepId, value) {
  const step = STEPS.find(s => s.id === stepId)
  if (step?.type === 'choice') {
    const choice = step.choices.find(c => c.value === value)
    return choice ? `${choice.icon} ${choice.label}` : value
  }
  if (step?.unit) return `${value} ${step.unit}`
  return value
}

export default function App() {
  const [answers,     setAnswers]     = useState({})
  const [currentStep, setCurrentStep] = useState(0)
  const [results,     setResults]     = useState(null)
  const [loading,     setLoading]     = useState(false)
  const [error,       setError]       = useState(null)

  const completedSteps = STEPS.slice(0, currentStep)
  const activeStep     = STEPS[currentStep]

  async function handleAnswer(value, meta) {
    const newAnswers = { ...answers, [activeStep.id]: value, ...(meta ? { billMeta: meta } : {}) }
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
            address:                      newAnswers.address,
            annual_usage_kwh:             parseFloat(newAnswers.annual_usage_kwh),
            system_size_kw:               parseFloat(newAnswers.system_size_kw),
            customer_type:                newAnswers.customer_type,
            electricity_charge_incl_gst:  newAnswers.billMeta?.electricity_charge_incl_gst ?? null,
            bill_period_usage_kwh:        newAnswers.billMeta?.bill_period_usage_kwh ?? null,
          }),
        })
        const data = await res.json()
        if (!res.ok) throw new Error(data.detail || 'Something went wrong.')
        setResults(data)
      } catch (e) {
        setError(e.message)
        setCurrentStep(STEPS.length - 1)
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
    <div className="app">
      <motion.header
        className="app-header"
        initial={{ opacity: 0, y: -16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <span className="app-icon">⚡</span>
        <div className="app-title">Microgeneration Readiness Advisor</div>
        <div className="app-subtitle">Alberta solar, simplified</div>
      </motion.header>

      <div className="feed">
        <AnimatePresence>
          {completedSteps.map(step => (
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
            className="card loading-card"
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
          >
            <span className="spin">⚙️</span>
            <span>Pulling real weather data for your location...</span>
          </motion.div>
        )}

        {results && (
          <Results results={results} onReset={handleReset} />
        )}
      </div>
    </div>
  )
}
