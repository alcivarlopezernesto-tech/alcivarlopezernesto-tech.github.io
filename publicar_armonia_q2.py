#!/usr/bin/env python3
import datetime, shutil, subprocess
from pathlib import Path
S = Path(__file__).resolve().parent
PED = S.parent / "cadenza_pedagogy" / "content"

NIV = {"armonia_i": 1, "armonia_ii": 2, "armonia_iii": 3}
Q2 = ["q2", "ud2b", "ud3", "ud5b", "ud6", "ud8b"]
DEST = S / "estatico" / "pdf" / "armonia"

def main():
    m = datetime.date.today().month
    if m not in (1, 2, 3, 4, 5, 6):
        return None
    nuevos = []
    for nivel, n in NIV.items():
        for u in Q2:
            dst = DEST / ("armonia-%d-guia-%s.pdf" % (n, u))
            if dst.exists():
                continue
            src = list((PED / nivel / "2026-2027" / "guias" / "version_autor").glob("*_%s_2026-2027.pdf" % u))
            if src:
                shutil.copy2(src[0], dst)
                nuevos.append(dst.name)
    if not nuevos:
        return []
    for cmd in (["python3", "build.py"], ["python3", "verificar_sitio.py"]):
        subprocess.run(cmd, cwd=S, check=True, capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=S, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "Armonía: guías del segundo quimestre"], cwd=S, check=True)
    return nuevos

if __name__ == "__main__":
    r = main()
    if r is None:
        pass  # sin ruido hasta febrero
    elif not r:
        print("Armonía: las guías del segundo quimestre ya estaban publicadas.")
    else:
        print("Armonía: publicadas %d guías del segundo quimestre: %s" % (len(r), ", ".join(r)))
