import math
import numpy as np
import pandas as pd
import pytest

from engine import Parametri, izracunaj, priprema, GreskaUnosa, z_vrijednost, narudzba_csv


def okvir(redovi, **extra):
    d = []
    for i, (naziv, mjeseci, nab, prod, zal) in enumerate(redovi):
        r = {"Šifra": f"A{i}", "Naziv": naziv, "Dobavljač": "D1", "Nabavna cijena": nab,
             "Prodajna cijena": prod, "Prosječna zaliha": zal}
        for k, v in extra.items():
            r[k] = v[i] if isinstance(v, list) else v
        for m, v in enumerate(mjeseci, 1):
            r[f"mj{m}"] = v
        d.append(r)
    return pd.DataFrame(d)


def sigma_10():
    # mjeseci s uzorkovanim σ točno 10 oko prosjeka 100 nije moguć u cijelim brojevima; koristimo poznati σ
    base = np.array([100 - 10, 100 + 10] * 6, dtype=float)
    return list(base)


def test_sigurnosna_zaliha_jednostavna_formula():
    m = sigma_10()
    df = okvir([("Y", m, 5.0, 8.0, 100)], **{"Lead time": 21})
    d, _ = priprema(df)
    p = Parametri(razina_a=95, razina_b=95, razina_c=95)
    r = izracunaj(d, p)
    sigma = np.std(m, ddof=1)
    ocekivano = 1.65 * sigma * math.sqrt(21 / 30)
    assert r.artikli.loc[0, "sigurnosna"] == pytest.approx(ocekivano)
    # primjer iz primopredaje: σ = 10 → 13,8
    assert 1.65 * 10 * math.sqrt(21 / 30) == pytest.approx(13.8, abs=0.05)


def test_eoq_i_tocka_naruciavanja():
    m = [100] * 12  # D = 1200, σ = 0
    df = okvir([("X", m, 10.0, 15.0, 100)], **{"Lead time": 30})
    d, _ = priprema(df)
    r = izracunaj(d, Parametri())  # S=60, h=20% → H=2
    a = r.artikli.loc[0]
    assert a["eoq_osnovni"] == pytest.approx(math.sqrt(2 * 1200 * 60 / 2))  # ≈ 268,3
    assert a["eoq"] == 269
    assert a["tocka_naruc"] == pytest.approx(100 / 30 * 30)  # σ=0 → samo potražnja u roku


def test_abc_xyz():
    redovi = [("velik", [1000] * 12, 1, 10, 10),
              ("srednji", [100] * 12, 1, 10, 10),
              ("mali", [10] * 12, 1, 10, 10),
              ("nepravilan", [0] * 11 + [200], 1, 10, 10)]
    d, _ = priprema(okvir(redovi))
    r = izracunaj(d, Parametri()).artikli
    assert r.loc[0, "abc"] == "A"
    assert r.loc[0, "xyz"] == "X"
    assert r.loc[3, "xyz"] == "Z"


def test_narudzba_pravilo():
    m = [100] * 12
    df = okvir([("niska", m, 10.0, 15.0, 100), ("puna", m, 10.0, 15.0, 100)],
               **{"Lead time": 30, "Trenutna zaliha": [50, 1000], "Na putu": [0, 0]})
    d, _ = priprema(df)
    a = izracunaj(d, Parametri()).artikli
    assert a.loc[0, "narudzba"] > 0 and a.loc[0, "narudzba"] % a.loc[0, "eoq"] == 0
    assert a.loc[1, "narudzba"] == 0


def test_na_putu_smanjuje_narudzbu():
    m = [100] * 12
    df = okvir([("x", m, 10.0, 15.0, 100)], **{"Lead time": 30, "Trenutna zaliha": 50, "Na putu": 500})
    d, _ = priprema(df)
    assert izracunaj(d, Parametri()).artikli.loc[0, "narudzba"] == 0


def test_moq_i_pakiranje():
    m = [100] * 12
    df = okvir([("x", m, 10.0, 15.0, 100)], **{"Lead time": 30, "Trenutna zaliha": 0, "MOQ": 500, "Pakiranje": 120})
    d, _ = priprema(df)
    e = izracunaj(d, Parametri()).artikli.loc[0, "eoq"]
    assert e == 600  # max(269, 500) zaokruženo na višekratnik 120


