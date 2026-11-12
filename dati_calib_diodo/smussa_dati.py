"""Smooth the txt measurements so they follow the shape of the Excel calibration
(../dati_guadagno/dati_potenza.xlsx).

Reads the ORIGINAL files from dati_backup/ and rewrites dati/ (safe to re-run).
Summary per frequency in smussa_riepilogo.csv.

Method, per frequency f (F_MIN..F_MAX)  -- final value blends original and curve with ALPHA:
  1. Excel shape g_f(P): cubic fit of log10(V_excel) vs P[dBm] on P >= P_MIN_EXCEL
     (below that the Excel values are noise). Below P_MIN_EXCEL the curve is continued
     with the local slope at P_MIN_EXCEL (straight line in semilog = square-law region).
     Frequencies not in the Excel use the mean shape of all Excel frequencies.
  2. Level: LIVELLO='misure' -> one offset D_f = weighted mean of (log10|V_txt| - g_f(P))
     over the non-noisy txt points (sigma/|V| <= SOGLIA_REL), weights 1/max(rel,REL_FLOOR)^2.
     LIVELLO='excel' -> D_f = 0 (curves exactly at the Excel level).
  3. Smoothed value: log10|V| = (1-a) log10|V_orig| + a (g_f(P) + D_f), a = ALPHA (1 for noisy points).
  4. Error: |V| * median sigma/|V| of the valid txt points of that frequency
     (REL_MIN_VALIDO < rel <= SOGLIA_REL).
Frequencies outside F_MIN..F_MAX (20, 48, 50 GHz) are copied unchanged.
"""
from pathlib import Path
import shutil
import numpy as np
import pandas as pd

ALPHA = 0.8           # smoothing strength: 0 = original data, 1 = fully on the Excel-shaped curve
                        # (blend in log space; noisy points, sigma/|V| > SOGLIA_REL, always use 1)
LIVELLO = 'misure'      # 'misure' = keep measured level, 'excel' = use Excel level
F_MIN, F_MAX = 22, 46   # frequencies to smooth [GHz]
P_MIN_EXCEL = -20       # Excel reliable only for P >= this [dBm]
GRADO = 3               # polynomial degree for the Excel shape (log10 V vs dBm)
SOGLIA_REL = 0.25       # txt points with sigma/|V| above this are ignored when fitting the level
REL_FLOOR = 0.05        # minimum relative error used in the weights
REL_MIN_VALIDO = 1e-3   # sigma~0 points ignored for the error estimate

base = Path(__file__).resolve().parent
dir_backup, dir_dati = base / 'dati_backup', base / 'dati'

raw = pd.read_excel(base.parent / 'dati_guadagno' / 'dati_potenza.xlsx', header=None)
excel = pd.DataFrame(raw.iloc[3:, 2:].astype(float).values,
                     index=raw.iloc[3:, 0].astype(int).values,
                     columns=raw.iloc[2, 2:].astype(float).values).sort_index()
ex = excel[excel.index >= P_MIN_EXCEL]
Pex = ex.index.values.astype(float)

coef = {f: np.polyfit(Pex, np.log10(ex[f].values), GRADO) for f in ex.columns}
coef_medio = np.mean(list(coef.values()), axis=0)


def forma(c, P):
    """log10 V of the Excel shape; straight-line continuation below P_MIN_EXCEL."""
    P = np.asarray(P, float)
    pend = np.polyval(np.polyder(c), P_MIN_EXCEL)
    return np.where(P >= P_MIN_EXCEL, np.polyval(c, P),
                    np.polyval(c, P_MIN_EXCEL) + pend * (P - P_MIN_EXCEL))


riepilogo = []
for fp in sorted(dir_backup.glob('DRM_diodo_*.txt'), key=lambda p: int(p.stem.split('_')[2])):
    f = int(fp.stem.split('_')[2])
    if not (F_MIN <= f <= F_MAX):
        shutil.copy2(fp, dir_dati / fp.name)
        continue

    testo = fp.read_bytes().decode()
    eol = '\r\n' if '\r\n' in testo else '\n'
    righe = testo.splitlines()
    df = pd.read_csv(fp, sep='\t', header=None, names=['P', 'V', 'sV', 'n'])
    P = df['P'].values.astype(float)
    absV = df['V'].abs().values * 1e3          # mV, same unit as the Excel
    rel = df['sV'].values / df['V'].abs().values   # relative error (unit independent)
    buoni = rel <= SOGLIA_REL

    c = coef.get(float(f), coef_medio)
    g = forma(c, P)
    if LIVELLO == 'excel':
        D, sD = 0.0, 0.0
    else:
        w = 1 / np.maximum(rel[buoni], REL_FLOOR) ** 2
        D = np.sum(w * (np.log10(absV[buoni]) - g[buoni])) / np.sum(w)
        sD = 1 / np.sqrt(np.sum(w * np.log(10) ** 2))
    alpha = np.where(buoni, ALPHA, 1.0)        # noisy points go fully to the curve
    logV_new = (1 - alpha) * np.log10(absV) + alpha * (g + D)
    V_new = -10 ** logV_new * 1e-3             # back to V, as in the txt
    rel_err = float(np.median(rel[buoni & (rel > REL_MIN_VALIDO)]))
    sV_new = np.abs(V_new) * rel_err

    res_dB = 10 * (np.log10(absV) - (g + D))
    riepilogo.append(dict(f_GHz=f, forma='excel %g GHz' % f if float(f) in coef else 'excel media',
                          offset_dB=10 * D, err_offset_dB=10 * sD, rel_err=rel_err,
                          scarto_rms_dB=float(np.sqrt(np.mean(res_dB[buoni] ** 2)))))
    for i in range(len(df)):
        campi = righe[i].split('\t')
        campi[1], campi[2] = repr(float(V_new[i])), repr(float(sV_new[i]))
        righe[i] = '\t'.join(campi)
    (dir_dati / fp.name).write_bytes((eol.join(righe) + eol).encode())

riepilogo = pd.DataFrame(riepilogo)
riepilogo.to_csv(base / 'smussa_riepilogo.csv', index=False)
print(f'Smoothed {len(riepilogo)} frequencies ({F_MIN}-{F_MAX} GHz), alpha = {ALPHA}, level = {LIVELLO}\n')
print(riepilogo.round(3).to_string(index=False))
