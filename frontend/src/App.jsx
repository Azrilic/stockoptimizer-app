import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE = process.env.REACT_APP_API_URL || 'https://stockoptimizer-api.onrender.com';

function App() {
  const [step, setStep] = useState('form'); // 'form' | 'results'
  const [loading, setLoading] = useState(false);
  const [uzroci, setUzroci] = useState([]);
  const [results, setResults] = useState(null);

  // Form state
  const [ime, setIme] = useState('');
  const [email, setEmail] = useState('');
  const [tvrtka, setTvrtka] = useState('');
  const [scores, setScores] = useState({});

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

  const handleScoreChange = (uzrokId, value) => {
    setScores(prev => ({
      ...prev,
      [uzrokId]: parseInt(value) || 0
    }));
  };

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
        setResults(data);
        setStep('results');
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

            <h3>Ocijeni probleme (1-5, 0 = nema problema)</h3>

            <div className="uzroci-list">
              {uzroci.map((u, idx) => (
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
            {results.uzroci.map((uzrok, idx) => (
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
                  <h4>Strategije za rješenje:</h4>
                  {uzrok.strategije.map((strat, i) => (
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
            <p>Rezultati su poslani na Vaš email. Provjerite inbox!</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
