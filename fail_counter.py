import sys
from collections import Counter

FAIL_PATTERNS = {
    "FAIL ALIGN - (063) Align Focus Conversion Failed.  Unable to align lens within maximum number of attempts.": 
        "FAIL ALIGN (063) - Align Focus Conversion failed",

    "FAIL ALIGN - (205) Failed to compute final Z position": 
        "FAIL ALIGN (205) - Failed to compute final Z position",

    "FAIL ALIGN - Final Image Test Failed.  MTF (Could not find the required geometry in the ROI.)": 
        "FAIL ALIGN - MTF (Could not find the required geometry in the ROI.)",

    "FAIL ALIGN - Final Image Test Failed.  MTF.": 
        "FAIL ALIGN - MTF",

    "FAIL DISPENSE - (112) Unable to Detect Camera Housing": 
        "FAIL DISPENSE (112) - Unable to Detect Camera Housing",

    "FAIL DISPENSE - (128) Unable to Verify Epoxy Bead": 
        "FAIL DISPENSE (128) - The dispense bead failed the validation criteria",

    "Open Camera ExDone on Align call failed - -2094": 
        "CAMERA ALIGN -2094 Camera electronics driver: frame error",

    "Open Camera ExDone on Align call failed - -2107": 
        "CAMERA ALIGN -2107 Camera electronics driver: camera communication error",

    "Open Camera ExDone on Dispense call failed - -2094": 
        "CAMERA DISPENSE -2094 Camera electronics driver: frame error",

    "Open Camera ExDone on Dispense call failed - -2107": 
        "CAMERA DISPENSE -2107 Camera electronics driver: camera communication error",
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
    print("=" * 110)
    print(f"{'TYPE':<6} | {'FAIL DESCRIPTION':<80} | {'COUNT':>6}")
    print("-" * 110)

    total = 0
    for label, count in counter.items():
        print(f"{'CMAT':<6} | {label:<80} | {count:>6}")
        total += count

    print("-" * 110)
    print(f"{'SUMA FAIL':<90} {total:>6}")
    print("=" * 110)
    input("ENTER aby zamknac...")

if __name__ == "__main__":
    main()
