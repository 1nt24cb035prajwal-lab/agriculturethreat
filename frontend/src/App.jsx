export default function App() {
  const cards = [
    { title: 'Weather Status', value: '31°C', detail: 'Partly cloudy', tone: 'green' },
    { title: 'Crop Health', value: '84%', detail: 'Strong vegetative stage', tone: 'blue' },
    { title: 'Disease Risk', value: 'Medium', detail: 'Leaf blast watch', tone: 'amber' },
    { title: 'Water Requirement', value: '28 L/day', detail: 'Schedule irrigation', tone: 'teal' },
    { title: 'NDVI', value: '0.72', detail: 'Healthy canopy', tone: 'green' },
    { title: 'Expected Yield', value: '6.2 t/acre', detail: '36 days to harvest', tone: 'purple' },
    { title: 'Fertilizer', value: 'Urea + Potash', detail: 'Top dress in 3 days', tone: 'orange' },
    { title: 'Threat Alerts', value: '3 Active', detail: '2 medium, 1 high', tone: 'red' }
  ];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">🌾 Agriculture Threat Fusion</div>
        <nav>
          <button>Dashboard</button>
          <button>Crop Input</button>
          <button>Weather</button>
          <button>Satellite</button>
          <button>Disease AI</button>
          <button>Water & Soil</button>
          <button>Reports</button>
        </nav>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <p className="eyebrow">Smart farming dashboard</p>
            <h1>Welcome, Ananya Gowda</h1>
          </div>
          <button className="primary-btn">Farmer Login</button>
        </header>

        <section className="stats-grid">
          {cards.map((card) => (
            <article key={card.title} className={`stat-card ${card.tone}`}>
              <h3>{card.title}</h3>
              <div className="stat-value">{card.value}</div>
              <p>{card.detail}</p>
            </article>
          ))}
        </section>

        <section className="content-grid">
          <div className="panel">
            <h2>Weather Forecast</h2>
            <div className="chart-bars">
              {[32, 30, 29, 31, 34, 30, 33].map((temp, index) => (
                <div key={index} className="bar-col">
                  <div className="bar" style={{ height: `${temp}%` }}></div>
                  <label>{['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][index]}</label>
                </div>
              ))}
            </div>
          </div>
          <div className="panel">
            <h2>Threat Alerts</h2>
            <ul>
              <li>Leaf blast risk: High</li>
              <li>Water stress: Medium</li>
              <li>Nutrient imbalance: Low</li>
            </ul>
          </div>
        </section>
      </main>
    </div>
  );
}
