import { motion } from 'framer-motion'
import Skyline from './Skyline'

export default function Landing({ onStart }) {
  return (
    <>
      <div className="bg-sun" />
      <Skyline />

      <div className="landing">
        <div className="landing-brand">
          <span className="landing-brand-mark" />
          <span className="landing-brand-word">Solar<span>Fit</span></span>
        </div>

        <motion.div
          className="hero"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <h1>Know if solar fits your roof, <em>before</em> you spend a dollar.</h1>
          <p>
            Enter your address and a photo of your electricity bill. SolarFit pulls real
            satellite roof data, real historical weather, and your own usage to give you a
            plain verdict, not a sales pitch.
          </p>
          <div className="hero-cta">
            <button className="cta-btn" onClick={onStart}>Check my roof →</button>
            <span className="cta-note"><b>About a minute.</b> Free. No account, no sales calls.</span>
          </div>
        </motion.div>

        <motion.div
          className="card"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
        >
          <div className="card-eyebrow">How it works</div>
          <div className="how-steps">
            <div className="how-step-row">
              <span className="how-step-num">1</span>
              <div className="how-step-body">
                <h3>Enter your address</h3>
                <p>We confirm the exact spot and check what's actually buildable on your roof.</p>
              </div>
            </div>
            <div className="how-step-row">
              <span className="how-step-num">2</span>
              <div className="how-step-body">
                <h3>Upload a photo of your bill</h3>
                <p>We read your usage straight off it. No typing required.</p>
                <span className="privacy-note">⚠ Read once, then discarded. Never stored.</span>
              </div>
            </div>
            <div className="how-step-row">
              <span className="how-step-num">3</span>
              <div className="how-step-body">
                <h3>Get your verdict</h3>
                <p>System size, cost, payback, CO₂ offset, and what to sort out next.</p>
              </div>
            </div>
          </div>
        </motion.div>

        <motion.div
          className="card"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
        >
          <div className="card-eyebrow">What you'll get</div>
          <p className="preview-caption">Example report, illustrative</p>
          <div className="preview-grid">

            <div className="mini">
              <div className="mini-label">Verdict</div>
              <span className="mini-pill">Full coverage</span>
              <div className="mini-num">6.6 kW</div>
              <div className="mini-sub">15 panels, about 8,200 kWh a year</div>
              <div className="mini-sub detail">Covers 112% of what you use in a year, credit to spare</div>
            </div>

            <div className="mini">
              <div className="mini-label">What you'll save</div>
              <div className="mini-num">$1,340</div>
              <div className="mini-sub">Saved this year with solar</div>
              <div className="bill-compare">
                <div className="bill-row">
                  <span className="bill-tag">Your bill</span>
                  <span className="bill-bar"><i style={{ width: '100%', background: 'var(--text-dim)' }} /></span>
                  <span className="bill-val">$1,340</span>
                </div>
                <div className="bill-row">
                  <span className="bill-tag">With solar</span>
                  <span className="bill-covered">✓ $0, fully covered</span>
                </div>
              </div>
              <div className="mini-sub detail">Only counts power you'd actually use, priced at your own rate from your bill</div>
            </div>

            <div className="mini">
              <div className="mini-label">Month by month</div>
              <div className="mini-sub lead">Peaks in August, dips in December</div>
              <div className="mini-chart">
                <svg viewBox="0 0 220 64" preserveAspectRatio="none">
                  <polyline points="0,50 20,44 40,30 60,18 80,10 100,8 120,10 140,16 160,28 180,40 200,48 220,50"
                    fill="none" stroke="var(--gold)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                  <polyline points="0,40 20,39 40,36 60,34 80,33 100,32 120,33 140,35 160,37 180,39 200,40 220,41"
                    fill="none" stroke="var(--sky)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </div>
              <div className="mini-sub">Production in gold, your usage in blue</div>
              <div className="mini-sub detail">Built from a full year of real daily sunlight data at your address</div>
            </div>

          </div>
        </motion.div>

        <div className="landing-footer">
          <p className="landing-footer-credit">Made by Balkaran Singh Jaswal</p>
        </div>
      </div>
    </>
  )
}
