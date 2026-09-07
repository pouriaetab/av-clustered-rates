"""
Estimate design effects from NHTSA Standing General Order (SGO 2021-01)
ADS incident reports.

WHY THIS FILE EXISTS
--------------------
The CA DMV analysis (empirical_deff.py) measures clustering in *safety-driver
disengagements*. SGO ADS reports cover *driverless* operation, so they speak
directly to the event class the paper actually cares about. This is the
event-class caveat in Section 6.2 addressed rather than disclosed.

TWO DEDUPLICATION STEPS THAT MUST HAPPEN FIRST
-----------------------------------------------
The SGO file is a report log, not an event log. Measuring clustering on raw
rows would measure how often entities FILE, not how often events HAPPEN --
which would be a different quantity wearing this paper's label. So:

1. Report versions. One incident is amended over time; each amendment is a new
   row sharing a "Report ID" with a higher "Report Version". We keep only the
   highest version per Report ID.
2. Duplicate reports of one incident. NHTSA assigns "Same Incident ID" to link
   reports describing the same physical event (e.g. two entities reporting one
   crash). We collapse each Same Incident ID to a single event.

Only after both do we count events per cluster.

CLUSTER UNITS
-------------
  vehicle-day   (Same Vehicle ID, or VIN as fallback) x Incident Date
                -- the unit used for the DMV analysis, for comparability
  entity-city-day  Reporting Entity x City x Incident Date
                -- coarser; catches "one bad location on one day" clustering
                   that the vehicle-day unit misses when a fleet rotates cars

EXPECT D_hat NEAR 1 AND READ IT HONESTLY
-----------------------------------------
SGO ADS incidents are far rarer per vehicle-day than disengagements. Two
reportable incidents on the same vehicle on the same day is an unusual event,
so most clusters will be size 1 and D_hat may come out close to 1.

That is a legitimate finding, not a failure. It would mean driverless
reportable incidents do not cluster at the vehicle-day level -- which narrows
the paper's claim to the event classes that do cluster (disengagements,
near-misses, behavioural events, which is what the rate-estimation literature
actually models) rather than refuting it. Report whatever comes out.

USAGE
    python3 sgo_deff.py data/SGO-2021-01_Incident_Reports_ADS.csv

Download from:
    https://static.nhtsa.gov/odi/ffdd/sgo-2021-01/SGO-2021-01_Incident_Reports_ADS.csv
"""

import csv
import re
import sys
from collections import Counter, defaultdict

csv.field_size_limit(10_000_000)  # narrative fields are large

MIN_EVENTS = 30


def open_any(path):
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(path, newline="", encoding=enc) as f:
                f.read()
            return open(path, newline="", encoding=enc)
        except UnicodeDecodeError:
            continue
    raise SystemExit(f"could not decode {path}")


def find_col(fieldnames, *needles, exclude=()):
    best = None
    for name in fieldnames or []:
        flat = "".join(c for c in (name or "").upper() if c.isalnum())
        if all(n in flat for n in needles) and not any(x in flat for x in exclude):
            if best is None or len(flat) < len(best[1]):
                best = (name, flat)
    return best[0] if best else None


def deff(sizes):
    tot = sum(sizes)
    return float("nan") if tot == 0 else sum(k * k for k in sizes) / tot


def norm_date(s):
    s = (s or "").strip()
    if not s:
        return ""
    m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$", s)
    if m:
        mo, d, y = m.groups()
        y = ("20" + y) if len(y) == 2 else y
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"
    return s


