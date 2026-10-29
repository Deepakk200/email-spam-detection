"""Fail (exit 1) if README.md disagrees with results/metrics.json / results/cv_results.csv,
contains hand-typed metrics outside the generated block, or says "email" outside Limitations / Next steps.

Usage: python scripts/check_consistency.py
"""
import re
import sys

from make_readme import CV_METRICS, END, README, START, TEST_METRICS, f4, load, render

errors = []
readme = README.read_text(encoding="utf-8")
metrics, cv = load()
head, rest = readme.split(START, 1)
block, tail = rest.split(END, 1)
block = block.strip("\n")

# 1. The generated block must be exactly what the sources produce today.
if block != render(metrics, cv):
    errors.append("Results block is stale: re-run scripts/make_readme.py")

# 2. Independent check: every number in the CV and test tables matches the sources.
rows = {line.split("|")[1].strip(): line for line in block.splitlines() if line.startswith("| ")}
num = re.compile(r"\d+\.\d+|\d+")
for r in cv:
    expected = [f4(r[f"{m}_{s}"]) for m, _ in CV_METRICS for s in ("mean", "std")]
    found = num.findall(rows.get(r["model"], ""))
    if found != expected:
        errors.append(f"CV row {r['model']}: README {found} != sources {expected}")
for key, label in [("default_threshold", "default"), ("tuned_threshold", "tuned")]:
    t = metrics["test_metrics"][key]
    cm = t["confusion_matrix"]
    expected = [f4(t[m]) for m, _ in TEST_METRICS] + [str(cm[k]) for k in ("tn", "fp", "fn", "tp")]
    found = num.findall(rows.get(label, ""))
    if found != expected:
        errors.append(f"Test row {label}: README {found} != sources {expected}")

# 3. No hand-typed metrics (decimals or percentages) outside the generated block.
for line in (head + tail).splitlines():
    if re.search(r"\d+\.\d+|\d+\s*%", line):
        errors.append(f"Number outside generated block: {line!r}")

# 4. "email" only inside the Limitations and Next steps sections.
section = ""
for line in readme.splitlines():
    if line.startswith("## "):
        section = line[3:].strip().lower()
    if re.search(r"e-?mail", line, re.I) and section not in ("limitations", "next steps"):
        errors.append(f"'email' outside Limitations/Next steps (section '{section}'): {line!r}")

if errors:
    print("FAIL")
    print("\n".join(f"- {e}" for e in errors))
    sys.exit(1)
print(f"OK: README matches metrics.json and cv_results.csv ({len(cv)} CV rows, 2 test rows checked)")
