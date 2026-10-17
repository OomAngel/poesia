"""Break down octo_quatrains.tsv by source / Mexican authorship; write death-subset id list."""

import collections
import csv
import re
import unicodedata

rows = list(csv.DictReader(open("octo_quatrains.tsv"), delimiter="\t", quoting=csv.QUOTE_NONE))
print("es poems with >=2 stanzas:", sum(int(r["stanzas"]) >= 2 for r in rows))
sel = [r for r in rows if r["octo"] == "1" and r["q_loose"] == "1" and r["short"] == "1"]
print(
    "octo&q_loose&short by source:",
    collections.Counter(r["source"] or "(blank)" for r in sel).most_common(12),
)
print(
    "octo all by source:",
    collections.Counter(r["source"] or "(blank)" for r in rows if r["octo"] == "1").most_common(12),
)
mex = [l.split("\t")[1] for l in list(open("mexican_authors.out"))[1:]]


def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    if "," in s:
        a, b = s.split(",", 1)
        s = b + " " + a
    return set(re.findall(r"[a-z]+", s)) - {"de", "la", "y", "del", "fray", "sor"}


mk = [[t for t in norm(m) if len(t) > 1] for m in mex]


def ismex(a):
    at = norm(a)
    if "rojas" in at:
        return False
    return any(len(k) >= 2 and all(t in at for t in k) for k in mk)


mexsel = [r for r in sel if ismex(r["author"])]
print(
    "Mexican-authored octo&q_loose&short:",
    len(mexsel),
    collections.Counter(r["author"] for r in mexsel).most_common(15),
)
print(
    "Mexican-authored octo (any length/shape):",
    sum(1 for r in rows if r["octo"] == "1" and ismex(r["author"])),
)
d = [r for r in sel if r["death"] == "1"]
print("death subset:", len(d), "mexican:", sum(ismex(r["author"]) for r in d))
print("death subset authors:", collections.Counter(r["author"] for r in d).most_common(25))
with open("death_octo_quatrain_ids.tsv", "w") as o:
    for r in d:
        o.write(
            "\t".join(
                [
                    r["id"],
                    r["source"],
                    r["author"],
                    r["title"],
                    r["lines"],
                    str(int(ismex(r["author"]))),
                ]
            )
            + "\n"
        )
