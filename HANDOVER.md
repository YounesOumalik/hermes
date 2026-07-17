# ProdServeur — Handover & Procédure d'amorçage SSH

> Document de référence pour le **nouveau VPS Contabo** provisionné le 2026-07-16.
> Identifiant Contabo : `vmi3445841` · IP publique : `169.58.30.70` · Nom d'affichage : `ProdServeur`.

---

## 1. État actuel (TL;DR)

| Élément | Valeur |
|---|---|
| Provider | Contabo Cloud VPS 4 (2026), **sans configuration** |
| Hostname (Contabo) | `vmi3445841.contaboserver.net` |
| IP publique | `169.58.30.70` |
| Reverse DNS | `vmi3445841.contaboserver.net` |
| OS (livré) | Ubuntu 22.04 LTS (kernel `6.8.0-124-generic`) |
| Disque | `/dev/sda1` 96 GiB (2.2 GiB utilisés, 94 GiB libres) |
| RAM | 7.8 GiB (6.3 GiB libres au boot) |
| User SSH | `younes` (créé manuellement — Contabo ne livre **que** `root`) |
| Sudo | ✅ dans groupe `sudo` (avec mot de passe, pas NOPASSWD) |
| Auth SSH | ✅ **Opérationnelle par clé** depuis 2026-07-16 |
| Réseau | ✅ Port 22 ouvert, ping OK (~75 ms depuis ce poste) |
| Host key serveur | ED25519 `SHA256:zxROApKMji1lsawEfFxqiBTi98v9qZQd3fY33KExNiI` |

---

## 2. Pourquoi la connexion SSH échoue pour l'instant

Contabo livre les VPS **"sans configuration"** depuis le panel :
- Aucun utilisateur `younes` n'est créé à la livraison, seul `root` existe avec un mot de passe aléatoire.
- `~root/.ssh/authorized_keys` est vide.
- L'auth par clé publique est donc impossible tant qu'aucune clé publique n'a été injectée côté serveur.

C'est exactement ce que confirment nos tests :

```text
$ ssh younes@169.58.30.70
younes@169.58.30.70: Permission denied (publickey,password)

$ ssh root@169.58.30.70
# → utilisera le mdp du panel si tu l'as encore
```

---

## 3. Procédure recommandée (par ordre de préférence)

### Option A — Onglet **SSH-Key** du panel Contabo (la plus propre)

1. Ouvre le panel Contabo → section **Serveurs & Hébergement**.
2. Sélectionne `vmi3445841 (ProdServeur)`.
3. Bouton **Réinitialiser les informations d'identification** (visible sur la capture).
4. Bascule sur l'onglet **SSH-Key** (à droite de "Mot de passe").
5. Colle le contenu de ta clé publique :
   ```bash
   cat ~/.ssh/id_smartserveur.pub
   # → ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKt0iH4Q/zeCwV6dL04wk3XEzN4YEQi8ZMvRimJwneUB smartserveur-younes-ista-mrirt
   ```
6. Confirme → attends ~30 s que le serveur propage la clé.
7. Lance :
   ```bash
   cd ~/Documents/ProdServeur
   ./scripts/test-connection.sh
   ```

### Option B — Connexion `root` initiale puis injection manuelle

Si tu retrouves le mot de passe root envoyé par mail à la création :

```bash
# 1. Installer sshpass (si pas déjà fait)
sudo apt install -y sshpass

# 2. Login root avec le mdp du panel
ssh root@169.58.30.70

# 3. Sur le serveur :
useradd -m -s /bin/bash younes            # si l'user n'existe pas
mkdir -p /home/younes/.ssh
echo "$(cat ~/.ssh/id_smartserveur.pub)" >> /home/younes/.ssh/authorized_keys
chown -R younes:younes /home/younes/.ssh
chmod 700 /home/younes/.ssh
chmod 600 /home/younes/.ssh/authorized_keys

# 4. Vérifier que PasswordAuth est encore autorisé (sinon désactiver après test)
grep -i "^PasswordAuthentication" /etc/ssh/sshd_config
```

### Option C — Automatisée via `bootstrap.sh`

Le script `scripts/bootstrap.sh` encapsule l'option A ou B :

```bash
cd ~/Documents/ProdServeur
./scripts/bootstrap.sh                    # affiche la clé + instructions
SSH_PASSWORD='ton_mdp_panel' ./scripts/bootstrap.sh   # injection auto (mode sshpass)
```

---

## 4. Configuration locale (déjà appliquée)

`~/.ssh/config` a été mis à jour pour ajouter l'alias `prodserveur` :

```sshconfig
Host prodserveur
    HostName 169.58.30.70
    User younes
    IdentityFile ~/.ssh/id_smartserveur
    IdentitiesOnly yes
    ServerAliveInterval 60
    ServerAliveCountMax 3
    AddKeysToAgent yes
```

**Conséquence** : `ssh prodserveur` se connecte directement sans préciser l'IP.

> L'ancien alias `smartserveur` (164.68.97.103, vmi3398975) est conservé pour l'ancien serveur — voir section 5.

---

## 5. Distinction avec l'ancien "SmartServeur"

Tu as **deux VPS Contabo** actifs. Pour éviter toute confusion :

