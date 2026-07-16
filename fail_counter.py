
import sys
import os
import csv
import re
from io import StringIO
from collections import Counter, defaultdict, deque


MTF_LABEL = "MTF Image Test error"
CENTRATION_LABEL = "Centration Test error"


FAIL_PATTERNS = {
    "Open Camera ExDone on IQT call failed - -2107":
        "CAMERA IQT (2107) - Camera communication error",

    "MTF Image Test error":
        MTF_LABEL,

    "Open Camera ExDone on IQT call failed - -2094":
        "CAMERA IQT (2094) - Frame error",

    "Centration Test error":
        CENTRATION_LABEL,
}


def extract_last_3_digits(value):
    if value is None:
        return "UNKNOWN"

    text = str(value).strip()
    digits = re.findall(r"\d", text)

    if len(digits) >= 3:
        return "".join(digits[-3:])

    return "UNKNOWN"


def split_records_from_process_history(file_text):
    pattern = re.compile(
        r"(?m)^\d{1,2}/\d{1,2}/\d{4},\d{1,2}:\d{2}:\d{2}\s*(?:AM|PM),"
    )

    matches = list(pattern.finditer(file_text))

    if not matches:
        return []

    records = []

    for i, match in enumerate(matches):
        start = match.start()

        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(file_text)

        record = file_text[start:end].strip()

        if record:
            records.append(record)

    return records


def parse_record_first_columns(record_text):
    """
    ProcessHistory column order:
    DATE      = index 0
    TIME      = index 1
    PALLET ID = index 16
    PCB ID    = index 17
    """

    one_line = record_text.replace("\r", " ").replace("\n", " ")

    try:
        reader = csv.reader(StringIO(one_line))
        fields = next(reader)

        date_value = fields[0].strip() if len(fields) > 0 else ""
        time_value = fields[1].strip() if len(fields) > 1 else ""
        pallet_id = fields[16].strip() if len(fields) > 16 else ""
        pcb_id = fields[17].strip() if len(fields) > 17 else ""

        return date_value, time_value, pallet_id, pcb_id

    except Exception:
        return "", "", "", ""


def fallback_find_pallet_id(record_text):
    match = re.search(r"P\d{5}[A-Z]\d{6}", record_text)

    if match:
        return match.group(0)

    return ""


def fallback_find_pcb_id(record_text):
    match = re.search(r"\bA[0-9A-Z]{10,20}\b", record_text)

    if match:
        return match.group(0)

    return "UNKNOWN_PCB"


def analyze_record(
    record_text,
    fail_counter,
    pallet_counter,
    last_10_counter,
    last_20_global,
    pcb_by_pallet_counter
):
    date_value, time_value, pallet_id, pcb_id = parse_record_first_columns(record_text)

    if not pallet_id:
        pallet_id = fallback_find_pallet_id(record_text)

    if not pcb_id:
        pcb_id = fallback_find_pcb_id(record_text)

    pallet_short = extract_last_3_digits(pallet_id)

    if not pcb_id:
        pcb_id = "UNKNOWN_PCB"

    if date_value and time_value:
        date_time = date_value + " " + time_value
    elif date_value:
        date_time = date_value
    elif time_value:
        date_time = time_value
    else:
        date_time = "UNKNOWN_TIME"

    record_lower = record_text.lower()

    for pattern, label in FAIL_PATTERNS.items():
        if pattern.lower() in record_lower:
            fail_counter[label] += 1
            pallet_counter[label][pallet_short] += 1

            # LAST 10 FAILS - bez PCB ID
            last_10_counter[label].append((date_time, pallet_short))

            # OSTATNIE 20 SZT. FAIL - bez PCB ID
            last_20_global.append((date_time, pallet_short, label))

            # PCB ID tylko dla MTF Image Test error oraz Centration Test error
            if label in (MTF_LABEL, CENTRATION_LABEL):
                pcb_by_pallet_counter[label][(pallet_short, pcb_id)] += 1


def analyze_csv_file(
    file_path,
    fail_counter,
    pallet_counter,
    last_10_counter,
    last_20_global,
    pcb_by_pallet_counter
):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        file_text = f.read()

    records = split_records_from_process_history(file_text)

    if records:
        for record in records:
            analyze_record(
                record,
                fail_counter,
                pallet_counter,
                last_10_counter,
                last_20_global,
                pcb_by_pallet_counter
            )
        return

    # Fallback dla innego formatu pliku
    for line in file_text.splitlines():
        line_lower = line.lower()

        for pattern, label in FAIL_PATTERNS.items():
            if pattern.lower() in line_lower:
                fail_counter[label] += 1
                pallet_counter[label]["UNKNOWN"] += 1
                last_10_counter[label].append(("UNKNOWN_TIME", "UNKNOWN"))
                last_20_global.append(("UNKNOWN_TIME", "UNKNOWN", label))

                if label in (MTF_LABEL, CENTRATION_LABEL):
                    pcb_by_pallet_counter[label][("UNKNOWN", "UNKNOWN_PCB")] += 1


