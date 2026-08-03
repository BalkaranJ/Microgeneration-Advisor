import { useState } from 'react'
import { motion } from 'framer-motion'
import Landing from './components/Landing'
import Skyline from './components/Skyline'
import Step from './components/Step'
import Results from './components/Results'

const STEPS = [
  {
    id: 'address',
    question: "Where is your property?",
    hint: "Street address, city, or neighbourhood — anywhere in Canada",
    type: 'address-confirm',
    placeholder: 'e.g. 123 Main St, Calgary, AB',
  },
  {
    id: 'annual_usage_kwh',
    question: "How much electricity do you use in a year?",
    hint: "Upload a photo of your Enmax, Atco, or Epcor bill and we'll read it for you",
    type: 'bill-upload',
    unit: 'kWh',
  },
]

export default function App() {
  const [showIntro,   setShowIntro]   = useState(true)
  const [answers,     setAnswers]     = useState({})
  const [currentStep, setCurrentStep] = useState(0)
  const [results,     setResults]     = useState(null)
  const [loading,     setLoading]     = useState(false)
  const [error,       setError]       = useState(null)

  const activeStep = STEPS[currentStep]

  async function handleAnswer(value, meta) {
    const newAnswers = {
      ...answers,
      [activeStep.id]: value,
      ...(meta ? { [`${activeStep.id}_meta`]: meta } : {}),
    }
    setAnswers(newAnswers)
    setError(null)

    if (currentStep < STEPS.length - 1) {
      setCurrentStep(currentStep + 1)
    } else {
      setLoading(true)
      try {
        const addressMeta = newAnswers.address_meta
        const billMeta     = newAnswers.annual_usage_kwh_meta

        const res = await fetch('http://localhost:8000/assess', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            location:                     addressMeta.location,
            lat:                          addressMeta.lat,
            lon:                          addressMeta.lon,
            annual_usage_kwh:             parseFloat(newAnswers.annual_usage_kwh),
            electricity_charge_incl_gst:  billMeta?.electricity_charge_incl_gst ?? null,
            bill_period_usage_kwh:        billMeta?.bill_period_usage_kwh ?? null,
            monthly_usage_history:        billMeta?.monthly_history ?? null,
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

  if (showIntro) {
    return <Landing onStart={() => setShowIntro(false)} />
  }

  return (
    <>
      <Skyline />

      <div className="app">
        <motion.header
          className="app-header"
          initial={{ opacity: 0, y: -16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <span className="app-icon">☀️</span>
          <div className="app-title">SolarFit</div>
          <div className="app-subtitle">Solar, simplified</div>
        </motion.header>

        <div className="feed">
          {!results && !loading && activeStep && (
            <Step
              key={activeStep.id}
              step={activeStep}
              stepIndex={currentStep}
              stepCount={STEPS.length}
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
              <span>Pulling weather data and estimating your ideal system size...</span>
            </motion.div>
          )}

          {results && (
            <Results results={results} onReset={handleReset} />
          )}
        </div>
      </div>
    </>
  )
}
