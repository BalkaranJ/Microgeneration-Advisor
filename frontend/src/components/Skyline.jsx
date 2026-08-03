export default function Skyline() {
  return (
    <div className="bg-skyline">
      <svg viewBox="0 0 1200 92" preserveAspectRatio="none">
        {/* ground strip and horizon line */}
        <rect x="0" y="78" width="1200" height="14" fill="rgba(139,163,109,0.16)" />
        <rect x="0" y="77" width="1200" height="1.5" fill="rgba(139,163,109,0.30)" />

        {/* building 1: flat-roof block, far left */}
        <rect x="10" y="38" width="70" height="40" fill="rgba(23,30,46,0.045)" />
        {/* building 2: low flat-roof block */}
        <rect x="100" y="52" width="50" height="26" fill="rgba(23,30,46,0.045)" />

        {/* house 1: gable-roofed house with a lit window */}
        <rect x="168" y="48" width="56" height="30" fill="rgba(23,30,46,0.05)" />
        <polygon points="160,48 232,48 196,22" fill="rgba(23,30,46,0.07)" />
        <rect x="193" y="58" width="6" height="6" fill="rgba(200,121,31,0.32)" />

        {/* house 2: gable-roofed house, no window */}
        <rect x="232" y="56" width="46" height="22" fill="rgba(23,30,46,0.05)" />
        <polygon points="226,56 284,56 255,34" fill="rgba(23,30,46,0.07)" />

        {/* house 3: gable-roofed house, no window */}
        <rect x="294" y="58" width="44" height="20" fill="rgba(23,30,46,0.05)" />
        <polygon points="290,58 342,58 316,24" fill="rgba(23,30,46,0.07)" />

        {/* buildings 3-6: flat-roof blocks filling the mid skyline */}
        <rect x="350" y="42" width="65" height="36" fill="rgba(23,30,46,0.045)" />
        <rect x="460" y="54" width="55" height="24" fill="rgba(23,30,46,0.04)" />
        <rect x="545" y="32" width="80" height="46" fill="rgba(23,30,46,0.05)" />
        <rect x="660" y="58" width="45" height="20" fill="rgba(23,30,46,0.04)" />
        <rect x="740" y="40" width="70" height="38" fill="rgba(23,30,46,0.045)" />

        {/* house 4: gable-roofed house with a lit window */}
        <rect x="830" y="58" width="54" height="20" fill="rgba(23,30,46,0.04)" />
        <polygon points="824,58 890,58 857,44" fill="rgba(23,30,46,0.06)" />
        <rect x="853" y="64" width="6" height="6" fill="rgba(200,121,31,0.32)" />

        {/* building 7: tall flat-roof block with a rooftop ledge/antenna rail (grain-elevator style anchor) */}
        <rect x="895" y="28" width="95" height="50" fill="rgba(23,30,46,0.05)" />
        {/* building 8: flat-roof block */}
        <rect x="1000" y="48" width="60" height="30" fill="rgba(23,30,46,0.045)" />

        {/* house 5: gable-roofed house, far right, with a lit window */}
        <rect x="1145" y="54" width="60" height="24" fill="rgba(23,30,46,0.05)" />
        <polygon points="1137,54 1213,54 1175,26" fill="rgba(23,30,46,0.07)" />
        <rect x="1170" y="63" width="6" height="6" fill="rgba(200,121,31,0.32)" />

        {/* pine tree beside house 1 */}
        <polygon points="165,44 191,26 195,31 169,49" fill="rgba(31,42,74,0.30)" />
        <polygon points="165,44 179,34 183,39 169,49" fill="rgba(200,121,31,0.20)" />
        <line x1="174" y1="38" x2="178" y2="43" stroke="rgba(245,247,251,0.45)" strokeWidth="1" />
        <line x1="182" y1="32" x2="186" y2="37" stroke="rgba(245,247,251,0.45)" strokeWidth="1" />

        {/* pine tree beside house 4 */}
        <polygon points="829,56 852,46 854,52 831,62" fill="rgba(31,42,74,0.30)" />
        <line x1="837" y1="53" x2="839" y2="59" stroke="rgba(245,247,251,0.45)" strokeWidth="1" />
        <line x1="844" y1="49" x2="846" y2="55" stroke="rgba(245,247,251,0.45)" strokeWidth="1" />

        {/* rooftop ledge and lit windows on building 7 */}
        <rect x="902" y="22" width="81" height="5" fill="rgba(31,42,74,0.30)" />
        <line x1="922" y1="22" x2="922" y2="27" stroke="rgba(245,247,251,0.45)" strokeWidth="1" />
        <line x1="942" y1="22" x2="942" y2="27" stroke="rgba(245,247,251,0.45)" strokeWidth="1" />
        <line x1="962" y1="22" x2="962" y2="27" stroke="rgba(245,247,251,0.45)" strokeWidth="1" />
        <rect x="915" y="40" width="6" height="6" fill="rgba(200,121,31,0.32)" />
        <rect x="935" y="40" width="6" height="6" fill="rgba(200,121,31,0.32)" />
        <rect x="955" y="40" width="6" height="6" fill="rgba(200,121,31,0.32)" />

        {/* pine tree beside house 5 */}
        <polygon points="1143,50 1169,30 1173,35 1147,55" fill="rgba(31,42,74,0.30)" />
        <line x1="1152" y1="43" x2="1156" y2="48" stroke="rgba(245,247,251,0.45)" strokeWidth="1" />
        <line x1="1160" y1="37" x2="1164" y2="42" stroke="rgba(245,247,251,0.45)" strokeWidth="1" />
      </svg>
    </div>
  )
}
