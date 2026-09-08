# Pilote V0 — congestion et deadlock avec SUMO / V2V

Ce dépôt exécute une boucle réelle **observation → V2V → détection → décision →
commande TraCI → réévaluation** sur un carrefour à quatre branches. Méthodes :
NaiveYield, FCFS et CooperativeV2VResolver. Aucun RL/MARL, vision, CARLA ou radio
réaliste. Tous les seuils YAML sont des hypothèses du pilote.

Voir [TASKS.md](TASKS.md) pour les Gates et [le guide détaillé](docs/USER_GUIDE.md)
pour vos propres simulations et tests. Le README de conception est conservé dans
`docs/README_ORIGINAL.md` ; les autres spécifications sont à la racine et dans `docs/`.

## Environnement validé

- Ubuntu 24.04 sous WSL2/WSLg, sur la machine Windows locale.
- Python 3.12.3, SUMO/TraCI/sumolib 1.27.1.
- Environnement Linux : `~/.venvs/traffic-conflict-pilot`.
- Sources et résultats dans ce dépôt Windows.
- Les binaires SUMO Windows sont bloqués par Smart App Control ; utiliser WSL
  sur cette machine. Aucune protection Windows n'a été modifiée.
- Dépendances : `requirements.txt` ; versions installées au diagnostic dans
  `requirements-linux.lock.txt` et `requirements-windows.lock.txt`.

## Installation et tests depuis PowerShell

Ouvrir le terminal PowerShell de VS Code à la racine du dépôt :

```powershell
Set-Location 'C:\Users\Judicael Makwiza\OneDrive\Documents\traffic-conflict-pilot\traffic_conflict_pilot_pack'
wsl.exe -d Ubuntu --exec bash scripts/setup_wsl.sh
wsl.exe -d Ubuntu --exec bash scripts/python_wsl.sh scripts/doctor.py
wsl.exe -d Ubuntu --exec bash scripts/python_wsl.sh -m pytest -q
```

Le setup crée/réutilise l'environnement, installe les paquets et vérifie un pas
TraCI réel. Si la machine est déjà préparée, diagnostic et tests suffisent.
Aucune activation manuelle de `.venv` n'est nécessaire avec ces commandes.

## Construire les trois scénarios

```powershell
wsl.exe -d Ubuntu --exec bash scripts/python_wsl.sh scripts/build_scenarios.py --scenario S0 --seed 1
wsl.exe -d Ubuntu --exec bash scripts/python_wsl.sh scripts/build_scenarios.py --scenario S1 --seed 1
wsl.exe -d Ubuntu --exec bash scripts/python_wsl.sh scripts/build_scenarios.py --scenario S2 --seed 1
```

Sorties : `scenarios/normal/seed_001/`, `scenarios/deadlock/seed_001/`,
`scenarios/congestion/seed_001/`. Chaque run reconstruit aussi ses entrées dans
son propre sous-dossier `scenario/` afin de rester autonome.

## Reproduire chaque configuration

Les commandes suivantes remplacent explicitement la seed 1 officielle. Pour
conserver les résultats de référence, choisir un autre `--output-dir`.

```powershell
wsl.exe -d Ubuntu --exec bash scripts/python_wsl.sh scripts/run_experiment.py --scenario S0 --method fcfs --seed 1 --overwrite
wsl.exe -d Ubuntu --exec bash scripts/python_wsl.sh scripts/run_experiment.py --scenario S0 --method cooperative --seed 1 --overwrite
wsl.exe -d Ubuntu --exec bash scripts/python_wsl.sh scripts/run_experiment.py --scenario S1 --method naive --seed 1 --overwrite
wsl.exe -d Ubuntu --exec bash scripts/python_wsl.sh scripts/run_experiment.py --scenario S1 --method fcfs --seed 1 --overwrite
wsl.exe -d Ubuntu --exec bash scripts/python_wsl.sh scripts/run_experiment.py --scenario S1 --method cooperative --seed 1 --overwrite
wsl.exe -d Ubuntu --exec bash scripts/python_wsl.sh scripts/run_experiment.py --scenario S2 --method fcfs --seed 1 --overwrite
wsl.exe -d Ubuntu --exec bash scripts/python_wsl.sh scripts/run_experiment.py --scenario S2 --method cooperative --seed 1 --overwrite
```

Changer la seed de 1 à 10 pour reproduire chaque répétition. Dossier par défaut :
`outputs/runs/<scénario_nom>/<méthode>/seed_XXX/`. Sans `--overwrite`, un résultat
existant est protégé contre un remplacement involontaire.

## Refaire la matrice complète puis le rapport

```powershell
wsl.exe -d Ubuntu --exec bash scripts/python_wsl.sh scripts/run_matrix.py --jobs 2 --overwrite
wsl.exe -d Ubuntu --exec bash scripts/python_wsl.sh scripts/generate_report.py
```

La matrice comprend 7 configurations × seeds `[1,2,3,4,5,6,7,8,9,10]`, soit 70 runs.
`--jobs 1` permet l'exécution séquentielle. Les essais de développement et le mode
`observe` sont exclus des agrégats finaux. L'échec de récupération NaiveYield S1
est un résultat attendu de la baseline et reste visible.

Sorties : `outputs/aggregated/run_metrics.csv` (par run),
`outputs/aggregated/aggregated_metrics.csv` (moyenne, médiane, écart-type échantillon,
min/max et effectif par métrique), `outputs/figures/` et `reports/pilot_report.pdf`
(10 pages maximum). `outputs/runs/matrix_manifest.json` conserve seeds, commit,
empreinte du code et empreintes des résumés.

Après remplacement d'un résultat officiel, relancer toute la matrice puis le
rapport pour conserver un manifeste cohérent. Pour les essais personnels,
utiliser `outputs/custom/`.

## SUMO GUI facultatif

```powershell
wsl.exe -d Ubuntu --exec bash scripts/python_wsl.sh scripts/run_experiment.py --scenario S1 --method cooperative --seed 42 --gui --output-dir outputs/custom/gui_s1
```

Cette commande garde le contrôleur Python actif. Ouvrir seulement un `.sumocfg`
dans sumo-gui n'exécute pas la stratégie V2V. Les expériences finales sont headless ;
les snapshots matplotlib proviennent des positions CSV.

## Interprétation et limites

Chaque run contient configuration, provenance, XML SUMO, trajectoires, états
agrégés, événements, détails de trajets et résumés CSV/JSON.

- L'attente Python inclut les arrêts programmés ; l'attente native SUMO reste séparée.
- L'attente moyenne principale porte sur les terminés. Les inachevés ont des
  observations censurées ; une valeur absente n'est jamais remplacée par zéro.
- FCFS prévient le deadlock S1 : récupération N/A. Naive sans récupération :
  valeur censurée à l'horizon, récupération N/A.
- Collision, téléportation ou erreur de contrôle invalident le run.
- L'équité principale est N/A si toute la demande n'est pas terminée.
- Le débit utilise l'horizon complet : deux méthodes terminant toute la même
  demande ont le même débit global. Les courbes cumulées montrent le vidage du réseau.

Le pilote émule l'arbitrage commun en Python à partir des messages V2V parfaits.
Il ne valide ni consensus distribué, ni radio réelle, ni généralisation. Sans
ablation, le gain de la politique ne démontre pas séparément le gain causal du V2V.

## Autre machine Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install --no-deps -e .
python scripts/doctor.py
python -m pytest -q
python scripts/run_matrix.py --jobs 2
python scripts/generate_report.py
```

Les scripts sont également portables vers Windows si sa politique autorise les
binaires officiels. Toujours vérifier `doctor.py` avant les simulations.