def test_total_redak_i_negativne():
    df = okvir([("a", [10] * 12, 1, 2, 5), ("b", [-5] + [10] * 11, 1, 2, 5)])
    df.loc[len(df)] = {**df.iloc[0].to_dict(), "Šifra": "Total", "Naziv": "Total"}
    d, upoz = priprema(df)
    assert len(d) == 2
    assert any("negativnih" in u for u in upoz)
    assert d["m1"].min() >= 0


def test_nedostaju_stupci_i_kriva_broj_mjeseci():
    with pytest.raises(GreskaUnosa):
        priprema(pd.DataFrame({"Šifra": ["a"], "Naziv": ["b"]}))
    df = okvir([("a", [1] * 12, 1, 2, 3)]).drop(columns=["mj12"])
    with pytest.raises(GreskaUnosa):
        priprema(df)


def test_uskladjenost_zbraja_se_na_sto():
    redovi = [(f"a{i}", [10 * (i + 1)] * 12, 1, 5, 20 * (i + 1)) for i in range(20)]
    d, _ = priprema(okvir(redovi))
    r = izracunaj(d, Parametri())
    assert r.uskladjenost["udio_prodaja"].sum() == pytest.approx(100)
    assert r.uskladjenost["udio_zaliha"].sum() == pytest.approx(100)


def test_lead_time_konstantan_upozorenje():
    m = [100] * 12
    df = okvir([("a", m, 1, 2, 3), ("b", m, 1, 2, 3)], **{"Lead time": 21})
    d, _ = priprema(df)
    assert any("isti lead time" in u for u in izracunaj(d, Parametri()).upozorenja)


def test_z_vrijednosti():
    assert z_vrijednost(95) == 1.65 and z_vrijednost(99) == 2.33
    assert z_vrijednost(97) == pytest.approx(1.88, abs=0.01)


def minimalni(redovi):
    d = []
    for i, m in enumerate(redovi):
        r = {"Šifra": f"S{i}"}
        r.update({f"mj{k}": v for k, v in enumerate(m, 1)})
        d.append(r)
    return pd.DataFrame(d)


def test_minimalni_ulaz_samo_sifra_i_12_mjeseci():
    m = [[100, 120, 80, 110, 90, 105, 95, 115, 85, 100, 125, 75], [10] * 12, [0] * 11 + [30]]
    d, _ = priprema(minimalni(m))
    r = izracunaj(d, Parametri())
    a = r.artikli
    assert list(a["abc"]) == ["A", "C", "C"] or set(a["abc"]) <= {"A", "B", "C"}
    assert (a["sigurnosna"] >= 0).all() and a["sigurnosna"].iloc[0] > 0
    assert (a["tocka_naruc"] > 0).all()
    # bez cijene: količina = potražnja za 4 tjedna
    assert a["eoq_izvor"].eq("pokrivenost").all()
    assert a.loc[1, "eoq"] == math.ceil(120 / 52 * 4)
    assert r.sazetak["ima_cijene"] is False and r.sazetak["vrijednost_zaliha"] is None
    assert r.uskladjenost.empty
    assert np.isnan(a["narudzba"]).all()
    assert narudzba_csv(a).empty


def test_samo_trenutna_zaliha_daje_narudzbu_bez_cijena():
    m = [[100] * 12, [100] * 12]
    df = minimalni(m)
    df["Trenutna zaliha"] = [0, 5000]
    d, _ = priprema(df)
    r = izracunaj(d, Parametri())
    n = narudzba_csv(r.artikli)
    assert list(n.columns) == ["dobavljac", "sifra", "naziv", "kolicina"]
    assert list(n["sifra"]) == ["S0"]
    assert n["kolicina"].iloc[0] > 0


def test_suvisni_numericki_stupac_i_ukupno_stupac():
    df = minimalni([[10] * 12, [20] * 12])
    df["Ukupno"] = 120
    df["Grupa"] = [1, 2]
    d, upoz = priprema(df)
    assert any("Grupa" in u for u in upoz)
    assert d["m1"].tolist() == [10, 20] and d["m12"].tolist() == [10, 20]  # 'Ukupno' i 'Grupa' nisu mjeseci


def test_nejasni_mjeseci_su_greska_a_ne_tiho_pomicanje():
    df = minimalni([[10] * 12, [20] * 12])
    df.insert(5, "Grupa", [1, 2])  # usred mjeseci → nijedan niz od 12
    with pytest.raises(GreskaUnosa):
        priprema(df)


