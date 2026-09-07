"""
Build the empirical design-effect table for the paper from California DMV
autonomous vehicle disengagement reports (testing with a driver).

Cluster unit: the vehicle-day, i.e. one VIN on one calendar date. Design effect
estimated as D_hat = sum(K_i^2) / sum(K_i) over observed clusters.

Emits a plain-text table, a LaTeX table body, and parsing diagnostics.

USAGE
    python3 empirical_deff.py data/2023-*.csv data/2024-*.csv

Read the CAVEATS in estimate_deff_from_dmv.py before quoting any figure here.
"""

import csv
import re
import sys
from collections import Counter, defaultdict

MIN_EVENTS = 30  # below this, D_hat is too unstable to report


def open_any(path):
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(path, newline="", encoding=enc) as f:
                f.read()
            return open(path, newline="", encoding=enc)
        except UnicodeDecodeError:
            continue
    raise SystemExit(f"could not decode {path}")


def find_col(fieldnames, *needles):
    for name in fieldnames:
        flat = "".join(ch for ch in (name or "").upper() if ch.isalnum())
        if all(n in flat for n in needles):
            return name
    return None


def canon_mfr(name):
    """Normalise manufacturer spelling so a fleet matches across years."""
    s = re.sub(r"[^A-Za-z0-9 ]", " ", name).upper()
    s = re.sub(r"\b(INC|LLC|CORP|CORPORATION|COMPANY|CO|LTD|USA|US|"
               r"NORTH|AMERICA|TECHNOLOGIES|OPERATIONS|RESEARCH|DEVELOPMENT|"
               r"DBA|NATC|BY|TOYOTA|AD|AI)\b", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s or name.upper().strip()


def deff(sizes):
    tot = sum(sizes)
    return float("nan") if tot == 0 else sum(k * k for k in sizes) / tot


def load(path):
    fh = open_any(path)
    reader = csv.DictReader(fh)
    c_mfr = find_col(reader.fieldnames, "MANUFACTURER")
    c_date = find_col(reader.fieldnames, "DATE")
    c_vin = find_col(reader.fieldnames, "VIN")
    if not all([c_mfr, c_date, c_vin]):
        raise SystemExit(f"{path}: missing required columns")

    clusters = defaultdict(Counter)   # canon mfr -> Counter[(vin, date)]
    display = {}                      # canon mfr -> prettiest seen name
    kept = skipped = 0
    for row in reader:
        mfr = (row.get(c_mfr) or "").strip()
        date = (row.get(c_date) or "").strip()
        vin = (row.get(c_vin) or "").strip()
        if not mfr or not date or not vin:
            skipped += 1
            continue
        kept += 1
        key = canon_mfr(mfr)
        display.setdefault(key, mfr)
        clusters[key][(vin, date)] += 1
    fh.close()
    return clusters, display, kept, skipped


def main(paths):
    years, per_year, names = [], {}, {}
    for p in paths:
        m = re.search(r"(20\d{2})", p)
        year = m.group(1) if m else p
        years.append(year)
        clusters, display, kept, skipped = load(p)
        per_year[year] = clusters
        names.update(display)
        print(f"[{year}] {p}")
        print(f"        rows kept {kept:,}   skipped (blank mfr/date/VIN) "
              f"{skipped:,}")
    print()

    # Manufacturers meeting the threshold in at least one year
    keys = sorted(
        {k for y in years for k, c in per_year[y].items()
         if sum(c.values()) >= MIN_EVENTS},
        key=lambda k: -max(sum(per_year[y].get(k, Counter()).values())
                           for y in years))

    hdr = f"{'Fleet':<26}"
    for y in years:
        hdr += f"{y+' n':>9}{y+' D':>8}"
    print(hdr)
    print("-" * len(hdr))

    rows_tex = []
    for k in keys:
        line = f"{names[k][:26]:<26}"
        tex = [names[k].title().replace("&", "\\&")]
        for y in years:
            sizes = list(per_year[y].get(k, Counter()).values())
            n = sum(sizes)
            if n >= MIN_EVENTS:
                d = deff(sizes)
                line += f"{n:>9,}{d:>8.2f}"
                tex += [f"{n:,}", f"{d:.2f}"]
            else:
                line += f"{'--':>9}{'--':>8}"
                tex += ["--", "--"]
        print(line)
        rows_tex.append(" & ".join(tex) + r" \\")

    print("-" * len(hdr))
    pooled_line = f"{'POOLED (all fleets)':<26}"
    pooled_tex = [r"\textbf{Pooled, all fleets}"]
    for y in years:
        allsizes = [v for c in per_year[y].values() for v in c.values()]
        n, d = sum(allsizes), deff(allsizes)
        pooled_line += f"{n:>9,}{d:>8.2f}"
        pooled_tex += [f"\\textbf{{{n:,}}}", f"\\textbf{{{d:.2f}}}"]
    print(pooled_line)

    print("\n\n%%% LaTeX table body %%%")
    for r in rows_tex:
        print(r)
    print(r"\midrule")
    print(" & ".join(pooled_tex) + r" \\")

    print("\n%%% summary %%%")
    for y in years:
        allsizes = [v for c in per_year[y].values() for v in c.values()]
        d = deff(allsizes)
        print(f"{y}: pooled D_hat = {d:.2f}, CI too narrow by {d**0.5:.2f}x, "
              f"mileage understated by {d:.2f}x")
    reported = [deff(list(per_year[y][k].values()))
                for y in years for k in per_year[y]
                if sum(per_year[y][k].values()) >= MIN_EVENTS]
    print(f"per-fleet D_hat range across both years: "
          f"{min(reported):.2f} to {max(reported):.2f}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    main(sys.argv[1:])
