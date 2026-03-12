import os
import json
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64

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

# Email config
SENDER_EMAIL = os.getenv('SENDER_EMAIL', '')
SENDER_PASSWORD = os.getenv('SENDER_PASSWORD', '')
ANTONIO_EMAIL = 'antonio.zrilic@gmail.com'
EMAIL_ENABLED = bool(SENDER_EMAIL and SENDER_PASSWORD)
WEBINAR_LINK = 'https://api.leadconnectorhq.com/widget/booking/Z5TZs90rLSeZxnaP7eAu'

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

# Pošalji email
def send_email(to_email, subject, html_body):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = to_email

        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())

        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

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

        print(f"[DEBUG] EMAIL_ENABLED: {EMAIL_ENABLED}", flush=True)

        # Build emails if enabled
        if EMAIL_ENABLED:
            print(f"[DEBUG] Gradi email HTML", flush=True)
            user_email_html = build_user_email_html(ime, top_uzroci)
            admin_email_html = build_admin_email_html(ime, email, tvrtka, top_uzroci)
            print(f"[DEBUG] Email HTML građen, počinje slanje", flush=True)

            # Send emails
            send_email(email, f'StockOptimizer Detektiv – Vaši rezultati ({datetime.now().strftime("%d.%m.%Y")})', user_email_html)
            send_email(ANTONIO_EMAIL, f'NOVI LEAD - {ime}', admin_email_html)
            print(f"[DEBUG] Mailovi poslani", flush=True)
            message = 'Rezultati su poslani na email!'
        else:
            print(f"[DEBUG] Email slanje nije dostupno, vraćam rezultate", flush=True)
            message = 'Rezultati su obrađeni (email slanje nije dostupno).'

        print(f"[DEBUG] Vraćam JSON rezultate", flush=True)
        return jsonify({
            'success': True,
            'message': message,
            'uzroci': top_uzroci
        }), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/uzroci', methods=['GET'])
def get_uzroci():
    uzroci_df, _ = get_excel_data()
    uzroci_list = uzroci_df[['ID_uzroka', 'Naziv_uzroka']].to_dict('records')
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
