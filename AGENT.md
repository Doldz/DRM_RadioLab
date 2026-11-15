# CRITICAL RULES - MUST FOLLOW

## RESPONSES

- Keep responses concise and to the point - unless the user asks otherwise

## PLANNING MODE

- Always ask clarifying questions
- Never assume design, tech stack or features
- Use deep-dive sub-agents to assist with research
- Use deep-dive sub-agents to review the different aspects of your plan before presenting to the user

## CHANGE / EDIT MODE

- Never implement features yourself when possible - use sub-agents!
- Identify changes from the plan that can be implemented in parallel, and use sub-agents to implement the features efficiently
- When using sub-agents to implement features, act as a coordinator only
- Use the best model for the task - premium models for complex tasks (like coding) and mid-tier models for simpler tasks, like documentation
- After completing features (large or small), always run commands like lint, type check and next build to check code quality

## TESTING

- Use any testing tools, libraries available to the project for testing your changes
- Never assume your changes simply work, always test!
- If the project does not have any testing tools, scripts, MCP tools, skills, etc. available for testing, ask the user whether testing should be skipped.


# PROGETTO: DRM_RadioLab (laboratorio di strumentazione, Milano)

Radiometro total power in banda Ka (26–40 GHz): feedhorn DRM → guida WR28 → LNA ERZIA-LNA-2600-4000 → filtro 26–40 GHz → diodo rivelatore FTL-981B → multimetro. Analisi in notebook Jupyter (Python: numpy, pandas, scipy, matplotlib), commenti e markdown in **italiano**. Kernel conda `base`.

## Struttura
- `dati_calib_diodo/` – calibrazione del diodo V(ν, P) (`calib_diodo.ipynb`).
- `dati_guadagno/` – guadagno della catena ERZIA con generatore Anritsu e diodo calibrato (`guadagno_erzia.ipynb`), errore su <G> con calibrazione diodo e generatore.
- `dati_T_noise/` – temperatura di rumore e rumore 1/f (`calcolo_T_noise.ipynb`), dati in parquet (temperature dalla centralina Lake Shore 218, tensioni).
- `dati_srsr/`, `spherical_cuts/`, `progetto_graps/` – beam pattern della feedhorn (SRSR-D → spherical cut GRASP).
- `stima_tensione_uscita/` – stima della potenza/tensione attesa dal Sole.
- `README.md` – to-do list dell'esame.

## Stato T_noise (`dati_T_noise/calcolo_T_noise.ipynb`)
- Metodo scelto: **Y-factor** carico caldo (ambiente) / freddo (LN2). Il fit V(T) durante il riscaldamento dell'azoto è stato **scartato**: la sonda `temp_1` sul fondo del bagno resta a 77.4 K mentre V sale (l'azoto evapora), quindi la sonda non segue la temperatura radiometrica (χ²_rid ~ 1e4, fit a tratti tra 126 e 250 K).
- Finestre (ora locale = colonna `date`; `unix_time` è UTC, +2 h): caldo 15:00–15:12, freddo 15:22–15:40 del 17/04/2026; controllo deriva il 18/04 02:00–03:00.
- Risultato: **T_noise = 250.6 ± 4.5 K** (Y = V_H/V_C, **nessuna correzione per l'offset V0**: tolta su richiesta), errore con **solo due contributi** (scelta dell'utente): deriva di guadagno (−0.5% in ~11 h → 4.2 K) e scelta della finestra fredda (1.7 K); statistico e temperature dei carichi tolti dal bilancio.
- Sonde di temperatura: lette da una centralina **Lake Shore 218** (manuale in `../218_manual.pdf`): supporta solo diodi Si/GaAlAs e RTD (Pt100, Pt1000, Cernox, ...), **non termocoppie**; il tipo di sensore montato non è noto (Cernox escluso dal rumore a 300 K). Passo di lettura 0.001 K sotto 100 K, 0.01 K sopra. Nomi: 1 ecosorb interno fondo dx, 5 ecosorb interno fondo sx, 6 amplificatore ERZIA (~308 K), 7 estremità superiore ecosorb, 8 feedhorn; sonde 2–4 non funzionanti. Incertezza su T: strumentale dalle fluttuazioni nella finestra (residui da retta ⊕ q/√12, pochi mK) ⊕ accuratezza stimata dai dati: T_C confrontata con il punto di ebollizione di N2 a Milano (~1000 ± 15 hPa → 77.24 ± 0.13 K), T_H dalla dispersione delle sonde ambiente 1,5,7,8.
- Sezione prima dello Y-factor: solo l'andamento del segnale con T6 (ERZIA) durante l'accensione del 17/04 (~13:20:34), k = d ln G/dT6 ≈ −0.78 %/K, fit unico sui primi 20 min (nessun errore riportato: campioni autocorrelati); sonda in ritardo → limite superiore.
- Le date sono `datetime64[us]`: per interpolare usare i secondi (`DatetimeIndex.as_unit('ns').asi8/1e9`), mai `asi8` assumendo ns.
- Le date vanno lette con `pd.to_datetime(..., format='ISO8601')` (con `errors='coerce'` le righe senza frazione di secondo diventano NaT).
- Frequenza di ginocchio 1/f: f_k ≈ 1.09 Hz (atteso 0.8 Hz secondo il prof).
- Detrending per il rumore 1/f: **non spline**; si sottrae il modello termico V = c0 + c1·T6 con **solo la sonda ERZIA** (scelta dell'utente; la più correlata sui campioni singoli, ρ = −0.26), letture grezze senza smoothing, c1 ≈ −3.6 µV/K = −0.09 %/K. Aggiungere la feedhorn (T8) non serve: collineare con T6 (ρ = 0.94), f_k invariato. Spiega solo il salto del 20/04 ~07:30; il gradino del 19/04 ~10:00 non è spiegato da nessuna sonda.

## Convenzioni di analisi
- Campioni a ~0.24 s sono autocorrelati: errori sulle medie da medie a blocchi, non `std/√N` sui singoli campioni né `std` dei campioni.
- Riportare sempre un bilancio dei sistematici esplicito; non gonfiare le barre d'errore con √χ² per mascherare un modello sbagliato.
- Non inventare incertezze strumentali: se un valore è un'ipotesi, dichiararlo e chiedere.
- **Figure per la relazione LaTeX: sempre in PDF**, generate dal notebook stesso con `fig.savefig('images/<nome>.pdf', bbox_inches='tight')` (cartella `images/` accanto al notebook), così l'utente le modifica dal notebook. Mai estrarre PNG dagli output.
- Nella relazione LaTeX non citare il valore atteso di f_k (0.8 Hz).
- Testare le modifiche ai notebook eseguendoli: `jupyter nbconvert --to notebook --execute <nb> --output <tmp>`.
