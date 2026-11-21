# OVERRIDE

Application personnelle d'entraînement façon « Système » LitRPG. Un Système adaptatif génère chaque soir une quête de 20 à 25 min selon ton niveau, ta récupération et ton matériel.

> **État : phase 1 (noyau jouable).** Éveil, check-in, quêtes HAUT / BAS / RECALIBRAGE, mode quête avec RIR, rapport, XP et niveaux, écran Statut, mobilité quotidienne, Docker et HTTPS Tailscale.
> À venir : progression automatique complète, patchs et épreuves de rang (phase 2), Système vivant, Donjon, pénalités (phase 3), PWA, ntfy, export, sauvegardes, Homepage (phase 4).

## Installation dans Dockge

Sur le serveur (`lgabeelink`) :

```bash
cd /opt/stacks
sudo git clone https://github.com/renaar/override.git override
cd override
sudo chown -R 1000:1000 data      # le conteneur tourne avec l'utilisateur 1000
```

Le dépôt est privé : `git clone` te demandera ton identifiant GitHub et un *personal access token* (ou utilise `gh repo clone renaar/override override`).

Puis, dans Dockge :

1. Rafraîchis la liste des stacks : **override** apparaît (Dockge lit `/opt/stacks/override/compose.yaml`).
2. Clique sur **Démarrer**. La première fois, l'image est construite (1 à 2 min sur le N150).
3. Vérifie : `http://192.168.0.23:8087/healthz` doit répondre `{"status":"ok",...}`.

Le port par défaut est **8087**. Pour en changer, crée un fichier `.env` à côté de `compose.yaml` avec `OVERRIDE_PORT=8088`.

### Ce qu'il y a dans `./data`

| Fichier | Rôle |
|---|---|
| `override.db` | ta base SQLite (toute ta progression) |
| `config.json` | XP, durées, RIR, seuils, placements de l'Éveil |
| `skills.json` | l'arbre des compétences |
| `ranks.json`, `titles.json` | épreuves de rang et titres |
| `system_messages.json` | la bibliothèque de messages du Système |

Les fichiers JSON sont modifiables. Redémarre la stack après une modification.

## Mise à jour

```bash
cd /opt/stacks/override
sudo git pull
```

Puis, dans Dockge : **Mettre à jour** (ou `docker compose up -d --build`).
Si tu as modifié un JSON de `data/`, `git pull` te le signalera : garde ta version (`git stash`, puis `git stash pop`) ou accepte la nouvelle.

## HTTPS avec Tailscale (nécessaire pour l'écran toujours allumé et, plus tard, la PWA)

Prérequis dans la console Tailscale (https://login.tailscale.com/admin/dns) :

- **MagicDNS** activé ;
- **HTTPS Certificates** activé.

Sur le serveur, lance une seule fois :

```bash
sudo tailscale serve --bg 8087
```

> Vérifie la syntaxe avec `tailscale serve --help` : elle a changé selon les versions. Avec les versions récentes, `--bg` laisse le service actif en arrière-plan et survit aux redémarrages.

Contrôle avec `tailscale serve status`. L'adresse ressemble à :

```
https://lgabeelink.<ton-tailnet>.ts.net/
```

Utilise **cette URL partout**, à la maison comme dehors : ton téléphone est dans le tailnet. Pour tout arrêter : `sudo tailscale serve reset`.

L'accès LAN `http://192.168.0.23:8087` reste possible, mais sans HTTPS : pas de maintien de l'écran allumé ni de PWA.

## Uptime Kuma

Ajoute une sonde **HTTP(s)** sur `http://192.168.0.23:8087/healthz`, avec un intervalle de 60 s et le mot-clé `ok`.

## Première soirée

1. Ouvre l'URL Tailscale sur ton téléphone.
2. L'**Éveil** démarre : nom, mensurations, matériel, jour de repos, puis 8 tests guidés (prévois 15 à 20 min, un mètre ruban et tes haltères).
3. L'Éveil compte comme ta première quête. Dès le lendemain : check-in (3 taps), puis la quête HAUT.

## Développement

```bash
pip install -r requirements-dev.txt
python -m pytest                      # tests du moteur et du service
DATA_DIR=/tmp/override-data uvicorn app.main:app --reload --port 8087
```

Le nom de l'appli se change avec la variable d'environnement `APP_NAME`.
