"""Rad s lokalnim mapama: najnoviju CSV/Excel datoteku iz ulazne mape pretvara u narudžbu.

Primjer (ručno ili iz Windows Task Schedulera / cron-a):
    python cli.py --ulaz C:\\StockOptimizer\\ulaz --izlaz C:\\StockOptimizer\\izlaz
Izlaz: narudzba.csv (za uvoz u ERP) i stockoptimizer-rezultat.xlsx.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import engine
from engine import GreskaUnosa, Parametri


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ulaz", required=True, help="mapa s izvozom iz ERP-a (.csv ili .xlsx)")
    ap.add_argument("--izlaz", required=True, help="mapa u koju se sprema narudžba")
    d = Parametri()
    for ime in ("razina_a", "razina_b", "razina_c"):
        ap.add_argument(f"--{ime.replace('_', '-')}", type=int, default=getattr(d, ime))
    for ime in ("trosak_narudzbe", "drzanje_postotak", "lead_time_default", "pokrivenost_tjedana", "abc_a", "abc_b", "xyz_x", "xyz_y"):
        ap.add_argument(f"--{ime.replace('_', '-')}", type=float, default=getattr(d, ime))
    a = ap.parse_args(argv)

    ulaz, izlaz = Path(a.ulaz), Path(a.izlaz)
    kandidati = [f for f in ulaz.glob("*") if f.suffix.lower() in (".csv", ".xlsx", ".xlsm", ".xls") and not f.name.startswith("~$")]
    if not kandidati:
        print(f"U mapi {ulaz} nema .csv ni .xlsx datoteke.", file=sys.stderr)
        return 2
    datoteka = max(kandidati, key=lambda f: f.stat().st_mtime)
    p = Parametri(**{k: getattr(a, k) for k in vars(d)})
    try:
        df = engine.ucitaj(datoteka.read_bytes(), datoteka.name)
        pod, upoz = engine.priprema(df)
        rez = engine.izracunaj(pod, p, upoz)
    except GreskaUnosa as e:
        print(f"Greška: {e}", file=sys.stderr)
        return 1

    izlaz.mkdir(parents=True, exist_ok=True)
    oznaka = datetime.now().strftime("%Y-%m-%d")
    csv_put = izlaz / f"narudzba-{oznaka}.csv"
    xlsx_put = izlaz / f"stockoptimizer-rezultat-{oznaka}.xlsx"
    engine.narudzba_csv(rez.artikli).to_csv(csv_put, sep=";", index=False, encoding="utf-8-sig")
    xlsx_put.write_bytes(engine.izvezi_excel(rez, p))
    s = rez.sazetak
    print(f"Ulaz: {datoteka.name} ({s['broj_artikala']} artikala)")
    if s["narudzba_stavki"] is not None:
        print(f"Za naručiti: {s['narudzba_stavki']} stavki, {s['narudzba_vrijednost']:,.2f} EUR")
    for u in rez.upozorenja:
        print("Upozorenje:", u)
    print(f"Spremljeno: {csv_put} i {xlsx_put}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