def test_manje_od_12_mjeseci_je_greska():
    df = minimalni([[1] * 12]).drop(columns=["mj12"])
    with pytest.raises(GreskaUnosa):
        priprema(df)


def test_csv_s_bomom_i_cp1250():
    from engine import ucitaj, predlozak_csv, STUPCI_PREDLOSKA
    redak = ";".join(["A1"] + [""] * 10 + [str(10 + i) for i in range(12)]) + "\n"
    # špranca iz aplikacije (UTF-8 s BOM-om) s dopisanim retkom
    d, _ = priprema(ucitaj(predlozak_csv() + redak.encode("utf-8"), "x.csv"))
    assert d["sifra"].tolist() == ["A1"] and d["m12"].tolist() == [21]
    # Windows-1250 s hrvatskim slovima i decimalnim zarezom
    tekst = "Šifra;Naziv;Nabavna cijena;" + ";".join(f"M{i}" for i in range(1, 13)) + "\n" + \
        "A1;Čokolada šuma;1,5;" + ";".join(["5"] * 12) + "\n"
    d, _ = priprema(ucitaj(tekst.encode("cp1250"), "izvoz.csv"))
    assert d["naziv"].tolist() == ["Čokolada šuma"] and d["nabavna"].tolist() == [1.5]


def test_prazna_spranca_je_jasna_greska():
    from engine import ucitaj, predlozak_csv
    with pytest.raises(GreskaUnosa, match="nijednog retka"):
        priprema(ucitaj(predlozak_csv(), "p.csv"))


def _puni(redovi):
    """redovi: (mjeseci, nabavna, prodajna, prosj. zaliha)"""
    return okvir([(f"a{i}", m, n, pr, z) for i, (m, n, pr, z) in enumerate(redovi)])


def test_marza_gmroi_i_abc_po_marzi():
    # artikl 0: velik promet, mala marža; artikl 1: manji promet, velika marža
    d, _ = priprema(_puni([([300] * 12, 10.0, 10.5, 300),      # promet 37.800, marža 1.800
                           ([10] * 12, 10.0, 40.0, 10),        # promet 4.800, marža 3.600
                           ([1] * 12, 10.0, 11.0, 5)]))        # promet 132, marža 12
    r = izracunaj(d, Parametri())
    a = r.artikli
    assert a.loc[0, "marza_god"] == pytest.approx(1800)
    assert a.loc[1, "marza_pct"] == pytest.approx(75)
    assert a.loc[0, "gmroi"] == pytest.approx(1800 / (300 * 10))       # 0,6
    assert a.loc[1, "gmroi"] == pytest.approx(3600 / (10 * 10))        # 36
    assert a.loc[0, "abc"] == "A" and a.loc[1, "abc"] == "B"           # po prometu vodi artikl 0
    assert a.loc[1, "abc_marza"] == "A"                                 # po marži vodi artikl 1
    assert r.sazetak["ima_marzu"] is True
    assert r.sazetak["gmroi"] == pytest.approx((1800 + 3600 + 12) / (3000 + 100 + 50))


def test_bez_cijena_nema_marze_ni_gmroi():
    d, _ = priprema(minimalni([[10] * 12]))
    r = izracunaj(d, Parametri())
    assert r.sazetak["ima_marzu"] is False and r.sazetak["gmroi"] is None
    assert r.artikli["abc_marza"].isna().all()
    assert r.sazetak["cashflow"] is None


def test_cashflow_cetiri_kategorije_i_faktori():
    # obrtaj 0,5 -> 'do 1' (30 %), obrtaj 3 -> '2 do 3' (85 %), bez prodaje ulazi u 'do 1' (30 %)
    d, _ = priprema(_puni([([5] * 12, 10.0, 15.0, 120),    # D=60, zaliha 120  -> obrtaj 0,5
                           ([30] * 12, 10.0, 15.0, 120),   # D=360, zaliha 120 -> obrtaj 3
                           ([0] * 12, 10.0, 15.0, 50)]))   # bez prodaje, zaliha 50
    r = izracunaj(d, Parametri())
    a = r.artikli
    assert list(a["cf_pojas"]) == [0, 2, 0]
    assert a.loc[0, "cf_realna"] == pytest.approx(1200 * 0.30)
    assert a.loc[1, "cf_realna"] == pytest.approx(1200 * 0.85)
    assert a.loc[2, "cf_realna"] == pytest.approx(500 * 0.30)
    cf = r.sazetak["cashflow"]
    assert len(cf["redovi"]) == 4 and cf["prag"] == 3          # medijan 1,75 -> prag najmanje 3
    assert [x["pojas"] for x in cf["redovi"]] == ["do 1", "1 do 2", "2 do 3", "preko 3"]
    assert cf["vrijednost"] == pytest.approx(1200 + 1200 + 500)
    assert cf["realna"] == pytest.approx(360 + 1020 + 150)
    assert cf["umanjenje"] == pytest.approx(cf["vrijednost"] - cf["realna"])
    assert cf["mrtva_artikala"] == 1 and cf["mrtva_vrijednost"] == pytest.approx(500)
    r2 = izracunaj(d, Parametri(cf_faktori=(0, 50, 50, 50)))   # vlastiti postoci
    assert r2.sazetak["cashflow"]["realna"] == pytest.approx(0.5 * 1200 + 0 * 1200 + 0)


