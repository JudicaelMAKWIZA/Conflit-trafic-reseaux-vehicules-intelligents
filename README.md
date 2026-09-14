# Système Autonome de Détection et de résolution des conflits dans un réseaux de vehicules intelligents

Ce projet constitue la version **expérimentale** d'un système autonome de détection et de résolution des conflits routiers dans un réseau de véhicules intelligents.

Cette version valide la faisabilité technique d'une boucle complète :

```text
SUMO
→ observation du trafic
→ échange V2V abstrait
→ détection de l'état du trafic
→ décision de résolution
→ commande TraCI
→ réévaluation
```

Les stratégies actuellement disponibles sont :

* `NaiveYield` ;
* `FCFS` ;
* `CooperativeV2VResolver`.


## Prérequis

Environnement :

* Python 3.12 ;
* SUMO ;
* TraCI / sumolib ;
* Ubuntu / WSL2.

Les dépendances Python sont définies dans :

```text
requirements.txt
requirements-linux.lock.txt
requirements-windows.lock.txt
```

## Structure

```text
configs/       configurations expérimentales
scenarios/     scénarios SUMO reproductibles
scripts/       outils de construction, exécution et validation
src/           code source principal
tests/         tests unitaires et d'intégration
README.md      documentation
```

## Installation sous WSL

Depuis la racine du projet :

```bash
bash scripts/setup_wsl.sh
bash scripts/python_wsl.sh scripts/doctor.py
bash scripts/python_wsl.sh -m pytest -q
```

Le script `doctor.py` vérifie notamment que Python, SUMO et TraCI fonctionnent correctement avant le lancement des expériences.

## Tests

Pour lancer l'ensemble des tests :

```bash
bash scripts/python_wsl.sh -m pytest -q
```

Le projet contient des tests unitaires ainsi que des tests d'intégration couvrant notamment les scénarios S0, S1 et S2.

## Scénarios disponibles

### S0 — Trafic normal

Scénario de contrôle destiné à vérifier que le système ne détecte pas abusivement un deadlock dans une circulation normale.

### S1 — Deadlock contrôlé

Scénario expérimental construit pour provoquer une situation d'attente mutuelle et tester :

* sa détection ;
* son maintien ;
* sa résolution par les différentes stratégies.

Le blocage dans cette première version est volontairement contrôlé et ne représente pas encore un deadlock géométrique spontané complet.

### S2 — Congestion soutenue

Scénario de forte demande destiné à provoquer une congestion durable et à comparer les stratégies de régulation.

## Construction des scénarios

```bash
bash scripts/python_wsl.sh scripts/build_scenarios.py --scenario S0 --seed 1
bash scripts/python_wsl.sh scripts/build_scenarios.py --scenario S1 --seed 1
bash scripts/python_wsl.sh scripts/build_scenarios.py --scenario S2 --seed 1
```

Les scénarios construits sont enregistrés sous :

```text
scenarios/normal/
scenarios/deadlock/
scenarios/congestion/
```

## Exécuter une expérience

Exemples :

```bash
bash scripts/python_wsl.sh scripts/run_experiment.py --scenario S0 --method fcfs --seed 1 --overwrite

bash scripts/python_wsl.sh scripts/run_experiment.py --scenario S0 --method cooperative --seed 1 --overwrite

bash scripts/python_wsl.sh scripts/run_experiment.py --scenario S1 --method naive --seed 1 --overwrite

bash scripts/python_wsl.sh scripts/run_experiment.py --scenario S1 --method fcfs --seed 1 --overwrite

bash scripts/python_wsl.sh scripts/run_experiment.py --scenario S1 --method cooperative --seed 1 --overwrite

bash scripts/python_wsl.sh scripts/run_experiment.py --scenario S2 --method fcfs --seed 1 --overwrite

bash scripts/python_wsl.sh scripts/run_experiment.py --scenario S2 --method cooperative --seed 1 --overwrite
```

## SUMO GUI

Une expérience peut être observée avec l'interface graphique SUMO :

```bash
bash scripts/python_wsl.sh scripts/run_experiment.py \
  --scenario S1 \
  --method cooperative \
  --seed 42 \
  --gui \
  --gui-delay 200 \
  --output-dir outputs/custom/gui_s1
```

## Métriques principales

La version experimentale mesure notamment :

* temps d'attente ;
* temps de trajet ;
* débit ;
* vitesse moyenne ;
* longueur des files ;
* durée de congestion ;
* latence de détection ;
* temps de récupération ;
* collisions ;
* téléportations ;
* équité entre approches.

Les résultats sont calculés automatiquement pendant les campagnes expérimentales.

## Limites 

Cette version repose encore sur plusieurs hypothèses simplificatrices :

* communication V2V abstraite et parfaite ;
* vue commune reconstruite en Python ;
* une géométrie de carrefour limitée ;
* véhicules intelligents homogènes ;
* seuils de congestion heuristiques ;
* deadlock S1 volontairement contrôlé ;
* absence de communication radio réelle ;
* absence de trafic humain réaliste ;
* absence de validation sur réseau routier réel.

## Évolution du projet

A suivre


