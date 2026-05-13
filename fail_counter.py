import sys
import os
import csv
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta

FAIL_PATTERNS = {
    "FAIL ALIGN - (005) Program Stopped by Operator":
        "FAIL ALIGN (005) - Program Stopped by Operator",

    "FAIL ALIGN - (008) Unable to Acquire Align Camera Image.  Frame error":
        "FAIL ALIGN (008) - Unable to Acquire Align Camera Image - Frame error",

    "FAIL ALIGN - (009) Unable to Detect Lens Gripped":
        "FAIL ALIGN (009) - Unable to Detect Lens Gripped",

    "FAIL ALIGN - (063) Align Focus Conversion Failed.  Unable to align lens within maximum number of attempts.":
        "FAIL ALIGN (063) - Align Focus Conversion failed",

    "FAIL ALIGN - (205) Failed to compute final Z position":
        "FAIL ALIGN (205) - Failed to compute final Z position",

    "FAIL ALIGN - Align.  Failed to translate error code":
        "FAIL ALIGN - Failed to translate error code",

    "FAIL ALIGN - Dispense.  Weigh Scale timed out.":
        "FAIL ALIGN - Dispense Weigh Scale timed out",

    "FAIL ALIGN - Final Image Test Failed.  MTF (Could not find the required geometry in the ROI.)":
        "FAIL ALIGN - MTF (ROI not found)",

    "FAIL ALIGN - Final Image Test Failed.  MTF.":
        "FAIL ALIGN - MTF",

    "FAIL DISPENSE - (005) Program Stopped by Operator":
        "FAIL DISPENSE (005) - Program Stopped by Operator",

    "FAIL DISPENSE - (057) Particle Test Failed.":
        "FAIL DISPENSE (057) - Particle Test Failed",

    "FAIL DISPENSE - (112) Unable to Detect Camera Housing":
        "FAIL DISPENSE (112) - Unable to Detect Camera Housing",

    "FAIL DISPENSE - (128) Unable to Verify Epoxy Bead":
        "FAIL DISPENSE (128) - Epoxy Bead validation failed",

    "General Error: One or more errors occurred.":
        "GENERAL ERROR - One or more errors occurred",

    "Material Handler Error Station=Station 1.202 (Dispense Main)":
        "MATERIAL HANDLER - Station 1.202 Dispense Main",

    "Material Handler Error Station=Station 1.211 (Utility Main)":
        "MATERIAL HANDLER - Station 1.211 Utility Main",

    "Material Handler Error Station=Station 2.203 (Dispense Return)":
        "MATERIAL HANDLER - Station 2.203 Dispense Return",

    "Open Camera Ex call on Dispense failed - Open Task Cancelled.":
        "CAMERA DISPENSE - Open Task Cancelled",

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
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def normalize_header(header):
    if header is None:
        return ""
    return str(header).strip().upper().replace("_", " ")


def find_setup_tag_from_row(row):
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
    for key, value in row.items():
        if normalize_header(key) == "PALLET ID":
            if value and str(value).strip():
                pallet_id = str(value).strip()
                return pallet_id[-3:]

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


def parse_datetime_from_text(text):
    if not text:
        return None

    text = str(text).strip()

    date_formats = [
        "%m/%d/%Y, %I:%M:%S %p",
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y, %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%d.%m.%Y %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
    ]

    for fmt in date_formats:
        try:
            return datetime.strptime(text, fmt)
        except Exception:
            pass

    regex_patterns = [
        r"\d{1,2}/\d{1,2}/\d{4},?\s+\d{1,2}:\d{2}:\d{2}\s*(AM|PM)",
        r"\d{1,2}/\d{1,2}/\d{4},?\s+\d{1,2}:\d{2}:\d{2}",
        r"\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}:\d{2}",
        r"\d{2}\.\d{2}\.\d{4}\s+\d{1,2}:\d{2}:\d{2}",
    ]

    for pattern in regex_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            found = match.group(0).strip()
            found = re.sub(r"\s+", " ", found)

            for fmt in date_formats:
                try:
                    return datetime.strptime(found, fmt)
                except Exception:
                    pass

    return None


def find_datetime_from_row(row):
    preferred_headers = [
        "DATE TIME",
        "DATETIME",
        "TIMESTAMP",
        "TIME STAMP",
        "START TIME",
        "END TIME",
        "PROCESS TIME",
        "DATE",
    ]

    for key, value in row.items():
        normalized = normalize_header(key)
        if normalized in preferred_headers:
            dt = parse_datetime_from_text(value)
            if dt:
                return dt

    date_value = None
    time_value = None

    for key, value in row.items():
        normalized = normalize_header(key)

        if normalized == "DATE" and value:
            date_value = str(value).strip()

        if normalized == "TIME" and value:
            time_value = str(value).strip()

    if date_value and time_value:
        dt = parse_datetime_from_text(date_value + " " + time_value)
        if dt:
            return dt

    row_text = " ".join(str(v) for v in row.values() if v is not None)
    return parse_datetime_from_text(row_text)


def get_hour_bucket(dt):
    if dt is None:
        return "UNKNOWN_TIME"

    return dt.strftime("%Y-%m-%d %H:00")


def format_hour_range(hour_bucket):
    if hour_bucket == "UNKNOWN_TIME":
        return "UNKNOWN_TIME"

    try:
        start_dt = datetime.strptime(hour_bucket, "%Y-%m-%d %H:00")
        end_dt = start_dt + timedelta(minutes=59)

        return (
            f"{start_dt.strftime('%Y-%m-%d')} "
            f"od {start_dt.strftime('%H:%M')} "
            f"do {end_dt.strftime('%H:%M')}"
        )
    except Exception:
        return hour_bucket


def detect_dialect(file_path):
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore", newline="") as f:
            sample = f.read(4096)
            dialect = csv.Sniffer().sniff(sample)
            return dialect
    except Exception:
        return csv.excel


def analyze_csv_file(
    file_path,
    grouped_counter,
    pallet_counter,
    trend_counter,
    trend_pallet_counter,
    hot_pallet_counter
):
    dialect = detect_dialect(file_path)

    with open(file_path, "r", encoding="utf-8", errors="ignore", newline="") as f:
        reader = csv.DictReader(f, dialect=dialect)

        if not reader.fieldnames:
            f.seek(0)

            for line in f:
                setup_tag = "UNKNOWN_SETUP_TAG"
                pallet_short = "UNKNOWN"
                hour_bucket = "UNKNOWN_TIME"

                for key, label in FAIL_PATTERNS.items():
                    if key in line:
                        grouped_counter[setup_tag][label] += 1
                        pallet_counter[setup_tag][label][pallet_short] += 1
                        trend_counter[setup_tag][hour_bucket] += 1
                        trend_pallet_counter[setup_tag][hour_bucket][pallet_short] += 1
                        hot_pallet_counter[setup_tag][pallet_short][label] += 1

            return

        for row in reader:
            setup_tag = find_setup_tag_from_row(row)
            pallet_short = find_pallet_id_from_row(row)
            dt = find_datetime_from_row(row)
            hour_bucket = get_hour_bucket(dt)

            row_text = " ".join(str(v) for v in row.values() if v is not None)

            for key, label in FAIL_PATTERNS.items():
                if key in row_text:
                    grouped_counter[setup_tag][label] += 1
                    pallet_counter[setup_tag][label][pallet_short] += 1
                    trend_counter[setup_tag][hour_bucket] += 1
                    trend_pallet_counter[setup_tag][hour_bucket][pallet_short] += 1
                    hot_pallet_counter[setup_tag][pallet_short][label] += 1


def get_pallets_above_5_with_count(pallet_counter_for_fail):
    pallets = []

    for pallet_short, count in pallet_counter_for_fail.items():
        if pallet_short != "UNKNOWN" and count > 5:
            pallets.append((pallet_short, count))

    def sort_key(item):
        pallet_number = item[0]
        if str(pallet_number).isdigit():
            return int(pallet_number)
        return str(pallet_number)

    return sorted(pallets, key=sort_key)


def get_hot_pallets_top5(hot_pallet_counter_for_setup):
    hot_pallets = []

    for pallet_short, fail_counter in hot_pallet_counter_for_setup.items():
        if pallet_short == "UNKNOWN":
            continue

        total = sum(fail_counter.values())

        if total > 5:
            hot_pallets.append((pallet_short, total, fail_counter))

    return sorted(hot_pallets, key=lambda x: (-x[1], x[0]))[:5]


def get_trend_top5_hours(trend_counter_for_setup):
    items = list(trend_counter_for_setup.items())

    def sort_key(item):
        hour_bucket, count = item
        unknown_flag = 1 if hour_bucket == "UNKNOWN_TIME" else 0
        return (-count, unknown_flag, hour_bucket)

    return sorted(items, key=sort_key)[:5]


def get_top_pallets_for_hour(trend_pallet_counter_for_hour):
    pallets = []

    for pallet_short, count in trend_pallet_counter_for_hour.items():
        if pallet_short != "UNKNOWN":
            pallets.append((pallet_short, count))

    return sorted(pallets, key=lambda x: (-x[1], x[0]))[:5]


def format_fail_with_pallets(label, count, pallets_above_5):
    if pallets_above_5:
        pallets_text = ", ".join([f"{pallet}({qty})" for pallet, qty in pallets_above_5])
        return f"{label} {count} [PALETKI >5 FAIL: {pallets_text}]"

    return f"{label} {count}"


def write_report(output_file, grouped_counter, pallet_counter, input_files):
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("FAIL REPORT - TOP 5 WG SETUP TAG\n")
        f.write(f"DATA: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 120 + "\n\n")

        f.write("ANALIZOWANE PLIKI:\n")
        for file_path in input_files:
            f.write(f"- {file_path}\n")

        f.write("\n" + "=" * 120 + "\n\n")

        grand_total = 0

        for setup_tag, counter in grouped_counter.items():
            sorted_fails = counter.most_common()
            top5 = sorted_fails[:5]
            total_for_setup = sum(counter.values())
            grand_total += total_for_setup

            f.write(f"SETUP TAG: {setup_tag}\n")
            f.write("-" * 120 + "\n")

            if top5:
                top5_parts = []

                for label, count in top5:
                    pallets_above_5 = get_pallets_above_5_with_count(
                        pallet_counter[setup_tag][label]
                    )

                    top5_parts.append(
                        format_fail_with_pallets(label, count, pallets_above_5)
                    )

                f.write(", ".join(top5_parts) + ".\n")
            else:
                f.write("BRAK FAIL.\n")

            f.write(f"\nSUMA FAIL DLA SETUP TAG: {total_for_setup}\n")
            f.write("=" * 120 + "\n\n")

        f.write(f"SUMA WSZYSTKICH FAIL: {grand_total}\n")
        f.write("=" * 120 + "\n")


def print_console_summary(
    grouped_counter,
    pallet_counter,
    trend_counter,
    trend_pallet_counter,
    hot_pallet_counter
):
    print("\nWYNIK ANALIZY - WSZYSTKIE FAIL WG SETUP TAG")
    print("=" * 170)

    grand_total = 0

    for setup_tag, counter in grouped_counter.items():
        sorted_fails = counter.most_common()
        setup_total = sum(counter.values())
        grand_total += setup_total

        print(f"\nSETUP TAG: {setup_tag}")
        print("-" * 170)
        print(f"{'FAIL DESCRIPTION':<100} | {'COUNT':>6} | {'PALETKI >5 FAIL':<40}")
        print("-" * 170)

        for label, count in sorted_fails:
            pallets_above_5 = get_pallets_above_5_with_count(
                pallet_counter[setup_tag][label]
            )

            if pallets_above_5:
                pallets_text = ", ".join([f"{pallet}({qty})" for pallet, qty in pallets_above_5])
            else:
                pallets_text = ""

            print(f"{label:<100} | {count:>6} | {pallets_text:<40}")

        print("-" * 170)
        print(f"{'SUMA FAIL DLA SETUP TAG':<100} | {setup_total:>6}")
        print("-" * 170)

        print("\nTREND FAIL WG GODZINY - TOP 5:")
        trend_top5 = get_trend_top5_hours(trend_counter[setup_tag])

        if trend_top5:
            for hour_bucket, count in trend_top5:
                hour_range = format_hour_range(hour_bucket)

                top_pallets_for_hour = get_top_pallets_for_hour(
                    trend_pallet_counter[setup_tag][hour_bucket]
                )

                if top_pallets_for_hour:
                    pallets_text = ", ".join(
                        [f"{pallet}({qty})" for pallet, qty in top_pallets_for_hour]
                    )
                else:
                    pallets_text = "BRAK PALETKI"

                print(f"{hour_range} -> {count} FAIL | PALETKI: {pallets_text}")
        else:
            print("BRAK DANYCH CZASOWYCH.")

        print("\nHOT PALLETS - TOP 5:")
        hot_pallets_top5 = get_hot_pallets_top5(hot_pallet_counter[setup_tag])

        if hot_pallets_top5:
            for pallet_short, total, fail_counter in hot_pallets_top5:
                fail_parts = [
                    f"{label} {count}"
                    for label, count in fail_counter.most_common()
                ]

                print(f"{pallet_short} -> {total} FAIL | " + ", ".join(fail_parts))
        else:
            print("BRAK PALETEK >5 FAIL.")

        print("=" * 170)

    print(f"\n{'SUMA WSZYSTKICH FAIL':<100} | {grand_total:>6}")
    print("=" * 170)


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
    pallet_counter = defaultdict(lambda: defaultdict(Counter))
    trend_counter = defaultdict(Counter)
    trend_pallet_counter = defaultdict(lambda: defaultdict(Counter))
    hot_pallet_counter = defaultdict(lambda: defaultdict(Counter))

    print("Analizowane pliki:")
    for file_path in csv_files:
        print("-", file_path)

        analyze_csv_file(
            file_path,
            grouped_counter,
            pallet_counter,
            trend_counter,
            trend_pallet_counter,
            hot_pallet_counter
        )

    print_console_summary(
        grouped_counter,
        pallet_counter,
        trend_counter,
        trend_pallet_counter,
        hot_pallet_counter
    )

    exe_dir = get_exe_folder()
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    output_file = os.path.join(exe_dir, f"fail_report__{timestamp}.txt")

    write_report(output_file, grouped_counter, pallet_counter, csv_files)

    print("\nZapisano raport TXT:")
    print(output_file)

    input("\nENTER aby zamknac...")


if __name__ == "__main__":
    main()
