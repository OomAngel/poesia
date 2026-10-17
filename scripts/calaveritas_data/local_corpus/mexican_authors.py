"""Count corpus_master poems by Mexican authors (read-only).

corpus_master has no country field. Mexican authorship is taken from two lists:
  (1) DISCO v5 author_metadata.tsv rows with country-birth == México (data-derived, 35 authors),
  (2) a hand list of Mexican poets (name, death year) written for this check — a lower bound:
      a Mexican poet not on either list is missed.
Names are matched after accent-stripping, lower-casing and "Surname, Name" -> "Name Surname";
a list name matches when all its tokens appear in the record's author string.
Usage: python mexican_authors.py
"""

import csv
import json
import re
import unicodedata
from collections import Counter, defaultdict

CM = "/home/angel/dev/poesia/seeds/poetry_corpus/corpus_master/poems.jsonl"
DISCO = "/home/angel/dev/poesia/seeds/poetry_corpus/external/disco-5.0/author_metadata.tsv"

HAND = {  # name: death year (None = living / unknown)
    "Sor Juana Ines de la Cruz": 1695,  # codespell:ignore
    "Juana Ines de la Cruz": 1695,  # codespell:ignore
    "Juan Ruiz de Alarcon": 1639,
    "Francisco de Terrazas": 1600,
    "Luis de Sandoval y Zapata": 1671,
    "Carlos de Siguenza y Gongora": 1700,
    "Matias de Bocanegra": 1668,
    "Manuel Martinez de Navarrete": 1809,
    "Jose Joaquin Fernandez de Lizardi": 1827,
    "Andres Quintana Roo": 1851,
    "Jose Joaquin Pesado": 1861,
    "Manuel Carpio": 1860,
    "Fernando Calderon": 1845,
    "Ignacio Rodriguez Galvan": 1842,
    "Guillermo Prieto": 1897,
    "Ignacio Ramirez": 1879,
    "Ignacio Manuel Altamirano": 1893,
    "Vicente Riva Palacio": 1896,
    "Juan de Dios Peza": 1910,
    "Manuel Acuna": 1873,
    "Manuel M. Flores": 1885,
    "Manuel Maria Flores": 1885,
    "Antonio Plaza": 1882,
    "Jose Rosas Moreno": 1883,
    "Joaquin Arcadio Pagaza": 1918,
    "Manuel Jose Othon": 1906,
    "Salvador Diaz Miron": 1928,
    "Manuel Gutierrez Najera": 1895,
    "Amado Nervo": 1919,
    "Luis G. Urbina": 1934,
    "Enrique Gonzalez Martinez": 1952,
    "Jose Juan Tablada": 1945,
    "Efren Rebolledo": 1929,
    "Maria Enriqueta Camarillo": 1968,
    "Francisco A. de Icaza": 1925,
    "Balbino Davalos": 1951,
    "Ramon Lopez Velarde": 1921,
    "Alfonso Reyes": 1959,
    "Carlos Pellicer": 1977,
    "Jose Gorostiza": 1973,
    "Xavier Villaurrutia": 1950,
    "Salvador Novo": 1974,
    "Jaime Torres Bodet": 1974,
    "Gilberto Owen": 1952,
    "Bernardo Ortiz de Montellano": 1949,
    "Manuel Maples Arce": 1981,
    "Renato Leduc": 1986,
    "Elias Nandino": 1993,
    "Concha Urquiza": 1945,
    "Octavio Paz": 1998,
    "Efrain Huerta": 1982,
    "Ali Chumacero": 2010,
    "Ruben Bonifaz Nuno": 2013,
    "Rosario Castellanos": 1974,
    "Jaime Sabines": 1999,
    "Marco Antonio Montes de Oca": 2009,
    "Eduardo Lizalde": 2022,
    "Jose Emilio Pacheco": 2014,
    "Homero Aridjis": None,
    "Juan Banuelos": 2017,
    "Gabriel Zaid": None,
    "Jaime Labastida": None,
    "David Huerta": 2022,
    "Elsa Cross": None,
    "Coral Bracho": None,
    "Francisco Hernandez": 2022,
    "Vicente Quirarte": None,
    "Gloria Gervitz": 2022,
    "Pura Lopez Colome": None,
    "Alberto Blanco": None,
    "Efrain Bartolome": None,
    "Carlos Montemayor": 2010,
    "Jose Carlos Becerra": 1970,
    "Jorge Cuesta": 1942,
    "Justo Sierra": 1912,
    "Jose Peon Contreras": 1907,
    "Laura Mendez de Cuenca": 1928,
    "Agustin F. Cuenca": 1884,
    "Francisco Gonzalez Leon": 1945,
    "Alfredo R. Placencia": 1930,
    "Guillermo Aguirre y Fierro": 1949,
    "Antonio Mediz Bolio": 1957,
    "Rafael Lopez": 1943,
    "Margarita Michelena": 1998,
    "Dolores Castro": 2022,
    "Enriqueta Ochoa": 2008,
    "Guadalupe Amor": 2000,
    "Griselda Alvarez": 2009,
    "Mario Santiago Papasquiaro": 1998,
    "Marco Antonio Campos": None,
    "Tomas Segovia": 2011,
    "Ricardo Castillo": None,
    "Max Rojas": 2015,
    "Jose Maria Roa Barcena": 1908,
    "Ignacio Montes de Oca": 1921,
    "Jose Juan Arreola": 2001,
    "Juan Jose Arreola": 2001,
    "Thelma Nava": 2019,
    "Oscar Oliva": None,
    "Ernesto Cardenal": None,  # (Cardenal is Nicaraguan: excluded below)
}
NOT_MEXICAN = {"Ernesto Cardenal"}


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    if "," in s:  # "Nervo, Amado" -> "amado nervo"
        a, b = s.split(",", 1)
        s = b + " " + a
    return re.findall(r"[a-z]+", s)


def main():
    keys = {}
    for row in csv.DictReader(open(DISCO, encoding="utf-8"), delimiter="\t"):
        if "xico" in (row.get("country-birth") or ""):
            keys[row["author"]] = ("disco", row.get("death"))
    for k, d in HAND.items():
        if k not in NOT_MEXICAN:
            keys.setdefault(k, ("hand", d))
    # drop particles from token sets, require >= 2 content tokens
    STOP = {"de", "la", "y", "del", "fray", "sor"}
    ktoks = {k: [t for t in norm(k) if t not in STOP and len(t) > 1] for k in keys}
    per_author, per_src = Counter(), defaultdict(Counter)
    eras = defaultdict(Counter)
    total_es = 0
    with open(CM, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            r = json.loads(line)
            if r["language"] != "es":
                continue
            total_es += 1
            atoks = set(t for t in norm(r["author"]) if t not in STOP)
            hit = None
            if (
                "rojas" in atoks
            ):  # "Soto, Pedro de" (DISCO, Mexico) must not match Pedro Soto de Rojas (Granada)
                continue
            for k, toks in ktoks.items():
                if len(toks) >= 2 and all(t in atoks for t in toks):
                    hit = k
                    break
            if hit:
                per_author[hit] += 1
                per_src[hit][r["source"] or "(blank)"] += 1
                eras[hit][r.get("century") or ""] += 1
    tot = sum(per_author.values())
    print(
        f"Spanish poems: {total_es}; by listed Mexican authors: {tot} ({tot / total_es:.1%}); authors matched: {len(per_author)}"
    )
    for a, n in per_author.most_common():
        print(f"{n}\t{a}\t{keys[a][0]}\tdeath={keys[a][1]}\t{dict(per_src[a])}")


if __name__ == "__main__":
    main()
