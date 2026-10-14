# StockOptimizer – što naručiti ovaj tjedan

Aplikacija iz izvoza iz ERP-a računa **količinu za narudžbu po dobavljaču**, a uz nju ABC/XYZ analizu,
sigurnosne zalihe, točke naručivanja, EOQ i obrtaj. Podaci se ne spremaju.

## Izračun

| Veličina | Formula |
|---|---|
| ABC | kumulativni godišnji promet (količina × prodajna cijena): A do 80 %, B do 95 %, C ostalo |
| XYZ | koeficijent varijacije 12 mjeseci: X ≤ 0,5, Y ≤ 1,0, Z iznad |
| Sigurnosna zaliha | `z × σD × √(LT/30)` – bez varijabilnosti roka isporuke (donja granica) |
| Točka naručivanja | `D/dan × LT + sigurnosna zaliha` |
| EOQ | `√(2 · D · S / H)`, `H = h × nabavna cijena`; zaokruženo na MOQ i pakiranje |
| Narudžba | ako je (stanje + na putu) ≤ točka naručivanja: višekratnik EOQ-a koji dovodi poziciju iznad točke |
| Obrtaj | godišnja potražnja / prosječna zaliha (nabavna vrijednost prodaje / nabavna vrijednost zalihe) |
| Usklađenost | po 9 polja: udio u zalihama − udio u prodaji; ±2 p.b. spomenuti, ±5 p.b. nalaz; A-polja i zalihe < 80 % prodaje = rizik manjka |

Zadano: razine usluge A 98 % / B 95 % / C 90 %, S = 60 € po narudžbi, h = 20 % godišnje, lead time 21 dan kad ga izvoz nema.

## Ulaz

Excel ili CSV, jedan redak po artiklu. Obavezno: Šifra, Naziv, Dobavljač, Nabavna cijena, Prodajna cijena,
Prosječna zaliha i točno 12 stupaca mjesečne prodaje. Za količinu za narudžbu treba **Trenutna zaliha**,
a preporučeno je i **Na putu**. Opcionalno: Lead time (dani), MOQ, Pakiranje. Predložak: `/api/predlozak.xlsx`.

## Pokretanje

```bash
pip install -r requirements.txt
python app.py                 # web na http://localhost:5001
python -m pytest              # testovi izračuna
```

### Bez ERP integracije: lokalne mape

```bash
python cli.py --ulaz C:\StockOptimizer\ulaz --izlaz C:\StockOptimizer\izlaz
```

Uzima najnoviju datoteku iz ulazne mape i sprema `narudzba-GGGG-MM-DD.csv` (separator `;`, UTF-8, za uvoz u ERP)
i Excel s cijelim rezultatom. Pokreće se ručno ili iz Windows Task Schedulera / cron-a, npr. petkom navečer.
Sve postavke imaju zadane vrijednosti i mogu se promijeniti zastavicama (`--trosak-narudzbe 60`, `--razina-a 98` …).

## Ograničenja

- Status zalihe uspoređuje *prosječnu* zalihu sa sigurnosnom zalihom i EOQ-om; to je procjena, ne trenutno stanje.
- Ako rok isporuke varira, sigurnosne su zalihe podcijenjene; izlaz to uvijek navodi.
- Nema PDF-a ni izravne ERP integracije; izlaz je CSV/Excel.
