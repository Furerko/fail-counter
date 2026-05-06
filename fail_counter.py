import sys
from collections import Counter

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

def main():
    if len(sys.argv) < 2:
        print("Przeciagnij plik CSV na program.")
        input("ENTER aby wyjsc...")
        return

    csv_file = sys.argv[1]
    counter = Counter()

    # --- CZYTANIE CSV ---
    with open(csv_file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            for key, label in FAIL_PATTERNS.items():
                if key in line:
                    counter[label] += 1

    # --- SORTOWANIE I TOP 5 ---
    sorted_fails = counter.most_common()
    top5 = sorted_fails[:5]

    # --- WYŚWIETLANIE WSZYSTKICH FAIL ---
    print("\nPLIK:", csv_file)
    print("=" * 120)
    print(f"{'TYPE':<6} | {'FAIL DESCRIPTION':<90} | {'COUNT':>6}")
    print("-" * 120)

    total = 0
    for label, count in sorted_fails:
        print(f"{'CMAT':<6} | {label:<90} | {count:>6}")
        total += count

    print("-" * 120)
    print(f"{'SUMA FAIL':<100} {total:>6}")
    print("=" * 120)

    # --- ZAPIS TOP 5 DO NOTATNIKA ---
    with open("top5_fail.txt", "w", encoding="utf-8") as f:
        f.write("TOP 5 FAIL\n")
        f.write("PLIK: " + csv_file + "\n")
        f.write("=" * 100 + "\n\n")

        for i, (label, count) in enumerate(top5, start=1):
            code = label.split("(")[1].split(")")[0] if "(" in label and ")" in label else "----"
            f.write(f"{i}. [{code:4}] {label:<75} {count:>5}\n")

        f.write("\n" + "=" * 100 + "\n")
        f.write(f"SUMA TOP 5: {sum(c for _, c in top5)}\n")

    print("\nZapisano plik: top5_fail.txt")
    input("ENTER aby zamknac...")

if __name__ == "__main__":
    main()
