import sys
import os
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

    # --- ŚCIEŻKA WYJŚCIA: TAM GDZIE CSV ---
    output_path = os.path.join(os.path.dirname(csv_file), "top5_fail.txt")

    # --- ZAPIS TOP 5 DO JEDNEJ LINII ---
    with open(output_path, "w", encoding="utf-8") as f:
        parts = []
        for label, count in top5:
            parts.append(f"{label} {count}")
        f.write(", ".join(parts) + ".")

    print(f"\nZapisano plik:\n{output_path}")
    input("ENTER aby zamknac...")

if __name__ == "__main__":
    main()
