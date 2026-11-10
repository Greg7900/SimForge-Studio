# SimForge Studio

Logiciel Windows qui règle, dans une seule fenêtre :
- un **volant** à entraînement direct sur carte ODrive v3.6 avec le firmware Odrive-Wheel ;
- des **pédales actives** DIY de ChrGri (carte PCB V6, ESP32-S3, servo iSV57T), par câble ou sans fil.

Il remplace l'outil web Odrive-Wheel et, pour les réglages, le plugin SimHub des pédales.
Interface en anglais par défaut, français par le sélecteur en haut à droite.

## Installer

**Utilisateur** : télécharge `SimForge-Studio-Setup-x.y.z.exe` dans les
[Releases](https://github.com/Greg7900/SimForge-Studio/releases) et lance-le. Windows affiche « éditeur inconnu »
(l'installeur n'est pas signé) : « Informations complémentaires », puis « Exécuter quand même ».

**Depuis le code** (Python 3.9 ou plus) : double-clic sur `simforge-studio-v3/SimForge Studio V3.bat`.
Le premier lancement installe les dépendances dans `.venv`. `SimForge Studio V3 (demo).bat` lance l'appli
avec du matériel simulé, sans rien brancher.

Un seul programme peut ouvrir un port série : ferme SimHub et l'outil web Odrive-Wheel pendant que SimForge tourne.

## Utiliser

| Menu | Rôle |
|---|---|
| Vue d'ensemble | État du volant et des pédales d'un coup d'œil |
| Volant › Mise en route | Calibration pas à pas d'une carte neuve (moteur, codeur, démarrage automatique) |
| Volant › Réglages | Tous les réglages : course, couple, butées, effets, moteur, codeur, alimentation |
| Volant › Moniteur, Codeur, Force test | Courbes en direct, signaux A/B/Z du codeur, essais d'effets sans jeu |
| Pédales › Réglages | Courbe force-course, cinématique, filtre, effets, diagnostic du servo, auto-test |
| Pédales › Firmware | Flashe les pédales et le récepteur |
| Pédales › Sans fil | Appaire les pédales et le récepteur |
| Outils | Test des manettes, overlay en jeu, console de la carte, journal |

Les réglages modifiés sont en orange tant qu'ils ne sont pas envoyés. « Appliquer » les envoie sans les mémoriser ;
« Enregistrer » les garde après extinction. Exporte tes réglages (bouton Exporter) avant tout flashage.

### Pédales : les deux prises USB de l'ESP32

| Firmware (page Firmware) | Prise UART (puce CH343) | Prise USB (native) |
|---|---|---|
| Pédale active — PCB V6 (ChrGri, d'origine) | réglages et flashage | manette pour les jeux |
| PCB V6, un seul câble (version SimForge) | flashage seulement | réglages et manette |
| Récepteur sans fil | flashage | manette et appairage |

On flashe toujours par la prise **UART**. La carte V6 prend son 5 V sur la prise USB de l'ESP32 (pont « IN-OUT »
à souder sur la carte ESP32) : même en sans-fil, chaque pédale a besoin d'un câble USB d'alimentation
(chargeur) ou d'un convertisseur 36 V → 5 V.

### Pédales sans fil (ESP-NOW)

1. Flashe un ESP32-S3 DevKitC avec un firmware « Récepteur sans fil » et branche-le au PC par sa prise USB.
2. Branche chaque pédale par câble, donne-lui son rôle dans Réglages et enregistre.
3. Page Sans fil : choisis « USB (manette du récepteur) », **Détecter**, puis **Appairer**.
4. Retire les câbles de données des pédales. Elles apparaissent sous « SANS-FIL-n » et se règlent à travers
   le récepteur. Les jeux lisent les trois pédales sur la manette du récepteur.

Le rôle d'une pédale ne se change que par câble ; refais ensuite l'appairage.

### Points à connaître

- **Filtre IMM des pédales** : avec le firmware fourni, il peut bloquer la pédale en position de départ.
  Garde un filtre Kalman.
- **Codeur du volant entraîné par courroie 72/16** : rapport non entier, donc pas d'index Z (fil Z débranché,
  « Utiliser l'index Z » décoché). Le volant refait son calage à chaque allumage : laisse-le droit et lâché.
- **Module ESP32-S3 N16R8 sur la carte V6** : fonctionne, bien que ses broches 35 à 37 soient en principe
  réservées à sa mémoire.
- **Journaux d'erreur** : `errors.log` et `crash.log`, dans `simforge-studio-v3` (lancé depuis le code) ou dans
  `%LOCALAPPDATA%\SimForge Studio` (version installée).

## Publier une nouvelle version

1. Vérifie que `main` contient ce que tu veux publier.
2. Sur GitHub : **Releases › Draft a new release**, crée une étiquette `vX.Y.Z` (par exemple `v3.2.0`) sur `main`,
   puis **Publish release**.
3. L'onglet **Actions** lance « Installeur Windows » : tests, programme, installeur. En une dizaine de minutes,
   `SimForge-Studio-Setup-X.Y.Z.exe` est attaché à la version.

Pour un installeur d'essai sans publier : **Actions › Installeur Windows › Run workflow** ; il se télécharge en bas
de la page du lancement (« Artifacts »). Installer une nouvelle version par-dessus l'ancienne la remplace.

## Développer

```
pip install -r simforge-studio-v3/requirements.txt pytest ruff
python simforge-studio-v3/simforge_studio.py --demo
python -m pytest tests
ruff check --select F,E9 --line-length 120 simforge-studio-v3 tools tests
```

- `main` : versions publiées. `dev` : travail en cours ; une branche par sujet, créée depuis `dev`.
- Organisation du code et règles : [CLAUDE.md](CLAUDE.md). Détail des pages : `simforge-studio-v3/LISEZMOI.txt`.
- Firmwares fournis et leurs modifications : `simforge-studio-v3/firmware/README.txt`. Chaque version SimForge a
  son `simforge_changes.diff` à appliquer sur le dépôt de ChrGri (commit `7564dad`).

## Licence et crédits

Les firmwares des pédales et du récepteur viennent de
[ChrGri/DIY-Sim-Racing-FFB-Pedal](https://github.com/ChrGri/DIY-Sim-Racing-FFB-Pedal), sous licence
CC BY-NC-SA 4.0 : usage non commercial, mention des auteurs, partage dans les mêmes conditions
(`simforge-studio-v3/firmware/LICENSE.txt`). SimForge Studio ne doit donc pas être vendu avec ces firmwares.
