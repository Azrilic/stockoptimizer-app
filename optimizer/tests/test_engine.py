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
