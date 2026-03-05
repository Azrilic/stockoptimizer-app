# StockOptimizer Detektiv - Full App

Kompletan sistem za prikupljanje podataka i automatsko slanje emaila sa rezultatima.

## 📋 Struktura

```
stockoptimizer-app/
├── backend/
│   ├── app.py (Flask API)
│   ├── requirements.txt
│   ├── render.yaml
│   └── data/
│       └── Stockoptimizer Detektiv.xlsx
├── frontend/
│   ├── App.jsx (React komponenta)
│   ├── App.css (CSS stilovi)
│   ├── package.json
│   └── public/
│       ├── index.html
│       └── index.js
├── vercel.json (Vercel config)
└── README.md
```

## 🚀 Deployment

### BACKEND (Python Flask na Render.com)

1. **Pristupi na https://render.com**
2. **Kreiraj novi Web Service**
3. **Odaberi GitHub repo** ili **dodaj kod direktno**
4. **Postavi konfiguraciju:**
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
   - Python version: 3.9+

5. **Postavi Environment Variables:**
   - `SENDER_EMAIL`: tvoja gmail adresa
   - `SENDER_PASSWORD`: Gmail App Password (vidi dolje)
   - `ANTONIO_EMAIL`: antonio.zrilic@logiko.hr

### FRONTEND (React na Vercel)

1. **Pristupi na https://vercel.com**
2. **Kreiraj novi projekt iz GitHub-a**
3. **Odaberi `frontend/` kao root directory**
4. **Postavi Environment Variable:**
   - `REACT_APP_API_URL`: tvoj Render backend URL
     (npr. `https://stockoptimizer-backend.onrender.com`)

5. **Deploy!**

## 🔐 Gmail Setup (za slanje emaila)

1. Idi na **Google Account → Security**
2. Omogući **"Less secure app access"** ILI koristi **App Password**
3. Za App Password:
   - Idi na myaccount.google.com/apppasswords
   - Odaberi "Mail" i "Windows Computer"
   - Google će ti dati 16-znaknu lozinku
   - To je `SENDER_PASSWORD` što trebam u Render

## 📊 Excel Datoteka

Trebam **Stockoptimizer Detektiv.xlsx** sa sheet-evima:
- `Uzroci_master` (ID_uzroka, Naziv_uzroka, Razina rješavanja, Područje)
- `Strategije_master` (ID_uzroka, Strategija, Objasnjenje, Vrijeme, Tip_rješenja)

## 💻 Lokalni razvoj (prije deploymenta)

### Backend (Python)

```bash
cd backend/
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Kreiraj data/ folder i dodaj Excel datoteku
mkdir data/
# Kopira Stockoptimizer Detektiv.xlsx u backend/data/

# Postavi env varijable
export SENDER_EMAIL="your_email@gmail.com"
export SENDER_PASSWORD="your_app_password"

# Startaj
python app.py
```

### Frontend (React)

```bash
cd frontend/
npm install
export REACT_APP_API_URL="http://localhost:5000"
npm start
```

## 🔗 API Endpoints

- `GET /api/uzroci` - Lista svih uzroka
- `POST /api/submit` - Submit forme sa ocjenama
  - Body: `{ime, email, tvrtka, scores: {U01: 5, U02: 4, ...}}`
  - Vraća: Top 5 uzroka sa strategijama + šalje 2 emaila
- `GET /health` - Health check

## 📧 Email Flow

1. **Klijent popuni formu**
2. **Backend generiše 2 emaila:**
   - Email 1: KLIJENTU sa Top strategijama
   - Email 2: TEBI (antonio.zrilic@logiko.hr) sa listom kontakata
3. **Oba emaila se šalju automatski**

## 🎯 Što se dešava kada klijent klikne "ANALIZIRAJ"?

```
1. Forma se šalje na /api/submit
2. Backend učitava Excel datoteku
3. Filtriraj ocjene >= 4, sortiraj po score
4. Za svaki top uzrok, pronađi sve strategije
5. Generiši HTML email sa svim detaljima
6. Pošalji email klijentu
7. Pošalji email tebi sa kontakt podacima
8. Prikaži rezultate u frontend-u
```

## 🛠️ Troubleshooting

**Problem: "Email not sent"**
- Provjeri da li je SENDER_EMAIL validan Gmail
- Provjeri da li je App Password točan (16 znakova)
- Provjeri network connectivity

**Problem: "Excel file not found"**
- Dodaj `backend/data/Stockoptimizer Detektiv.xlsx`
- Render trebam da uploadujem datoteku ili da je pull-ujem iz GitHub-a

**Problem: CORS error**
- Provjeri da je `flask-cors` instaliran
- Provjeri `REACT_APP_API_URL` u frontend env varijablama

## 📱 Mobile Responsive

App je potpuno responsive:
- ✅ Mobile (320px+)
- ✅ Tablet (768px+)
- ✅ Desktop (1024px+)

## 🎨 Branding

Trebam da prilagodim:
- Barve u `frontend/App.css` (trenutno navy blue #1f4e79)
- Logo/header u `frontend/App.jsx`
- Webinar link u `backend/app.py`

## 📞 Kontakt za Support

- Backend issues: Python/Flask/Gmail
- Frontend issues: React/CSS
- Deployment: Vercel/Render

---

**Verzija:** 1.0.0
**Kreirano:** März 2026