def format_pallets(counter):
    if not counter:
        return "-"

    def sort_key(item):
        pallet, qty = item

        if str(pallet).isdigit():
            return (-qty, int(pallet))

        return (-qty, str(pallet))

    sorted_items = sorted(counter.items(), key=sort_key)

    return ", ".join([f"{pallet}({qty})" for pallet, qty in sorted_items])


def print_last_20_global(last_20_global):
    events = list(last_20_global)

    print("\nOSTATNIE 20 SZT. FAIL")
    print("=" * 80)

    if not events:
        print("Brak znalezionych FAIL.")
        print("=" * 80)
        return

    for idx, (date_time, pallet_short, label) in enumerate(events, start=1):
        print(f"{idx:>2}. {date_time}")
        print(f"    PALLET : {pallet_short}")
        print(f"    FAIL   : {label}")
        print("-" * 80)

    print("=" * 80)


def print_last_10(label, last_10_counter):
    events = list(last_10_counter[label])

    if not events:
        print("  LAST 10 FAILS: brak")
        return

    print("  LAST 10 FAILS:")

    for idx, (date_time, pallet_short) in enumerate(events, start=1):
        print(f"    {idx:>2}. {date_time}")
        print(f"        PALLET: {pallet_short}")


def print_pcb_by_pallet_table(label, pcb_by_pallet_counter):
    """
    Tabela PCB ID pokazuje się TYLKO dla:
    - MTF Image Test error
    - Centration Test error
    """

    if label not in (MTF_LABEL, CENTRATION_LABEL):
        return

    counter = pcb_by_pallet_counter[label]

    if not counter:
        return

    print("  PCB ID TABLE:")
    print("  " + "-" * 100)
    print(f"  {'PALLET':<10} | {'PCB ID':<35} | {'QTY':>6}")
    print("  " + "-" * 100)

    def sort_key(item):
        (pallet_short, pcb_id), qty = item

        if str(pallet_short).isdigit():
            pallet_sort = int(pallet_short)
        else:
            pallet_sort = 999999

        return (-qty, pallet_sort, pcb_id)

    sorted_items = sorted(counter.items(), key=sort_key)

    for (pallet_short, pcb_id), qty in sorted_items:
        print(f"  {pallet_short:<10} | {pcb_id:<35} | {qty:>6}")

    print("  " + "-" * 100)


def print_summary(
    fail_counter,
    pallet_counter,
    last_10_counter,
    last_20_global,
    pcb_by_pallet_counter,
    input_files
):
    print("\nANALIZOWANE PLIKI:")
    for file_path in input_files:
        print("-", file_path)

    print_last_20_global(last_20_global)

    print("\nWYNIK ANALIZY")
    print("=" * 145)
    print(f"{'FAILURE CODE':<70} | {'FAIL COUNT':>10} | {'PALLET ID / QTY':<50}")
    print("-" * 145)

    total = 0

    for pattern, label in FAIL_PATTERNS.items():
        count = fail_counter[label]
        pallets_text = format_pallets(pallet_counter[label])

        print(f"{label:<70} | {count:>10} | {pallets_text:<50}")
        total += count

        print_last_10(label, last_10_counter)

        # PCB ID tabela tylko dla MTF i Centration
        print_pcb_by_pallet_table(label, pcb_by_pallet_counter)

        print("-" * 145)

    print(f"{'SUMA FAIL':<70} | {total:>10}")
    print("=" * 145)

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
    last_10_counter = defaultdict(lambda: deque(maxlen=10))
    last_20_global = deque(maxlen=20)

    pcb_by_pallet_counter = defaultdict(Counter)

    for file_path in csv_files:
        analyze_csv_file(
            file_path,
            fail_counter,
            pallet_counter,
            last_10_counter,
            last_20_global,
            pcb_by_pallet_counter
        )

    print_summary(
        fail_counter,
        pallet_counter,
        last_10_counter,
        last_20_global,
        pcb_by_pallet_counter,
        csv_files
    )

    input("\nENTER aby zamknac...")


if __name__ == "__main__":
    main()
