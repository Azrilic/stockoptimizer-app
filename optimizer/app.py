"""Web aplikacija: učitaj izvoz, dobij količine za narudžbu. Podaci se ne spremaju."""

import io
import json
import os

import numpy as np
import pandas as pd
from flask import Flask, jsonify, request, send_file, send_from_directory

import engine
from engine import GreskaUnosa, Parametri

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 15 * 1024 * 1024

POLJA = {
    "razina_a": int, "razina_b": int, "razina_c": int,
    "trosak_narudzbe": float, "drzanje_postotak": float, "lead_time_default": float,
    "pokrivenost_tjedana": float, "abc_a": float, "abc_b": float, "xyz_x": float, "xyz_y": float,
}


def parametri_iz(src) -> Parametri:
    p = Parametri()
    for k, tip in POLJA.items():
        v = src.get(k)
        if v not in (None, ""):
            try:
                setattr(p, k, tip(str(v).replace(",", ".")))
            except ValueError as e:
                raise GreskaUnosa(f"Parametar '{k}' nije ispravan broj.") from e
    if p.trosak_narudzbe < 0 or p.drzanje_postotak <= 0 or p.lead_time_default <= 0 or p.pokrivenost_tjedana <= 0:
        raise GreskaUnosa("Trošak narudžbe ne smije biti negativan, a držanje, lead time i pokrivenost moraju biti veći od nule.")
    if not (0 < p.abc_a < p.abc_b <= 100):
        raise GreskaUnosa("Granice ABC moraju biti rastuće i najviše 100%.")
    if not (0 < p.xyz_x < p.xyz_y):
        raise GreskaUnosa("Granice XYZ moraju biti rastuće.")
    return p


def pokreni(file_storage, form):
    if form.get("demo") == "1" and not (file_storage and file_storage.filename):
        df = engine.demo_podaci()
    elif not file_storage or not file_storage.filename:
        raise GreskaUnosa("Odaberite datoteku s izvozom ili isprobajte primjer.")
    else:
        df = engine.ucitaj(file_storage.read(), file_storage.filename)
    d, upoz = engine.priprema(df)
    p = parametri_iz(form)
    return engine.izracunaj(d, p, upoz), p


def j(obj):
    """JSON-sigurna kopija (numpy tipovi i NaN postaju obični tipovi / null)."""
    def pretvori(o):
        if isinstance(o, float) and np.isnan(o):
            return None
        return o.item() if hasattr(o, "item") else str(o)
    return json.loads(json.dumps(obj, default=pretvori))


def u_zapise(df: pd.DataFrame):
    return json.loads(df.replace({np.nan: None}).to_json(orient="records", force_ascii=False))


@app.errorhandler(GreskaUnosa)
def greska(e):
    return jsonify({"greska": str(e)}), 400


@app.errorhandler(413)
def prevelika(_):
    return jsonify({"greska": "Datoteka je prevelika (najviše 15 MB)."}), 413


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


def odgovor(rez):
    a = rez.artikli
    imamo_narudzbu = bool(a["narudzba"].notna().any())
    cols = ["sifra", "naziv", "dobavljac", "abc", "xyz", "klasa", "potraznja_god", "promet", "zaliha",
            "vrijednost_zalihe", "obrtaj", "dani_zalihe", "sigurnosna", "tocka_naruc", "eoq", "eoq_izvor",
            "status", "lt_dani", "lt_izvor", "cv"]
    if imamo_narudzbu:
        cols += [c for c in ("trenutna", "na_putu", "narudzba", "vrijednost_narudzbe") if c in a]
    return {
        "sazetak": j(rez.sazetak),
        "upozorenja": rez.upozorenja,
        "pretpostavke": rez.pretpostavke,
        "uskladjenost": u_zapise(rez.uskladjenost),
        "dobavljaci": u_zapise(engine.po_dobavljacu(a)),
        "narudzba": u_zapise(engine.narudzba_csv(a)),
        "ima_narudzbu": imamo_narudzbu,
        "artikli": u_zapise(a[[c for c in cols if c in a]].round(2)),
    }


@app.route("/api/analiziraj", methods=["POST"])
def analiziraj():
    rez, _ = pokreni(request.files.get("datoteka"), request.form)
    return jsonify(odgovor(rez))


@app.route("/api/izvoz.xlsx", methods=["POST"])
def izvoz_excel():
    rez, p = pokreni(request.files.get("datoteka"), request.form)
    return send_file(io.BytesIO(engine.izvezi_excel(rez, p)), as_attachment=True, download_name="stockoptimizer-rezultat.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.route("/api/narudzba.csv", methods=["POST"])
def izvoz_csv():
    rez, _ = pokreni(request.files.get("datoteka"), request.form)
    buf = io.StringIO()
    engine.narudzba_csv(rez.artikli).to_csv(buf, sep=";", index=False)
    return send_file(io.BytesIO(("\ufeff" + buf.getvalue()).encode("utf-8")), as_attachment=True,
                     download_name="narudzba.csv", mimetype="text/csv")


XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@app.route("/api/predlozak.xlsx")
def predlozak():
    return send_file(io.BytesIO(engine.predlozak_excel()), as_attachment=True,
                     download_name="stockoptimizer-predlozak.xlsx", mimetype=XLSX)


@app.route("/api/predlozak.csv")
def predlozak_csv():
    return send_file(io.BytesIO(engine.predlozak_csv()), as_attachment=True,
                     download_name="stockoptimizer-predlozak.csv", mimetype="text/csv")


@app.route("/api/primjer.xlsx")
def primjer():
    return send_file(io.BytesIO(engine.predlozak_excel(s_primjerom=True)), as_attachment=True,
                     download_name="stockoptimizer-primjer.xlsx", mimetype=XLSX)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)), debug=False)