def main(path):
    fh = open_any(path)
    reader = csv.DictReader(fh)
    fn = reader.fieldnames

    c_rid = find_col(fn, "REPORTID")
    c_ver = find_col(fn, "REPORTVERSION")
    c_inc = find_col(fn, "SAMEINCIDENTID")
    c_veh = find_col(fn, "SAMEVEHICLEID")
    c_vin = find_col(fn, "VIN", exclude=("DECODED",))
    c_ent = find_col(fn, "REPORTINGENTITY")
    c_date = find_col(fn, "INCIDENTDATE", exclude=("UNKNOWN",))
    c_city = find_col(fn, "CITY", exclude=("UNKNOWN",))

    print(f"\nFile: {path}")
    print("Columns resolved:")
    for label, col in [("Report ID", c_rid), ("Report Version", c_ver),
                       ("Same Incident ID", c_inc), ("Same Vehicle ID", c_veh),
                       ("VIN", c_vin), ("Reporting Entity", c_ent),
                       ("Incident Date", c_date), ("City", c_city)]:
        print(f"   {label:<18} {col!r}")
    if not (c_ent and c_date):
        raise SystemExit("missing Reporting Entity or Incident Date")

    rows = list(reader)
    fh.close()
    print(f"\nRaw rows: {len(rows):,}")

    # --- dedup 1: keep highest Report Version per Report ID -----------------
    if c_rid and c_ver:
        best = {}
        for r in rows:
            rid = (r.get(c_rid) or "").strip()
            try:
                v = float((r.get(c_ver) or "0").strip() or 0)
            except ValueError:
                v = 0.0
            if not rid:
                best[id(r)] = (v, r)
            elif rid not in best or v > best[rid][0]:
                best[rid] = (v, r)
        rows = [r for _, r in best.values()]
        print(f"After keeping latest report version:  {len(rows):,}")

    # --- dedup 2: collapse Same Incident ID --------------------------------
    if c_inc:
        seen, out, collapsed = set(), [], 0
        for r in rows:
            sid = (r.get(c_inc) or "").strip()
            if sid:
                if sid in seen:
                    collapsed += 1
                    continue
                seen.add(sid)
            out.append(r)
        rows = out
        print(f"After collapsing Same Incident ID:    {len(rows):,} "
              f"({collapsed:,} duplicate reports of one event removed)")

    # --- cluster ------------------------------------------------------------
    veh_day = defaultdict(Counter)
    ent_city_day = defaultdict(Counter)
    no_vehicle_key = no_date = 0

    for r in rows:
        ent = (r.get(c_ent) or "").strip() or "(unknown entity)"
        date = norm_date(r.get(c_date))
        if not date:
            no_date += 1
            continue
        vkey = (r.get(c_veh) or "").strip() if c_veh else ""
        if not vkey and c_vin:
            v = (r.get(c_vin) or "").strip()
            vkey = v if v and "PERSONALLY" not in v.upper() else ""
        if vkey:
            veh_day[ent][(vkey, date)] += 1
        else:
            no_vehicle_key += 1
        city = (r.get(c_city) or "").strip().upper() if c_city else ""
        ent_city_day[ent][(city, date)] += 1

    print(f"Rows without a usable incident date:  {no_date:,}")
    print(f"Rows without a usable vehicle key:    {no_vehicle_key:,}")

    def table(title, data):
        print(f"\n{title}")
        print(f"{'Reporting entity':<34}{'events':>8}{'clusters':>10}"
              f"{'mean K':>8}{'D_hat':>8}")
        print("-" * 68)
        allsizes = []
        for ent in sorted(data, key=lambda e: -sum(data[e].values())):
            sizes = list(data[ent].values())
            n = sum(sizes)
            allsizes.extend(sizes)
            if n < MIN_EVENTS:
                continue
            print(f"{ent[:34]:<34}{n:>8,}{len(sizes):>10,}"
                  f"{n/len(sizes):>8.2f}{deff(sizes):>8.2f}")
        print("-" * 68)
        d = deff(allsizes)
        print(f"{'POOLED (all entities)':<34}{sum(allsizes):>8,}"
              f"{len(allsizes):>10,}{sum(allsizes)/len(allsizes):>8.2f}{d:>8.2f}")
        return d

    d_veh = table("Cluster unit: vehicle-day", veh_day)
    d_ecd = table("Cluster unit: entity-city-day", ent_city_day)

    print("\n%%% summary %%%")
    for label, d in [("vehicle-day", d_veh), ("entity-city-day", d_ecd)]:
        print(f"{label:<18} pooled D_hat = {d:.2f}  ->  CI too narrow by "
              f"{d**0.5:.2f}x, mileage understated by {d:.2f}x")
    print("\nRead the 'EXPECT D_hat NEAR 1' note in this file's docstring before "
          "interpreting a value close to 1.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
