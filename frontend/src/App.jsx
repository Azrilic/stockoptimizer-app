import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE = process.env.REACT_APP_API_URL || 'https://stockoptimizer-api.onrender.com';

function App() {
  const [step, setStep] = useState('form'); // 'form' | 'results' | 'thankyou'
  const [loading, setLoading] = useState(false);
  const [uzroci, setUzroci] = useState([]);
  const [results, setResults] = useState(null);
  const THANK_YOU_URL = 'https://e.logiko.hr/aa-1-1243-7836-2383';

  // Form state
  const [ime, setIme] = useState('');
  const [email, setEmail] = useState('');
  const [tvrtka, setTvrtka] = useState('');
  const [scores, setScores] = useState({});

  // Accordion state
  const [expandedCategories, setExpandedCategories] = useState({});

  // Category mapping sa custom nazivima
  const categoryNames = {
    'Nabava': 'Problemi sa dobavljačima i nabavom',
    'Proizvodnja': 'Proizvodne opcije i rizici',
    'Prodaja': 'Prodajne strategije & Zalihe',
    'Tržište': 'Tržišni izazovi',
    'Općenito politika': 'Kontrola zaliha & Upravljanje'
  };

  // Load uzroci on mount
  useEffect(() => {
    fetch(`${API_BASE}/api/uzroci`)
      .then(r => r.json())
      .then(data => {
        setUzroci(data);
        // Initialize scores
        const initialScores = {};
        data.forEach(u => initialScores[u.ID_uzroka] = 0);
        setScores(initialScores);
      })
      .catch(err => console.error('Error loading uzroci:', err));
  }, []);

  // Handle redirect kada se prikaže Thank You stranica
  useEffect(() => {
    if (step === 'thankyou') {
      console.log('[DEBUG] Thank You stranica se prikazala, počinjem countdown...');
      const redirectTimer = setTimeout(() => {
        console.log('[DEBUG] Preusmjeravanja na:', THANK_YOU_URL);
        window.location.href = THANK_YOU_URL;
      }, 3000);

      return () => clearTimeout(redirectTimer);
    }
  }, [step]);

  const handleScoreChange = (uzrokId, value) => {
    setScores(prev => ({
      ...prev,
      [uzrokId]: parseInt(value) || 0
    }));
  };

  const toggleCategory = (category) => {
    setExpandedCategories(prev => ({
      ...prev,
      [category]: !prev[category]
    }));
  };

  // Grupiraj probleme po kategorijama
  const groupedProblems = uzroci.reduce((acc, u) => {
    const category = u.Područje;
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(u);
    return acc;
  }, {});

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!ime || !email) {
      alert('Ime i email su obavezni!');
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/api/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ime, email, tvrtka, scores })
      });

      const data = await response.json();

      if (data.success) {
        console.log('[DEBUG] Form submission uspješan, postavljam step na thankyou');
        setResults(data);
        setStep('thankyou');
      } else {
        alert('Error: ' + (data.error || 'Unknown error'));
      }
    } catch (err) {
      alert('Error submitting form: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      {step === 'form' && (
        <div className="form-container">
          <div className="header">
            <h1>StockOptimizer</h1>
            <h2>Detektiv</h2>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Ime:</label>
              <input
                type="text"
                value={ime}
                onChange={(e) => setIme(e.target.value)}
                placeholder="Unesite Vaše ime"
                required
              />
            </div>

            <div className="form-group">
              <label>Email:</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Unesite Vaš email"
                required
              />
            </div>

            <div className="form-group">
              <label>Tvrtka:</label>
              <input
                type="text"
                value={tvrtka}
                onChange={(e) => setTvrtka(e.target.value)}
                placeholder="Unesite naziv tvrtke"
              />
            </div>

            <div className="form-explanation">
              <h3>Kako funkcionira ovaj upitnik?</h3>
              <p>
                Ocijenite koliko svaki uzrok utječe na nekurentnu/preveliku zalihu (1=minimalno, 5=kritično).
                Upitnik je organiziran po funkcijama - klikni na odjeljak da ga otvoriš.
              </p>
              <div className="score-legend">
                <span className="legend-item"><span className="legend-badge" style={{background: '#28a745'}}></span> 1 = Minimalno</span>
                <span className="legend-item"><span className="legend-badge" style={{background: '#ffc107'}}></span> 2-3 = Umjereno</span>
                <span className="legend-item"><span className="legend-badge" style={{background: '#dc3545'}}></span> 4-5 = Kritično</span>
              </div>
            </div>

            <div className="accordion-list">
              {Object.keys(groupedProblems).map(category => (
                <div key={category} className="accordion-item">
                  <div
                    className="accordion-header"
                    onClick={() => toggleCategory(category)}
                  >
                    <span className="accordion-toggle">
                      {expandedCategories[category] ? '▼' : '▶'}
                    </span>
                    <span className="accordion-title">
                      {categoryNames[category] || category}
                    </span>
                    <span className="accordion-count">
                      ({groupedProblems[category].length})
                    </span>
                  </div>

                  {expandedCategories[category] && (
                    <div className="accordion-content">
                      {groupedProblems[category].map((u, idx) => (
                        <div key={u.ID_uzroka} className="uzrok-item">
                          <label>{idx + 1}. {u.Naziv_uzroka}</label>
                          <div className="slider-container">
                            <input
                              type="range"
                              min="0"
                              max="5"
                              value={scores[u.ID_uzroka] || 0}
                              onChange={(e) => handleScoreChange(u.ID_uzroka, e.target.value)}
                              className="slider"
                            />
                            <span className={`score-badge score-${scores[u.ID_uzroka] || 0}`}>
                              {scores[u.ID_uzroka] || 0}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>

            <button type="submit" disabled={loading} className="submit-btn">
              {loading ? 'Šaljem...' : 'ANALIZIRAJ'}
            </button>
          </form>
        </div>
      )}

      {step === 'results' && results && (
        <div className="results-container">
          <div className="header">
            <h1>Tvoji Top Problemi</h1>
            <button onClick={() => setStep('form')} className="back-btn">← Nazad</button>
          </div>

          <div className="results-list">
            {results.uzroci.slice(0, 1).map((uzrok, idx) => (
              <div key={uzrok.id} className={`result-card result-card-${Math.min(uzrok.score, 5)}`}>
                <div className="result-header">
                  <h3>#{idx + 1} {uzrok.naziv}</h3>
                  <span className={`score-badge score-${uzrok.score}`}>{uzrok.score}</span>
                </div>

                <div className="result-info">
                  <p><strong>Područje:</strong> {uzrok.podrucje}</p>
                  <p><strong>Razina:</strong> {uzrok.razina}</p>
                </div>

                <div className="strategije">
                  <h4>Preporučena strategija za rješenje:</h4>
                  {uzrok.strategije.slice(0, 1).map((strat, i) => (
                    <div key={i} className="strategija">
                      <p><strong>{i + 1}. {strat.naziv}</strong></p>
                      <p>{strat.objasnjenje}</p>
                      <p className="tip"><em>Tip: {strat.tip}</em></p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="cta-box">
            <div className="email-message">
              <p><strong>✉️ Ostale strategije se šalju na Vaš email</strong></p>
              <p>Razumite kako najbolje iskoristiti ove rezultate:</p>
              <a href="https://api.leadconnectorhq.com/widget/booking/Z5TZs90rLSeZxnaP7eAu" target="_blank" rel="noopener noreferrer" className="video-link">
                ▶️ Pogledajte objašnjavajući video
              </a>
            </div>
          </div>
        </div>
      )}

      {step === 'thankyou' && (
        <div className="thankyou-container">
          <div className="thankyou-content">
            <h1>Hvala! 🎉</h1>
            <p>Vaši rezultati su obrađeni!</p>
            <p>Email sa svim strategijama je na putu do vas...</p>
            <div className="spinner"></div>
            <p className="redirect-message">Preusmjeravamo vas na Thank You stranicu...</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
