# StockOptimizer – što naručiti ovaj tjedan

Aplikacija iz izvoza iz ERP-a radi u dvije faze. Podaci se ne spremaju.

1. **Analiza:** popis svih artikala (sortiranje, filtri po ABC/XYZ, dobavljaču i tekstu) i tri ABC/XYZ matrice: zalihe,
   prodaja i odstupanje između njih. Mjera: vrijednost (€), količina ili broj artikala; prikaz: apsolutno ili postotak.
   Klik na polje matrice (npr. AX) filtrira popis. Uz to sigurnosna zaliha, točka naručivanja, obrtaj i status.
2. **Narudžba (izvršenje):** količine za naručiti po dobavljaču, CSV spreman za uvoz u ERP.

Gumb "Isprobaj s primjerom" pokreće analizu na izmišljenim podacima, bez učitavanja datoteke.

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

Excel ili CSV. **Obavezno je samo: šifra artikla i 12 uzastopnih stupaca s mjesečnom prodajom (količine).**
Sve ostalo je dodatak koji otključava dodatne rezultate:

| Dodatni stupac | Što otključava | Bez njega |
|---|---|---|
| Trenutna zaliha | količina za naručiti ovaj tjedan | samo sigurnosna zaliha, točka naručivanja i količina po narudžbi |
| Na putu | ne naručuje se dvaput | narudžba ne uzima u obzir već naručeno (upozorenje) |
| Nabavna cijena | pravi EOQ, vrijednosti u € | količina po narudžbi = potražnja za 4 tjedna (parametar) |
| Prodajna cijena | ABC po prometu u € | ABC po nabavnoj vrijednosti, a bez cijena po količini |
| Prosječna zaliha | obrtaj, status, usporedba zaliha i prodaje | koristi se trenutna zaliha, ako je ima |
| Dobavljač | narudžba razdvojena po dobavljaču | jedna zajednička narudžba |
| Lead time (dani) | stvarni rokovi | zadano 21 dan |
| Naziv, MOQ, Pakiranje | čitljivost, zaokruživanje | – |

Mjeseci moraju stajati jedan do drugoga; ako uz njih postoje drugi brojčani stupci koji ih prekidaju ili ih ima više
od 12 uzastopno, aplikacija javlja grešku umjesto da pogađa. Predložak: `/api/predlozak.xlsx`.

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
