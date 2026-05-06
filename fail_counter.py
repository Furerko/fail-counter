import sys
from collections import Counter

FAIL_PATTERNS = {
    "FAIL ALIGN - (205) Failed to compute final Z position": "FAIL ALIGN (205) - Final Z position",
    "FAIL ALIGN - Final Image Test Failed.  MTF (Could not find the required geometry in the ROI.)": "FAIL ALIGN - MTF ROI",
    "FAIL ALIGN - Final Image Test Failed.  MTF.": "FAIL ALIGN - MTF",
    "FAIL DISPENSE - (112) Unable to Detect Camera Housing": "FAIL DISPENSE (112) - Camera Housing",
    "FAIL DISPENSE - (128) Unable to Verify Epoxy Bead": "FAIL DISPENSE (128) - Epoxy Bead",
    "Open Camera ExDone on Align call failed - -2094": "CAMERA ALIGN -2094 Frame error",
    "Open Camera ExDone on Align call failed - -2107": "CAMERA ALIGN -2107 Comm error",
    "Open Camera ExDone on Dispense call failed - -2094": "CAMERA DISPENSE -2094 Frame error",
    "Open Camera ExDone on Dispense call failed - -2107": "CAMERA DISPENSE -2107 Comm error",
}

def main():
    if len(sys.argv) < 2:
        print("Przeciagnij plik CSV na program.")
        input("ENTER aby wyjsc...")
        return

    csv_file = sys.argv[1]
    counter = Counter()

    with open(csv_file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            for key, label in FAIL_PATTERNS.items():
                if key in line:
                    counter[label] += 1

    print("\nPLIK:", csv_file)
    print("=" * 60)

    total = 0
    for label, count in counter.items():
        print(f"{label:<45} {count}")
        total += count

    print("=" * 60)
    print(f"SUMA FAIL: {total}")
    print("=" * 60)
    input("ENTER aby zamknac...")

if __name__ == "__main__":
    main()
