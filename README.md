# Pilot V0 — Détection et résolution autonome de congestion/blocage en réseau V2V

## Objectif
Ce dossier est un **pack de conception et d'exécution pour Codex dans VS Code**. Il ne contient pas encore le code final. Il définit exactement le mini-projet à construire localement pour vérifier la faisabilité du mémoire avant d'engager une implémentation plus lourde.

Le pilote doit démontrer, sur un trafic **structuré** simulé dans SUMO, qu'un ensemble de véhicules intelligents échangeant des informations en **V2V abstrait** peut :

1. observer l'état du trafic ;
2. détecter une congestion ou un blocage ;
3. déclencher une stratégie de résolution ;
4. modifier le comportement des véhicules via TraCI ;
5. mesurer objectivement si la situation s'améliore ;
6. comparer la méthode proposée à des baselines simples ;
7. générer automatiquement un rapport PDF de **10 pages maximum** avec figures, métriques et limites.

## Ce que le pilote NE doit PAS faire
- pas de YOLO ;
- pas de caméra ;
- pas de dataset réel obligatoire ;
- pas de CARLA ;
- pas de Veins/OMNeT++ ;
- pas de simulation radio réaliste ;
- pas de deep learning imposé ;
- pas de RL/MARL dans la V0, sauf si toutes les portes de validation sont franchies et qu'il reste du temps ;
- pas de prétention à reproduire tout un réseau urbain réel.

## Principe méthodologique
On commence par une solution **simple, explicable, mesurable et testable**. Le RL ne sera introduit que si le pilote montre que les règles simples deviennent insuffisantes sur des scénarios plus variés.

## Fichiers à lire par Codex
Dans cet ordre :

1. `SPEC.md`
2. `ARCHITECTURE.md`
3. `DECISIONS.md`
4. `EXPERIMENTS.md`
5. `METRICS.md`
6. `REPORT_SPEC.md`
7. `TASKS.md`
8. `NEXT_PHASE_RL.md`

Le prompt à envoyer à Codex est dans `CODEX_MASTER_PROMPT.txt`.

## Critère final de réussite du pilote
Le pilote est considéré réussi si :

- les 3 scénarios définis dans `EXPERIMENTS.md` sont exécutables de manière reproductible ;
- le système détecte le blocage du scénario dédié sans faux positif sur le scénario normal ;
- au moins une stratégie coopérative V2V réduit significativement le temps de récupération ou le temps d'attente par rapport à la baseline naïve ;
- toutes les métriques sont exportées en CSV/JSON ;
- les figures sont générées automatiquement ;
- le rapport PDF final est produit sans intervention manuelle et reste ≤ 10 pages ;
- les limites du pilote sont explicitement indiquées.

## Environnement recommandé
- VS Code
- Codex
- Git
- Python 3.11 ou 3.12
- SUMO + `sumo-gui`
- TraCI / sumolib

Avant de donner le prompt à Codex, vérifier dans le terminal :

```bash
python --version
sumo --version
sumo-gui --version
```

Si `sumo` n'est pas reconnu, installer SUMO avant le lancement du pilote.
