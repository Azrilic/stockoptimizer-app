import os
import json
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import threading
import requests

app = Flask(__name__)

# Excel datoteka - trebam je u backend/data/
EXCEL_FILE = 'data/Stockoptimizer Detektiv.xlsx'

# Cache Excel data na startu - sprječavamo učitavanje Excel-a na svakom zahtjevu!
_UZROCI_DF = None
_STRATEGIJE_DF = None

def get_excel_data():
    """Učitaj Excel datoteku samo prvi put, zatim koristi cached verziju"""
    global _UZROCI_DF, _STRATEGIJE_DF
    if _UZROCI_DF is None or _STRATEGIJE_DF is None:
        excel_data = pd.read_excel(EXCEL_FILE, sheet_name=None)
        _UZROCI_DF = excel_data['Uzroci_master']
        _STRATEGIJE_DF = excel_data['Strategije_master']
    return _UZROCI_DF, _STRATEGIJE_DF

# GHL API config
GHL_API_KEY = os.getenv('GHL_API_KEY', '')
GHL_LOCATION_ID = os.getenv('GHL_LOCATION_ID', 'E2mJCt83LKm33GZMeHI2')
WEBINAR_LINK = 'https://api.leadconnectorhq.com/widget/booking/Z5TZs90rLSeZxnaP7eAu'

# GHL Contacts API endpoint
GHL_CONTACTS_API = 'https://rest.gohighlevel.com/v1/contacts/'

# Provjeri da li je GHL API konfiguriran
GHL_ENABLED = bool(GHL_API_KEY)
if GHL_ENABLED:
    print("[DEBUG] GHL API je konfiguriran", flush=True)
else:
    print("[DEBUG] UPOZORENJE: GHL_API_KEY nije postavljen!", flush=True)

# Loadaj Excel datoteke
def load_excel_data():
    excel_data = pd.read_excel(EXCEL_FILE, sheet_name=None)
    uzroci_df = excel_data['Uzroci_master']
    strategije_df = excel_data['Strategije_master']
    return uzroci_df, strategije_df

# Mapaj ocjene na strategije
def map_scores_to_strategies(scores_dict, threshold=4):
    uzroci_df, strategije_df = get_excel_data()

    # Kreiraj dict sa ocjenama
    scored_uzroci = []
    for uzrok_id, score in scores_dict.items():
        if score >= threshold:
            uzrok_info = uzroci_df[uzroci_df['ID_uzroka'] == uzrok_id]
            if not uzrok_info.empty:
                scored_uzroci.append({
                    'id': uzrok_id,
                    'naziv': uzrok_info.iloc[0]['Naziv_uzroka'],
                    'razina': uzrok_info.iloc[0]['Razina rješavanja'],
                    'podrucje': uzrok_info.iloc[0]['Područje'],
                    'score': score,
                    'strategije': []
                })

    # Za svaki uzrok, pronađi sve strategije
    for uzrok in scored_uzroci:
        strats = strategije_df[strategije_df['ID_uzroka'] == uzrok['id']]
        for _, strat in strats.iterrows():
            uzrok['strategije'].append({
                'naziv': strat['Strategija'],
                'objasnjenje': strat['Objasnjenje'],
                'vrijeme': strat['Vrijeme'],
                'tip': strat['Tip_rješenja']
            })

    # Sortiraj po score (greatest first), uzmi top 5
    scored_uzroci.sort(key=lambda x: x['score'], reverse=True)
    return scored_uzroci[:5]