def test_gornji_prag_cashflowa_je_zaokruzeni_medijan_od_3_do_5():
    from engine import cf_prag, cf_pojasi
    s = lambda *v: pd.Series(v, dtype=float)
    assert cf_prag(s(0.6, 1.2, 2.0)) == 3          # spora firma: najmanje 3
    assert cf_prag(s(3.6, 3.8, 4.2)) == 4          # medijan 3,8 -> 4
    assert cf_prag(s(8, 12, 30)) == 5              # brza firma: najviše 5
    assert cf_prag(pd.Series([], dtype=float)) == 3
    assert cf_prag(s(1, 2), zadano=6) == 6         # ručno zadan prag
    assert cf_pojasi(4) == ["do 1", "1 do 2", "2 do 4", "preko 4"]


def test_zadani_faktori_su_konzervativni_i_padaju_s_obrtajem():
    f = Parametri().cf_faktori
    assert f == (30, 70, 85, 97)
    assert all(a <= b for a, b in zip(f, f[1:]))  # što sporiji obrtaj, to manji faktor


def test_spranca_ima_opisni_redak_koji_se_preskace():
    from engine import ucitaj, predlozak_csv, predlozak_excel
    redak = ";".join(["A1"] + [""] * 10 + [str(10 + i) for i in range(12)]) + "\n"
    d, _ = priprema(ucitaj(predlozak_csv() + redak.encode("utf-8"), "x.csv"))
    assert d["sifra"].tolist() == ["A1"]                       # opisni redak nije postao artikl
    with pytest.raises(GreskaUnosa, match="nijednog retka"):
        priprema(ucitaj(predlozak_excel(), "p.xlsx"))          # prazna špranca: samo opisi
    d, _ = priprema(ucitaj(predlozak_excel(s_primjerom=True), "primjer.xlsx"))
    assert len(d) == 40


def test_decimalni_zarez_uz_opisni_redak():
    from engine import ucitaj, predlozak_csv
    zaglavlje = predlozak_csv().decode("utf-8").split("\n")[:2]
    redak = ";".join(["A1", "Naziv", "Dob", "1,5", "2,25", "10", "", "", "", "", ""] + ["5"] * 12)
    csv = "\n".join(zaglavlje + [redak]).encode("utf-8")
    d, _ = priprema(ucitaj(csv, "x.csv"))
    assert d["nabavna"].tolist() == [1.5] and d["prodajna"].tolist() == [2.25]


def test_opisi_stupaca_su_recenice_s_uvjetom():
    from engine import OPISI_STUPACA, _opisni_redak, STUPCI_PREDLOSKA
    for naziv, obavezno, tekst in OPISI_STUPACA:
        assert tekst.endswith("."), naziv
        if not obavezno and naziv != "Pakiranje":
            assert tekst.startswith("Ako "), naziv          # npr. "Ako upišete nabavnu cijenu, ..."
    redak = _opisni_redak()
    assert len(redak) == len(STUPCI_PREDLOSKA) and redak[0].startswith("# ")
    assert not any(";" in c for c in redak)                  # ne smije razbiti CSV


def test_objasnjenje_sigurnosne_zalihe_navodi_vremenski_faktor():
    d, _ = priprema(minimalni([[10, 12, 9, 11, 14, 10, 8, 12, 13, 9, 11, 10]]))
    tekst = " ".join(izracunaj(d, Parametri()).pretpostavke)
    assert "vremenski faktor" in tekst and "horizont planiranja" in tekst
    assert "√(21 / 30) = 0.84" in tekst
    assert "Točka ponovnog naručivanja" in tekst
