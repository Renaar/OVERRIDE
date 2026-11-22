# OVERRIDE

Application personnelle d'entraînement façon « Système » LitRPG. Un Système adaptatif génère chaque soir une quête de 20 à 25 min selon ton niveau, ta récupération et ton matériel.

> **État : phase 1 (noyau jouable).** Éveil, check-in, quêtes HAUT / BAS / RECALIBRAGE, mode quête avec RIR, rapport, XP et niveaux, écran Statut, mobilité quotidienne, Docker et HTTPS Tailscale.
> À venir : progression automatique complète, patchs et épreuves de rang (phase 2), Système vivant, Donjon, pénalités (phase 3), PWA, ntfy, export, sauvegardes, Homepage (phase 4).

## Installation dans Dockge

L'image est construite par GitHub à chaque mise à jour du code et publiée sur `ghcr.io/renaar/override`. Aucun code n'est nécessaire sur le serveur.

### Une seule fois : autoriser le serveur à télécharger l'image

Le dépôt est privé, donc l'image l'est aussi.

1. Sur GitHub : **Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token**, avec la seule case **`read:packages`**.
2. Sur le serveur :

```bash
sudo docker login ghcr.io -u renaar
# mot de passe : colle le token
```

### Créer la stack

1. Dans Dockge : **+ Composer**, nom de la stack : `override`.
2. Colle le contenu de [`compose.yaml`](compose.yaml).
3. Clique sur **Déployer**.
4. Vérifie : `http://192.168.0.23:8087/healthz` doit répondre `{"status":"ok",...}`.

Le dossier `/opt/stacks/override/data` est créé automatiquement, avec les bons droits.

Réglages facultatifs, dans le `.env` de la stack (éditable dans Dockge) :

| Variable | Défaut | Rôle |
|---|---|---|
| `OVERRIDE_PORT` | `8087` | port sur le serveur |
| `OVERRIDE_TAG` | `latest` | version de l'image (`latest` = branche `main`) |

### Ce qu'il y a dans `./data`

| Fichier | Rôle |
|---|---|
| `override.db` | ta base SQLite (toute ta progression) |
| `config.json` | XP, durées, RIR, seuils, placements de l'Éveil |
| `skills.json` | l'arbre des compétences |
| `ranks.json`, `titles.json` | épreuves de rang et titres |
| `system_messages.json` | la bibliothèque de messages du Système |

Ces fichiers sont installés au premier démarrage, puis **mis à jour automatiquement** à chaque nouvelle version, tant que tu ne les as pas modifiés.

- Si tu modifies un fichier (redémarre la stack ensuite), ta version est conservée. La nouvelle version officielle est alors déposée à côté sous le nom `<fichier>.nouveau.json`, pour que tu puisses comparer.
- Pour revenir à la version officielle, supprime ton fichier et redémarre.

## Mise à jour

Dans Dockge, ouvre la stack et clique sur **Mettre à jour** : la dernière image est téléchargée et le conteneur redémarre. Ta progression reste dans `./data`.

## HTTPS avec Tailscale (nécessaire pour l'écran toujours allumé et, plus tard, la PWA)

Prérequis dans la console Tailscale (https://login.tailscale.com/admin/dns) :

- **MagicDNS** activé ;
- **HTTPS Certificates** activé.

OVERRIDE utilise son **propre port HTTPS, 8443**, pour ne pas prendre l'adresse principale (`:443`), déjà utilisée par Actual Budget. Sur le serveur, lance une seule fois :

```bash
sudo tailscale serve --bg --https=8443 8087
```

> ⚠ Ne lance pas `tailscale serve --bg 8087` sans `--https=8443` : cette forme remplace ce qui est servi sur l'adresse principale (ici Actual Budget).
> Vérifie la syntaxe avec `tailscale serve --help` : elle a changé selon les versions. `--bg` laisse le service actif en arrière-plan et survit aux redémarrages.

Contrôle avec `tailscale serve status`. L'adresse d'OVERRIDE est :

```
https://lgabeelink.tailab1c70.ts.net:8443/
```

Utilise **cette URL partout**, à la maison comme dehors : ton téléphone est dans le tailnet. Pour arrêter : `sudo tailscale serve --https=8443 off`.

L'accès LAN `http://192.168.0.23:8087` reste possible, mais sans HTTPS : pas de maintien de l'écran allumé ni de PWA.

## Uptime Kuma

Ajoute une sonde **HTTP(s)** sur `http://192.168.0.23:8087/healthz`, avec un intervalle de 60 s et le mot-clé `ok`.

## Première soirée

1. Ouvre l'URL Tailscale sur ton téléphone.
2. L'**Éveil** démarre : nom, mensurations, matériel, jour de repos, puis 8 tests guidés (prévois 15 à 20 min, un mètre ruban et tes haltères).
3. L'Éveil compte comme ta première quête. Dès le lendemain : check-in (3 taps), puis la quête HAUT.

## Développement

```bash
docker build -t ghcr.io/renaar/override:latest .   # image locale, sans passer par GitHub
pip install -r requirements-dev.txt
python -m pytest                      # tests du moteur et du service
DATA_DIR=/tmp/override-data uvicorn app.main:app --reload --port 8087
```

Le nom de l'appli se change avec la variable d'environnement `APP_NAME`.