# HTML Email za korisnika
def build_user_email_html(ime, top_uzroci):
    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #1f4e79; color: white; padding: 20px; border-radius: 5px; }}
            .webinar-box {{ background: #f4f7fb; border-left: 4px solid #1f4e79; padding: 15px; margin: 20px 0; }}
            .uzrok {{ background: #f9f9f9; border-left: 4px solid #c5504e; padding: 15px; margin: 20px 0; }}
            .uzrok.warning {{ border-left-color: #ffc000; }}
            .uzrok.success {{ border-left-color: #70ad47; }}
            .strategija {{ background: white; padding: 12px; margin: 10px 0; border-left: 3px solid #1f4e79; }}
            .score {{ font-weight: bold; color: #c5504e; font-size: 18px; }}
            .tip {{ color: #666; font-size: 12px; font-style: italic; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Vaše rezultate StockOptimizer Detektiva</h2>
            </div>

            <p>Pozdrav {ime},</p>
            <p>U nastavku su Vaši <strong>prioritetni uzroci</strong> i preporučene strategije prema ocjenama u upitniku.</p>

            <div class="webinar-box">
                <h3>Želite akciju a ne samo preporuke?</h3>
                <p>U srijedu radimo live implementacijsku radionicu gdje konkretno prolazimo kako ove strategije pretvoriti u operativne procese.</p>
                <p><strong>Wednesday, 25.02.2026. u 14:00</strong></p>
                <p><a href="{WEBINAR_LINK}" style="color: #1f4e79; font-weight: bold; text-decoration: none;">Pridružite se radionici na linku</a></p>
            </div>

            <hr>
    """

    for i, uzrok in enumerate(top_uzroci, 1):
        color_class = 'danger' if uzrok['score'] >= 5 else ('warning' if uzrok['score'] >= 4 else 'success')
        html += f"""
        <div class="uzrok {color_class}">
            <h3>#{i} Uzrok: {uzrok['naziv']} <span class="score">({uzrok['score']})</span></h3>
            <p><strong>Područje rješavanja:</strong> {uzrok['podrucje']}</p>
            <p><strong>Razina rješavanja:</strong> {uzrok['razina']}</p>

            <h4>Strategije za rješenje:</h4>
        """

        for j, strat in enumerate(uzrok['strategije'], 1):
            html += f"""
            <div class="strategija">
                <p><strong>{j}. {strat['naziv']}</strong></p>
                <p>{strat['objasnjenje']}</p>
                <p class="tip">Tip rješenja: {strat['tip']}</p>
            </div>
            """

        html += "</div>"

    html += f"""
            <hr>
            <p style="color: #666; font-size: 12px;">Email: {ime}</p>
            <p style="color: #666; font-size: 12px;">Generirano: {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
        </div>
    </body>
    </html>
    """
    return html

# Email za Antonija
def build_admin_email_html(ime, email, tvrtka, top_uzroci):
    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: #1f4e79; color: white; padding: 15px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
            th {{ background: #f9f9f9; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>NOVI LEAD - StockOptimizer Detektiv</h2>
            </div>

            <h3>Kontakt:</h3>
            <table>
                <tr><td><strong>Ime:</strong></td><td>{ime}</td></tr>
                <tr><td><strong>Email:</strong></td><td>{email}</td></tr>
                <tr><td><strong>Tvrtka:</strong></td><td>{tvrtka}</td></tr>
                <tr><td><strong>Vrijeme:</strong></td><td>{datetime.now().strftime('%d.%m.%Y %H:%M')}</td></tr>
            </table>

            <h3>Top uzroci (Score >= 4):</h3>
            <ul>
    """

    for uzrok in top_uzroci:
        html += f"<li><strong>{uzrok['naziv']}</strong> - Score: {uzrok['score']} | Područje: {uzrok['podrucje']}</li>"

    html += """
            </ul>

            <p>Za više detaljasa, pogledaj ulaznu formu ili dashboard.</p>
        </div>
    </body>
    </html>
    """
    return html

# Pošalji kontakt na GHL Contacts API
def send_to_ghl_contacts_api(user_name, user_email, company, top_uzroci):
    try:
        print(f"[DEBUG] GHL API: Kreiram kontakt za {user_email}", flush=True)

        # Pripremi strategije kao string za custom field
        strategije_text = '\n\n'.join([
            f"**{uzrok['naziv']} (Score: {uzrok['score']}/5)**\n" +
            '\n'.join([f"- {strat['naziv']}: {strat['objasnjenje']}" for strat in uzrok['strategije']])
            for uzrok in top_uzroci
        ])

        # Pripremi payload za GHL Contacts API
        payload = {
            'firstName': user_name.split()[0] if user_name else '',
            'lastName': ' '.join(user_name.split()[1:]) if len(user_name.split()) > 1 else '',
            'email': user_email,
            'companyName': company,
            'tags': ['StockOptimizer', 'Detektiv'],
            'customFieldValues': {
                'topUzroci': strategije_text,
                'submitTime': datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            }
        }

        # Pošalji POST na GHL Contacts API
        headers = {
            'Authorization': f'Bearer {GHL_API_KEY}',
            'Content-Type': 'application/json'
        }

        # GHL Location ID trebam dodati u URL
        url = f"{GHL_CONTACTS_API}?locationId={GHL_LOCATION_ID}"
        response = requests.post(url, json=payload, headers=headers, timeout=10)

        if response.status_code in [200, 201, 202]:
            print(f"[DEBUG] GHL API uspješan - Status: {response.status_code}", flush=True)
            print(f"[DEBUG] Odgovor: {response.json()}", flush=True)
            return True
        else:
            print(f"[DEBUG] GHL API greška - Status: {response.status_code}", flush=True)
            print(f"[DEBUG] Odgovor: {response.text}", flush=True)
            return False

    except Exception as e:
        print(f"[DEBUG] GHL API greška: {e}", flush=True)
        return False

# Pošalji podatke na GHL u background threadu (asinkrono) - bez blokade!
def send_to_ghl_async(user_email, user_name, company, top_uzroci):
    """Šalje kontakt na GHL Contacts API u background threadu - NE BLOKIRA response!"""
    def _send():
        try:
            print(f"[DEBUG] GHL thread: Počinje slanje", flush=True)
            send_to_ghl_contacts_api(user_name, user_email, company, top_uzroci)
            print(f"[DEBUG] GHL thread: Gotovo!", flush=True)
        except Exception as e:
            print(f"[DEBUG] GHL thread error: {e}", flush=True)

    thread = threading.Thread(target=_send, daemon=True)
    thread.start()

@app.route('/api/submit', methods=['POST'])
def submit_form():
    print(f"[DEBUG] POST /api/submit primljen - {datetime.now()}", flush=True)
    data = request.json

    ime = data.get('ime', '')
    email = data.get('email', '')
    tvrtka = data.get('tvrtka', '')
    scores = data.get('scores', {})  # {U01: 5, U02: 4, ...}

    if not email or not ime:
        return jsonify({'error': 'Ime i email su obavezni'}), 400

    try:
        # Map scores to strategies
        print(f"[DEBUG] Mapiranje uzroka - početo", flush=True)
        top_uzroci = map_scores_to_strategies(scores, threshold=4)
        print(f"[DEBUG] Mapiranje uzroka - završeno, pronađeno: {len(top_uzroci)} uzroka", flush=True)

        if not top_uzroci:
            return jsonify({'error': 'Nema uzroka sa score >= 4'}), 400

        # Vratiti rezultate PRVO, pa onda slati na GHL API (bez čekanja)
        print(f"[DEBUG] GHL_ENABLED: {GHL_ENABLED}", flush=True)

        # Kreiraj JSON odgovor koji se vraća odmah
        response_json = {
            'success': True,
            'message': 'Rezultati su obrađeni! ✅',
            'uzroci': top_uzroci
        }

        # Pokušaj slati na GHL ALI bez čekanja - ako timeout-uje, ignoriraj
        if GHL_ENABLED:
            try:
                print(f"[DEBUG] Pokreće GHL API thread", flush=True)
                # send_to_ghl_async će slati kontakt na GHL u threadu - NE BLOKIRA!
                send_to_ghl_async(email, ime, tvrtka, top_uzroci)
                print(f"[DEBUG] GHL API thread pokrenut - rezultati se vraćaju odmah!", flush=True)
            except Exception as ghl_error:
                print(f"[DEBUG] GHL greška (ignorirano): {ghl_error}", flush=True)
                # Ne trebam zaustaviti - korisnik već ima rezultate!

        print(f"[DEBUG] Vraćam JSON rezultate korisniku", flush=True)
        return jsonify(response_json), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/uzroci', methods=['GET'])
def get_uzroci():
    uzroci_df, _ = get_excel_data()
    uzroci_list = uzroci_df[['ID_uzroka', 'Naziv_uzroka', 'Područje']].to_dict('records')
    return jsonify(uzroci_list), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'OK'}), 200

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
    return response

if __name__ == '__main__':
    app.run(debug=False, port=5000)
