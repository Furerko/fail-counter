import sys
import os
import csv
import re
from collections import Counter, defaultdict
from datetime import datetime

FAIL_PATTERNS = {
    "FAIL ALIGN - (063) Align Focus Conversion Failed.  Unable to align lens within maximum number of attempts.":
        "FAIL ALIGN (063) - Align Focus Conversion failed",

    "FAIL ALIGN - (205) Failed to compute final Z position":
        "FAIL ALIGN (205) - Failed to compute final Z position",

    "FAIL ALIGN - Final Image Test Failed.  MTF (Could not find the required geometry in the ROI.)":
        "FAIL ALIGN - MTF (ROI not found)",

    "FAIL ALIGN - Final Image Test Failed.  MTF.":
        "FAIL ALIGN - MTF",

    "FAIL DISPENSE - (112) Unable to Detect Camera Housing":
        "FAIL DISPENSE (112) - Unable to Detect Camera Housing",

    "FAIL DISPENSE - (128) Unable to Verify Epoxy Bead":
        "FAIL DISPENSE (128) - Epoxy Bead validation failed",

    "Open Camera ExDone on Align call failed - -2094":
        "CAMERA ALIGN (2094) - Frame error",

    "Open Camera ExDone on Align call failed - -2107":
        "CAMERA ALIGN (2107) - Communication error",

    "Open Camera ExDone on Dispense call failed - -2094":
        "CAMERA DISPENSE (2094) - Frame error",

    "Open Camera ExDone on Dispense call failed - -2107":
        "CAMERA DISPENSE (2107) - Communication error",
}


def get_exe_folder():
    """
    Zwraca folder, w ktorym znajduje sie plik .exe.
    Dziala poprawnie po zbudowaniu przez PyInstaller.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def normalize_header(header):
    """
    Ujednolica nazwe kolumny.
    Przyklad:
    SETUP_TAG -> SETUP TAG
    Pallet Id -> PALLET ID
    """
    if header is None:
        return ""
    return str(header).strip().upper().replace("_", " ")


def find_setup_tag_from_row(row):
    """
    Probuje znalezc wartosc kolumny SETUP TAG w wierszu CSV.
    Jesli kolumna nie istnieje, zwraca UNKNOWN_SETUP_TAG.
    """

    for key, value in row.items():
        if normalize_header(key) == "SETUP TAG":
            if value and str(value).strip():
                return str(value).strip()

    row_text = " ".join(str(v) for v in row.values() if v is not None)

    patterns = [
        r"SETUP TAG\s*=\s*([^,;]+)",
        r"SETUP_TAG\s*=\s*([^,;]+)",
        r"SETUP TAG\s*:\s*([^,;]+)",
        r"SETUP_TAG\s*:\s*([^,;]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, row_text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    return "UNKNOWN_SETUP_TAG"


def find_pallet_id_from_row(row):
    """
    Pobiera PALLET ID z kolumny PALLET ID.
    Zwraca ostatnie 3 znaki, np.:
    P14740E181103 -> 103

    Jesli PALLET ID nie istnieje, zwraca UNKNOWN.
    """

    # 1. Normalna kolumna CSV
    for key, value in row.items():
        if normalize_header(key) == "PALLET ID":
            if value and str(value).strip():
                pallet_id = str(value).strip()
                return pallet_id[-3:]

    # 2. Fallback: szukanie tekstowe w calym wierszu, np. PALLET ID=...
    row_text = " ".join(str(v) for v in row.values() if v is not None)

    patterns = [
        r"PALLET ID\s*=\s*([^,;]+)",
        r"PALLET_ID\s*=\s*([^,;]+)",
        r"PALLET ID\s*:\s*([^,;]+)",
        r"PALLET_ID\s*:\s*([^,;]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, row_text, re.IGNORECASE)
        if match:
            pallet_id = match.group(1).strip()
            return pallet_id[-3:]

    return "UNKNOWN"


def detect_dialect(file_path):
    """
    Probuje wykryc separator CSV.
    Jesli sie nie uda, uzywa przecinka.
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore", newline="") as f:
            sample = f.read(4096)
            dialect = csv.Sniffer().sniff(sample)
            return dialect
    except Exception:
        return csv.excel


