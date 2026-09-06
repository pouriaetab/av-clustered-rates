"""
Estimate the design effect D = E[K^2]/E[K] from California DMV autonomous
vehicle disengagement reports.

The DMV publishes one row per disengagement, with (among others) the fields
Manufacturer, DATE, VIN NUMBER, DISENGAGEMENT INITIATED BY, DISENGAGEMENT
LOCATION, and a free-text cause description. A vehicle-day -- one VIN on one
calendar date -- is a natural and conservative cluster unit: disengagements
logged by the same vehicle on the same day are candidates for sharing an
underlying context (a construction zone, a weather condition, a route).

    D_hat = sum(K_i^2) / sum(K_i)

over observed clusters, where K_i is the number of events in cluster i.

USAGE
-----
The CSVs are linked from
https://www.dmv.ca.gov/portal/vehicle-industry-services/autonomous-vehicles/disengagement-reports/

Download one, then:

    python3 estimate_deff_from_dmv.py 2023-disengagement-reports.csv

CAVEATS -- read these before quoting any number this script prints
------------------------------------------------------------------
1. Reporting practice varies by manufacturer and by year. Some filings
   enumerate every disengagement; others aggregate. A manufacturer that
   aggregates will show an artificially low D_hat.
2. The vehicle-day is one choice of cluster unit among several. Road type,
   location, or cause text would give different partitions and different
   design effects. The right unit depends on the failure mode being studied.
3. Test-fleet disengagements under a safety driver are not the same event
   type as driverless safety events. Do not read these design effects as
   directly applicable to a driverless deployment without argument.
4. Manufacturers with very few reported events give unstable estimates; the
   script flags rows with fewer than 30 events.
"""

import csv
import sys
from collections import Counter, defaultdict


def sniff_open(path):
    """DMV files vary in encoding; try utf-8 then fall back."""
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(path, newline="", encoding=enc) as f:
                f.read()
            return open(path, newline="", encoding=enc)
        except UnicodeDecodeError:
            continue
    raise SystemExit(f"could not decode {path}")


def find_col(fieldnames, *needles):
    """Locate a column by fuzzy match, since headers drift between years."""
    for name in fieldnames:
        flat = "".join(ch for ch in name.upper() if ch.isalnum())
        if all(n in flat for n in needles):
            return name
    return None


def deff(sizes):
    """D_hat = sum(K^2)/sum(K)."""
    total = sum(sizes)
    if total == 0:
        return float("nan")
    return sum(k * k for k in sizes) / total


def main(path):
    fh = sniff_open(path)
    reader = csv.DictReader(fh)
    if not reader.fieldnames:
        raise SystemExit("no header row found")

    col_mfr = find_col(reader.fieldnames, "MANUFACTURER")
    col_date = find_col(reader.fieldnames, "DATE")
    col_vin = find_col(reader.fieldnames, "VIN")

    missing = [n for n, c in
               [("Manufacturer", col_mfr), ("DATE", col_date), ("VIN", col_vin)]
               if c is None]
    if missing:
        print("Columns found:", reader.fieldnames)
        raise SystemExit(f"could not locate required column(s): {missing}")

    # cluster key -> count, per manufacturer
    vehicle_day = defaultdict(Counter)   # mfr -> Counter[(vin, date)]
    mfr_day = defaultdict(Counter)       # mfr -> Counter[date]
    rows = 0

    for row in reader:
        mfr = (row.get(col_mfr) or "").strip()
        date = (row.get(col_date) or "").strip()
        vin = (row.get(col_vin) or "").strip()
        if not mfr or not date:
            continue
        rows += 1
        vehicle_day[mfr][(vin, date)] += 1
        mfr_day[mfr][date] += 1
    fh.close()

    print(f"\nFile: {path}")
    print(f"Disengagement rows parsed: {rows:,}")
    print(f"Manufacturers: {len(vehicle_day)}")
    print()
    print(f"{'Manufacturer':<34} {'events':>8} {'clusters':>9} "
          f"{'mean K':>7} {'D_hat':>7}   {'D_hat':>7}")
    print(f"{'':<34} {'':>8} {'(veh-day)':>9} {'':>7} {'veh-day':>7}   "
          f"{'mfr-day':>7}")
    print("-" * 82)

    all_vd, all_md = [], []
    for mfr in sorted(vehicle_day, key=lambda m: -sum(vehicle_day[m].values())):
        vd_sizes = list(vehicle_day[mfr].values())
        md_sizes = list(mfr_day[mfr].values())
        n_events = sum(vd_sizes)
        all_vd.extend(vd_sizes)
        all_md.extend(md_sizes)

        flag = "  (n<30, unstable)" if n_events < 30 else ""
        print(f"{mfr[:34]:<34} {n_events:>8,} {len(vd_sizes):>9,} "
              f"{n_events/len(vd_sizes):>7.2f} {deff(vd_sizes):>7.2f}   "
              f"{deff(md_sizes):>7.2f}{flag}")

    print("-" * 82)
    print(f"{'POOLED':<34} {sum(all_vd):>8,} {len(all_vd):>9,} "
          f"{sum(all_vd)/len(all_vd):>7.2f} {deff(all_vd):>7.2f}   "
          f"{deff(all_md):>7.2f}")

    d = deff(all_vd)
    print()
    print(f"Pooled vehicle-day design effect D_hat = {d:.2f}")
    print(f"  -> naive 95% CIs are too narrow by a factor of {d**0.5:.2f}")
    print(f"  -> required demonstration mileage understated by {d:.2f}x")
    print()
    print("Read the CAVEATS in this file's docstring before quoting these.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