| Alias SSH | IP | Hostname Contabo | Rôle |
|---|---|---|---|
| `smartserveur` | `164.68.97.103` | `vmi3398975` | Ancien serveur "SmaerEfp" (Cloud VPS 20 NVMe) — héberge LibreChat, etc. |
| `prodserveur` | `169.58.30.70` | `vmi3445841` | **Nouveau serveur cible** (Cloud VPS 4 2026, sans config) |

Les deux utilisent la **même clé SSH** `id_smartserveur` (ED25519). Pas besoin d'en générer une nouvelle.

---

## 6. Stack applicative installée (2026-07-16)

| Service | Version | Port(s) | Status |
|---|---|---|---|
| Docker CE | 29.6.1 | — | ✅ actif |
| Docker Compose | 5.3.1 | — | ✅ plugin |
| Node.js (NodeSource) | 22.23.1 LTS | — | ✅ |
| npm | 10.9.8 | — | ✅ |
| Caddy | 2.11.4 | 80, 443, 2019 (admin localhost) | ✅ actif |
| PostgreSQL | 16.14 | 5432 (localhost only par défaut) | ✅ actif |
| Redis | 7.0.15 | 6379 (localhost only par défaut) | ✅ actif |

### Configuration initiale

- **Caddy** : `/etc/caddy/Caddyfile` (admin localhost:2019, importe `/etc/caddy/sites-enabled/*.caddy`)
- **PostgreSQL** : pas encore de user créé. Pour en créer un :
  ```bash
  sudo -u postgres createuser -s younes  # superuser
  sudo -u postgres createdb younes        # DB par défaut
  ```
- **Redis** : localhost-only par défaut. Pour bind 0.0.0.0 (⚠️ ajouter mdp) : éditer `/etc/redis/redis.conf`
- **Docker** : `younes` ajouté au groupe `docker` (déconnexion/reconnexion SSH requise pour appliquer)

### Arborescence

```
/srv/apps/                       ← racine des applications (vide)
/srv/apps/<nom-app>/             ← par app : code + docker-compose.yml
/opt/backups/                    ← backups (à configurer)
/etc/caddy/Caddyfile             ← config globale Caddy
/etc/caddy/sites-enabled/        ← vhosts Caddy par app
```

### Pour ajouter une app

```bash
ssh prodserveur
cd /srv/apps
mkdir myapp && cd myapp
# 1. Cloner le code OU créer docker-compose.yml
# 2. Créer le vhost Caddy
echo 'myapp.example.com { reverse_proxy localhost:3000 }' | sudo tee /etc/caddy/sites-enabled/myapp.caddy
sudo systemctl reload caddy
```

---

## 7. Fichiers de ce dossier

```
ProdServeur/
├── HANDOVER.md                  ← ce fichier
├── README.md                    ← quick-start
└── scripts/
    ├── bootstrap.sh             ← injection de la clé (auto ou manuel)
    └── test-connection.sh       ← vérif réseau + auth + commande distante
```

---

## 7. Hardening post-amorçage (à faire plus tard, après première connexion)

Une fois la clé injectée et l'auth par clé confirmée :

1. **Désactiver l'auth par mot de passe** :
   ```bash
   ssh prodserveur 'sudo sed -i "s/^#\?PasswordAuthentication.*/PasswordAuthentication no/" /etc/ssh/sshd_config && sudo systemctl reload sshd'
   ```
2. **Désactiver le login root** :
   ```bash
   ssh prodserveur 'sudo sed -i "s/^#\?PermitRootLogin.*/PermitRootLogin prohibit-password/" /etc/ssh/sshd_config && sudo systemctl reload sshd'
   ```
3. **Activer le firewall UFW** :
   ```bash
   ssh prodserveur 'sudo ufw allow 22/tcp && sudo ufw --force enable'
   ```
4. **Installer fail2ban** :
   ```bash
   ssh prodserveur 'sudo apt install -y fail2ban && sudo systemctl enable --now fail2ban'
   ```
5. **Mises à jour initiales** :
   ```bash
   ssh prodserveur 'sudo apt update && sudo apt -y upgrade && sudo reboot'
   ```

---

## 8. Troubleshooting

| Symptôme | Cause probable | Fix |
|---|---|---|
| `Permission denied (publickey)` après injection | Clé pas encore propagée par Contabo (~30s) | Attendre puis re-tester, ou utiliser `StrictHostKeyChecking=no` temporairement |
| `Connection refused` | Service SSH pas démarré | Via console série Contabo : `systemctl start sshd` |
| `Host key verification failed` | IP réutilisée d'un ancien VPS | `ssh-keygen -R 169.58.30.70` puis reconnecter |
| `ssh: Could not resolve hostname prodserveur` | Alias pas dans `~/.ssh/config` | Vérifier `cat ~/.ssh/config \| grep -A6 'Host prodserveur'` |
| Auth clé OK mais `sudo` demande mdp | User pas dans `sudoers` (ou `NOPASSWD` absent) | `ssh root@...` puis `usermod -aG sudo younes` |

---

_Dernière mise à jour : 2026-07-16 · testé depuis ce poste, latence ~75 ms._