def analyze_csv_file(file_path, grouped_counter, file_counter, pallet_counter):
    """
    Analizuje jeden plik CSV.

    Wyniki zapisuje do:
    - grouped_counter[SETUP TAG][FAIL LABEL]
    - file_counter[NAZWA PLIKU][SETUP TAG][FAIL LABEL]
    - pallet_counter[SETUP TAG][FAIL LABEL][PALLET_LAST_3]
    """

    dialect = detect_dialect(file_path)

    with open(file_path, "r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f, dialect=dialect)

        # Jesli DictReader nie widzi naglowkow, fallback do zwyklego czytania linii
        if not reader.fieldnames:
            f.seek(0)
            for line in f:
                setup_tag = "UNKNOWN_SETUP_TAG"
                pallet_short = "UNKNOWN"

                for key, label in FAIL_PATTERNS.items():
                    if key in line:
                        grouped_counter[setup_tag][label] += 1
                        file_counter[os.path.basename(file_path)][setup_tag][label] += 1
                        pallet_counter[setup_tag][label][pallet_short] += 1
            return

        for row in reader:
            setup_tag = find_setup_tag_from_row(row)
            pallet_short = find_pallet_id_from_row(row)
            row_text = " ".join(str(v) for v in row.values() if v is not None)

            for key, label in FAIL_PATTERNS.items():
                if key in row_text:
                    grouped_counter[setup_tag][label] += 1
                    file_counter[os.path.basename(file_path)][setup_tag][label] += 1
                    pallet_counter[setup_tag][label][pallet_short] += 1


def get_pallets_above_5(pallet_counter_for_fail):
    """
    Zwraca liste paletek, gdzie liczba FAIL dla danego failure kodu jest > 5.
    Przyklad wyniku:
    ['102', '103', '104']
    """

    pallets = []

    for pallet_short, count in pallet_counter_for_fail.items():
        if pallet_short != "UNKNOWN" and count > 5:
            pallets.append(pallet_short)

    # sortowanie numeryczne jesli sie da, inaczej tekstowe
    def sort_key(value):
        if str(value).isdigit():
            return int(value)
        return str(value)

    return sorted(pallets, key=sort_key)


def write_report(output_file, grouped_counter, file_counter, pallet_counter, input_files):
    """
    Tworzy raport TXT:
    - lista analizowanych plikow
    - podzial po SETUP TAG
    - wszystkie FAILe
    - TOP 5 dla kazdego SETUP TAG
    - paletki z >5 FAIL dla kazdego failure kodu
    - podzial per plik
    """

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("FAIL REPORT\n")
        f.write(f"DATA: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 120 + "\n\n")

        f.write("ANALIZOWANE PLIKI:\n")
        for file_path in input_files:
            f.write(f"- {file_path}\n")

        f.write("\n" + "=" * 120 + "\n\n")

        grand_total = 0

        f.write("PODSUMOWANIE WG SETUP TAG\n")
        f.write("=" * 120 + "\n\n")

        for setup_tag, counter in grouped_counter.items():
            sorted_fails = counter.most_common()
            total_for_setup = sum(counter.values())
            grand_total += total_for_setup

            f.write(f"SETUP TAG: {setup_tag}\n")
            f.write("-" * 120 + "\n")
            f.write("ALL FAILS:\n")

            for label, count in sorted_fails:
                pallets_above_5 = get_pallets_above_5(pallet_counter[setup_tag][label])

                if pallets_above_5:
                    pallets_text = ", ".join(pallets_above_5)
                    f.write(f"{label} {count} | PALETKI >5 FAIL: {pallets_text}\n")
                else:
                    f.write(f"{label} {count}\n")

            f.write("\nTOP 5:\n")
            top5 = sorted_fails[:5]

            if top5:
                top5_parts = []

                for label, count in top5:
                    pallets_above_5 = get_pallets_above_5(pallet_counter[setup_tag][label])

                    if pallets_above_5:
                        pallets_text = ", ".join(pallets_above_5)
                        top5_parts.append(f"{label} {count} [PALETKI >5 FAIL: {pallets_text}]")
                    else:
                        top5_parts.append(f"{label} {count}")

                top5_line = ", ".join(top5_parts) + "."
            else:
                top5_line = "BRAK FAIL."

            f.write(top5_line + "\n")

            f.write(f"\nSUMA FAIL DLA SETUP TAG: {total_for_setup}\n")
            f.write("=" * 120 + "\n\n")

        f.write(f"SUMA WSZYSTKICH FAIL: {grand_total}\n")
        f.write("=" * 120 + "\n\n")

        f.write("SZCZEGOLY WG PLIKOW\n")
        f.write("=" * 120 + "\n\n")

        for file_name, setup_data in file_counter.items():
            f.write(f"PLIK: {file_name}\n")
            f.write("-" * 120 + "\n")

            for setup_tag, counter in setup_data.items():
                f.write(f"  SETUP TAG: {setup_tag}\n")

                for label, count in counter.most_common():
                    f.write(f"    {label} {count}\n")

                f.write(f"    SUMA: {sum(counter.values())}\n\n")

            f.write("=" * 120 + "\n\n")


def print_console_summary(grouped_counter, pallet_counter):
    """
    Pokazuje wynik w konsoli.
    """

    print("\nWYNIK ANALIZY")
    print("=" * 140)

    grand_total = 0

    for setup_tag, counter in grouped_counter.items():
        print(f"\nSETUP TAG: {setup_tag}")
        print("-" * 140)
        print(f"{'FAIL DESCRIPTION':<90} | {'COUNT':>6} | {'PALETKI >5 FAIL':<25}")
        print("-" * 140)

        for label, count in counter.most_common():
            pallets_above_5 = get_pallets_above_5(pallet_counter[setup_tag][label])
            pallets_text = ", ".join(pallets_above_5) if pallets_above_5 else ""

            print(f"{label:<90} | {count:>6} | {pallets_text:<25}")

        setup_total = sum(counter.values())
        grand_total += setup_total

        print("-" * 140)
        print(f"{'SUMA DLA SETUP TAG':<90} | {setup_total:>6}")

    print("=" * 140)
    print(f"{'SUMA WSZYSTKICH FAIL':<90} | {grand_total:>6}")
    print("=" * 140)


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

    grouped_counter = defaultdict(Counter)
    file_counter = defaultdict(lambda: defaultdict(Counter))
    pallet_counter = defaultdict(lambda: defaultdict(Counter))

    print("Analizowane pliki:")
    for file_path in csv_files:
        print("-", file_path)
        analyze_csv_file(file_path, grouped_counter, file_counter, pallet_counter)

    print_console_summary(grouped_counter, pallet_counter)

    exe_dir = get_exe_folder()

    # Nazwa pliku raportu:
    # fail_report__2026_05_06_07_54_00.txt
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    output_file = os.path.join(exe_dir, f"fail_report__{timestamp}.txt")

    write_report(output_file, grouped_counter, file_counter, pallet_counter, csv_files)

    print("\nZapisano raport:")
    print(output_file)

    input("\nENTER aby zamknac...")


if __name__ == "__main__":
    main()
