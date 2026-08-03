import { motion } from 'framer-motion'

function Skyline() {
  return (
    <div className="bg-skyline">
      <svg viewBox="0 0 1200 92" preserveAspectRatio="none">
        <rect x="0" y="78" width="1200" height="14" fill="rgba(139,163,109,0.16)" />
        <rect x="0" y="77" width="1200" height="1.5" fill="rgba(139,163,109,0.30)" />

        <rect x="10" y="38" width="70" height="40" fill="rgba(23,30,46,0.045)" />
        <rect x="100" y="52" width="50" height="26" fill="rgba(23,30,46,0.045)" />

        <rect x="168" y="48" width="56" height="30" fill="rgba(23,30,46,0.05)" />
        <polygon points="160,48 232,48 196,22" fill="rgba(23,30,46,0.07)" />
        <rect x="193" y="58" width="6" height="6" fill="rgba(200,121,31,0.32)" />

        <rect x="232" y="56" width="46" height="22" fill="rgba(23,30,46,0.05)" />
        <polygon points="226,56 284,56 255,34" fill="rgba(23,30,46,0.07)" />

        <rect x="294" y="58" width="44" height="20" fill="rgba(23,30,46,0.05)" />
        <polygon points="290,58 342,58 316,24" fill="rgba(23,30,46,0.07)" />

        <rect x="350" y="42" width="65" height="36" fill="rgba(23,30,46,0.045)" />
        <rect x="460" y="54" width="55" height="24" fill="rgba(23,30,46,0.04)" />
        <rect x="545" y="32" width="80" height="46" fill="rgba(23,30,46,0.05)" />
        <rect x="660" y="58" width="45" height="20" fill="rgba(23,30,46,0.04)" />
        <rect x="740" y="40" width="70" height="38" fill="rgba(23,30,46,0.045)" />

        <rect x="830" y="58" width="54" height="20" fill="rgba(23,30,46,0.04)" />
        <polygon points="824,58 890,58 857,44" fill="rgba(23,30,46,0.06)" />
        <rect x="853" y="64" width="6" height="6" fill="rgba(200,121,31,0.32)" />

        <rect x="895" y="28" width="95" height="50" fill="rgba(23,30,46,0.05)" />
        <rect x="1000" y="48" width="60" height="30" fill="rgba(23,30,46,0.045)" />

        <rect x="1145" y="54" width="60" height="24" fill="rgba(23,30,46,0.05)" />
        <polygon points="1137,54 1213,54 1175,26" fill="rgba(23,30,46,0.07)" />
        <rect x="1170" y="63" width="6" height="6" fill="rgba(200,121,31,0.32)" />

        <polygon points="165,44 191,26 195,31 169,49" fill="rgba(31,42,74,0.30)" />
        <polygon points="165,44 179,34 183,39 169,49" fill="rgba(200,121,31,0.20)" />
        <line x1="174" y1="38" x2="178" y2="43" stroke="rgba(245,247,251,0.45)" strokeWidth="1" />
        <line x1="182" y1="32" x2="186" y2="37" stroke="rgba(245,247,251,0.45)" strokeWidth="1" />

        <polygon points="829,56 852,46 854,52 831,62" fill="rgba(31,42,74,0.30)" />
        <line x1="837" y1="53" x2="839" y2="59" stroke="rgba(245,247,251,0.45)" strokeWidth="1" />
        <line x1="844" y1="49" x2="846" y2="55" stroke="rgba(245,247,251,0.45)" strokeWidth="1" />

        <rect x="902" y="22" width="81" height="5" fill="rgba(31,42,74,0.30)" />
        <line x1="922" y1="22" x2="922" y2="27" stroke="rgba(245,247,251,0.45)" strokeWidth="1" />
        <line x1="942" y1="22" x2="942" y2="27" stroke="rgba(245,247,251,0.45)" strokeWidth="1" />
        <line x1="962" y1="22" x2="962" y2="27" stroke="rgba(245,247,251,0.45)" strokeWidth="1" />

        <polygon points="1143,50 1169,30 1173,35 1147,55" fill="rgba(31,42,74,0.30)" />
        <line x1="1152" y1="43" x2="1156" y2="48" stroke="rgba(245,247,251,0.45)" strokeWidth="1" />
        <line x1="1160" y1="37" x2="1164" y2="42" stroke="rgba(245,247,251,0.45)" strokeWidth="1" />

        <rect x="915" y="40" width="6" height="6" fill="rgba(200,121,31,0.32)" />
        <rect x="935" y="40" width="6" height="6" fill="rgba(200,121,31,0.32)" />
        <rect x="955" y="40" width="6" height="6" fill="rgba(200,121,31,0.32)" />
      </svg>
    </div>
  )
}

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
