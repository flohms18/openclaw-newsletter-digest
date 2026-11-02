# OpenClaw Newsletter Digest

Chaque matin, un agent [OpenClaw](https://github.com/openclaw/openclaw) lit les newsletters d'un dossier Outlook
(via Microsoft Graph, **en lecture seule**), les résume et envoie la note sur WhatsApp.

## Contenu

| Fichier | Rôle |
|---|---|
| `graph_mail.py` | Connexion Microsoft (device code) et lecture des e-mails d'un dossier Outlook |
| `PROMPT.md` | Instructions de l'automatisation OpenClaw (lecture, résumé, envoi WhatsApp) |
| `requirements.txt` | Dépendances Python (`msal`, `requests`) |

## Installation

```bash
git clone https://github.com/<ton-pseudo>/openclaw-newsletter-digest.git ~/openclaw-newsletter-digest
cd ~/openclaw-newsletter-digest
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

## Connexion à Outlook (une seule fois)

```bash
./venv/bin/python graph_mail.py login
```

Ouvre https://www.microsoft.com/link, saisis le code affiché et accepte.
Seule la permission `Mail.Read` (lecture seule) est demandée. Le jeton est stocké dans `token_cache.json`
(permissions 600, **jamais versionné**).

Le script utilise l'identifiant public de « Microsoft Graph Command Line Tools » et l'autorité `consumers`
(comptes Outlook.com personnels). Pour un compte pro/école, remplace `AUTHORITY` par
`https://login.microsoftonline.com/organizations`.

## Utilisation

```bash
./venv/bin/python graph_mail.py folders          # liste les dossiers
./venv/bin/python graph_mail.py newsletters 7    # e-mails des 7 derniers jours (JSON)
```

Le dossier lu est `AI & Business Newsletter` par défaut ; change-le avec la variable `NEWSLETTER_FOLDER`.

## Automatisation OpenClaw

Crée une automatisation `agentTurn` planifiée (ex. `0 8 * * *`, `Europe/Paris`, livraison `none`)
avec le contenu de `PROMPT.md`, en remplaçant `<WHATSAPP_TARGET>` par ton numéro.

Le Mac doit être allumé : si la machine dort à l'heure prévue, l'exécution est rattrapée au réveil.

## Révoquer l'accès

account.microsoft.com → Confidentialité → Applications et services → « Microsoft Graph Command Line Tools ».
