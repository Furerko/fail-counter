
import sys
import os
import csv
from collections import Counter, defaultdict


FAIL_PATTERNS = {
    "Open Camera ExDone on IQT call failed - -2107":
        "CAMERA IQT (2107) - Camera communication error",

    "MTF Image Test error.":
        "MTF Image Test error",

    "Open Camera ExDone on IQT call failed - -2094":
        "CAMERA IQT (2094) - Frame error",

    "Centration Test error.":
        "Centration Test error",
}


def normalize_header(header):
    if header is None:
        return ""
    return str(header).strip().upper().replace("_", " ")


def detect_dialect(file_path):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore", newline="") as f:
            sample = f.read(4096)
            dialect = csv.Sniffer().sniff(sample)
            return dialect
    except Exception:
        return csv.excel


def get_pallet_short_from_row(row):
    """
    Pobiera PALLET ID z kolumny PALLET ID.
    Zwraca ostatnie 3 znaki, np.:
    P14740E181103 -> 103
    """

    for key, value in row.items():
        if normalize_header(key) == "PALLET ID":
            if value and str(value).strip():
                pallet_id = str(value).strip()
                return pallet_id[-3:]

    return "UNKNOWN"


def row_to_text(row):
    """
    Zamienia caly wiersz CSV na tekst.
    Dziala tez gdy csv.DictReader trafi na dodatkowe kolumny.
    """

    parts = []

    for value in row.values():
        if value is None:
            continue

        if isinstance(value, list):
            parts.extend(str(x) for x in value if x is not None)
        else:
            parts.append(str(value))

    return " ".join(parts)


def analyze_csv_file(file_path, fail_counter, pallet_counter):
    dialect = detect_dialect(file_path)

    with open(file_path, "r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f, dialect=dialect)

        if not reader.fieldnames:
            f.seek(0)

            for line in f:
                line_lower = line.lower()
                pallet_short = "UNKNOWN"

                for pattern, label in FAIL_PATTERNS.items():
                    if pattern.lower() in line_lower:
                        fail_counter[label] += 1
                        pallet_counter[label][pallet_short] += 1

            return

        for row in reader:
            pallet_short = get_pallet_short_from_row(row)
            row_text = row_to_text(row)
            row_text_lower = row_text.lower()

            for pattern, label in FAIL_PATTERNS.items():
                if pattern.lower() in row_text_lower:
                    fail_counter[label] += 1
                    pallet_counter[label][pallet_short] += 1


def format_pallets(counter):
    """
    Format:
    103(7), 104(2), 202(1)
    """

    if not counter:
        return "-"

    def sort_key(item):
        pallet, qty = item

        if str(pallet).isdigit():
            return (-qty, int(pallet))

        return (-qty, str(pallet))

    sorted_items = sorted(counter.items(), key=sort_key)

    return ", ".join([f"{pallet}({qty})" for pallet, qty in sorted_items])


def print_summary(fail_counter, pallet_counter, input_files):
    print("\nANALIZOWANE PLIKI:")
    for file_path in input_files:
        print("-", file_path)

    print("\nWYNIK ANALIZY")
    print("=" * 130)
    print(f"{'FAILURE CODE':<70} | {'FAIL COUNT':>10} | {'PALLET ID / QTY':<40}")
    print("-" * 130)

    total = 0

    for pattern, label in FAIL_PATTERNS.items():
        count = fail_counter[label]
        pallets_text = format_pallets(pallet_counter[label])

        print(f"{label:<70} | {count:>10} | {pallets_text:<40}")
        total += count

    print("-" * 130)
    print(f"{'SUMA FAIL':<70} | {total:>10}")
    print("=" * 130)

    if total == 0:
        print("\nNie znaleziono zadnych wskazanych failure kodow.")


def main():
    if len(sys.argv) < 2:
        print("Przeciagnij jeden lub wiecej plikow CSV na program.")
        input("ENTER aby wyjsc...")
        return

    input_files = sys.argv[1:]

    csv_files = [
        file_path for file_path in input_files
        if file_path.lower().endswith(".csv") and os.path.isfile(file_path)
    ]

    if not csv_files:
        print("Nie znaleziono plikow CSV.")
        input("ENTER aby wyjsc...")
        return

    fail_counter = Counter()
    pallet_counter = defaultdict(Counter)

    for file_path in csv_files:
        analyze_csv_file(file_path, fail_counter, pallet_counter)

    print_summary(fail_counter, pallet_counter, csv_files)

    input("\nENTER aby zamknac...")


if __name__ == "__main__":
    main()
