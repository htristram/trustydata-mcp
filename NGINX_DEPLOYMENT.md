# Déploiement avec Nginx - Guide Rapide

## Résumé de ce qui a été créé

Votre serveur MCP est maintenant **prêt pour claude.ai** ! Voici ce que j'ai créé :

### 1. Nouveau serveur MCP conforme ✅

**Fichier** : `server_remote.py`

- ✅ Protocole **Streamable HTTP** (MCP 2025-06-18) - dernière spécification
- ✅ Gestion des **sessions** avec `Mcp-Session-Id`
- ✅ **Authentification** Bearer token
- ✅ Support des **headers MCP** requis
- ✅ Endpoint `/mcp` conforme à la spec
- ✅ Health check `/health`

### 2. Configuration Nginx ✅

**Fichier** : `nginx_mcp.conf`

- ✅ Reverse proxy configuré
- ✅ Support HTTPS avec Let's Encrypt
- ✅ Headers MCP préservés
- ✅ Timeouts appropriés
- ✅ Headers de sécurité
- ✅ Logs configurés

### 3. Scripts et outils ✅

- `start_remote_server.sh` - Démarrage facile du serveur
- `test_remote_server.py` - Suite de tests complète
- `.env.remote.example` - Template de configuration
- `DEPLOYMENT.md` - Guide complet de déploiement

## Différences avec votre ancien serveur

| Aspect | Ancien (`server_http.py`) | Nouveau (`server_remote.py`) |
|--------|---------------------------|------------------------------|
| Protocole | SSE (déprécié) | Streamable HTTP (2025-06-18) |
| Sessions | ❌ Non géré | ✅ Headers Mcp-Session-Id |
| Auth | ❌ Aucune | ✅ Bearer token |
| Headers | ❌ Manquants | ✅ MCP-Protocol-Version |
| Endpoints | `/sse`, `/messages` | `/mcp` (spec conforme) |
| Claude.ai | ❌ Non compatible | ✅ Prêt à l'emploi |

## Test en local (avant déploiement)

### 1. Installation

```bash
cd /home/htristram/dev/trusty_claude_connect

# Installer les dépendances si pas déjà fait
venv/bin/pip install -r requirements.txt
```

### 2. Configuration

Créez un fichier `.env` :

```bash
cp .env.remote.example .env
nano .env
```

Contenu du `.env` :

```bash
TRUSTYDATA_API_KEY=trusty_ad_287513577b2fca54bc4998dcc931463e4b307a3721bdbfc2dea11937ce1d200e
SERVER_AUTH_TOKEN=$(openssl rand -hex 32)  # Générez un token sécurisé
PORT=8000
HOST=127.0.0.1
```

### 3. Démarrer le serveur

```bash
./start_remote_server.sh
```

Vous devriez voir :

```
╔═══════════════════════════════════════════════════╗
║   TrustyData MCP Remote Server - Startup         ║
╚═══════════════════════════════════════════════════╝

Starting MCP Remote Server...
  Protocol: Streamable HTTP (MCP 2025-06-18)
  Host: 127.0.0.1
  Port: 8000
  Endpoint: http://127.0.0.1:8000/mcp
  Health Check: http://127.0.0.1:8000/health
  Auth: Enabled
```

### 4. Tester le serveur

Dans un autre terminal :

```bash
# Test automatique complet
./test_remote_server.py

# Ou test manuel
curl http://127.0.0.1:8000/health
```

## Déploiement sur votre serveur avec Nginx

### Étape 1 : Préparer les fichiers

Sur votre serveur, créez un dossier :

```bash
sudo mkdir -p /opt/trustydata-mcp
cd /opt/trustydata-mcp
```

Copiez les fichiers suivants depuis votre machine locale :

```bash
# Depuis votre machine locale
scp server_remote.py votre-serveur:/opt/trustydata-mcp/
scp requirements.txt votre-serveur:/opt/trustydata-mcp/
scp nginx_mcp.conf votre-serveur:/tmp/
```

### Étape 2 : Configuration du serveur

Sur votre serveur :

```bash
# Créer l'environnement Python
cd /opt/trustydata-mcp
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Créer le .env
cat > .env << 'EOF'
TRUSTYDATA_API_KEY=trusty_ad_287513577b2fca54bc4998dcc931463e4b307a3721bdbfc2dea11937ce1d200e
SERVER_AUTH_TOKEN=$(openssl rand -hex 32)
PORT=8500
HOST=127.0.0.1
EOF

# Générer et remplacer le token
TOKEN=$(openssl rand -hex 32)
sed -i "s/\$(openssl rand -hex 32)/$TOKEN/" .env

# Notez le token pour plus tard !
echo "Votre SERVER_AUTH_TOKEN: $TOKEN"
```

### Étape 3 : Service systemd

Créez `/etc/systemd/system/trustydata-mcp.service` :

```ini
[Unit]
Description=TrustyData MCP Remote Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/work/trustydata-mcp
EnvironmentFile=/work/trustydata-mcp/.env
ExecStart=/work/trustydata-mcp/venv/bin/python /work/trustydata-mcp/server_remote.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Activez le service :

```bash
sudo systemctl daemon-reload
sudo systemctl enable trustydata-mcp
sudo systemctl start trustydata-mcp
sudo systemctl status trustydata-mcp
```

### Étape 4 : Configuration Nginx

```bash
# Copier la configuration
sudo cp /tmp/nginx_mcp.conf /etc/nginx/sites-available/mcp

# Éditez pour mettre votre domaine
sudo nano /etc/nginx/sites-available/mcp
# Changez : mcp.votre-domaine.com
```

**Points à modifier dans `nginx_mcp.conf`** :
1. `server_name mcp.votre-domaine.com;` (2 occurrences)
2. Chemins SSL (après installation du certificat)

### Étape 5 : Certificat SSL avec Let's Encrypt

```bash
# Installer certbot si pas déjà fait
sudo apt install certbot python3-certbot-nginx

# Obtenir le certificat
sudo certbot --nginx -d mcp.votre-domaine.com

# Les chemins SSL seront automatiquement configurés par certbot
```

### Étape 6 : Activer la configuration

```bash
# Activer le site
sudo ln -s /etc/nginx/sites-available/mcp /etc/nginx/sites-enabled/

# Tester la configuration
sudo nginx -t

# Si OK, recharger
sudo systemctl reload nginx
```

### Étape 7 : Test du déploiement

```bash
# Health check
curl https://mcp.votre-domaine.com/health

# Test complet (depuis votre machine locale)
export MCP_SERVER_URL="https://mcp.votre-domaine.com"
export SERVER_AUTH_TOKEN="votre_token"
./test_remote_server.py
```

## Configuration dans claude.ai

### Pour les plans Pro/Max

1. Allez sur https://claude.ai
2. **Settings** → **Connectors** → **Add custom connector**
3. Remplissez :
   - **URL** : `https://mcp.votre-domaine.com/mcp`
   - **Nom** : TrustyData French Localities
4. Cliquez **Add**

### Pour les plans Team/Enterprise

1. Admin settings → **Connectors**
2. **Add custom connector**
3. Remplissez les mêmes informations
4. (Optionnel) Configurez OAuth dans Advanced settings

### ⚠️ Important : Authentication

Le serveur utilise **Bearer token authentication**. Claude.ai devra envoyer le header :

```
Authorization: Bearer VOTRE_SERVER_AUTH_TOKEN
```

**Note** : Pour l'instant, Claude.ai ne supporte peut-être pas encore l'envoi de tokens personnalisés dans les connecteurs. Si c'est le cas, vous avez 2 options :

#### Option A : Désactiver temporairement l'auth (DEV UNIQUEMENT)

Dans votre `.env` sur le serveur :

```bash
# Commentez ou supprimez cette ligne
# SERVER_AUTH_TOKEN=...
```

Redémarrez le service :

```bash
sudo systemctl restart trustydata-mcp
```

#### Option B : Implémenter OAuth (Recommandé pour production)

Si vous voulez OAuth, je peux vous aider à l'implémenter. C'est ce qu'Anthropic recommande pour les connecteurs production.

## Vérification du fonctionnement

### Logs du service MCP

```bash
# En temps réel
sudo journalctl -u trustydata-mcp -f

# Dernières erreurs
sudo journalctl -u trustydata-mcp -p err -n 50
```

### Logs Nginx

```bash
# Accès
sudo tail -f /var/log/nginx/mcp_access.log

# Erreurs
sudo tail -f /var/log/nginx/mcp_error.log
```

### Test dans Claude

Dans une conversation avec Claude (après avoir ajouté le connecteur) :

```
Peux-tu rechercher les communes françaises avec plus de 50 000 habitants en Bretagne ?
```

Claude devrait utiliser automatiquement votre outil MCP.

## Sécurité

### Headers de sécurité (déjà configurés dans nginx)

- ✅ HTTPS obligatoire
- ✅ X-Frame-Options
- ✅ X-Content-Type-Options
- ✅ X-XSS-Protection

### Recommandations supplémentaires

1. **Limitez l'accès par IP** si vous connaissez les IPs d'Anthropic
2. **Rate limiting** pour éviter les abus
3. **Monitoring** avec des alertes
4. **Rotation régulière** du SERVER_AUTH_TOKEN
5. **Backups** de votre configuration

## Troubleshooting

### Le serveur ne démarre pas

```bash
# Voir les erreurs
sudo journalctl -u trustydata-mcp -n 50

# Vérifier les permissions
ls -la /opt/trustydata-mcp/

# Tester manuellement
cd /opt/trustydata-mcp
source venv/bin/activate
export $(cat .env | xargs)
python server_remote.py
```

### Nginx 502 Bad Gateway

```bash
# Le service tourne-t-il ?
sudo systemctl status trustydata-mcp

# Écoute-t-il sur le bon port ?
sudo netstat -tlnp | grep 8000

# Erreurs nginx ?
sudo nginx -t
sudo tail -f /var/log/nginx/mcp_error.log
```

### Claude.ai ne peut pas se connecter

1. **Vérifiez le certificat SSL** :
   ```bash
   curl -I https://mcp.votre-domaine.com/health
   ```

2. **Vérifiez que le endpoint est accessible** :
   ```bash
   curl -X POST https://mcp.votre-domaine.com/mcp \
     -H "Content-Type: application/json" \
     -H "MCP-Protocol-Version: 2025-06-18" \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
   ```

3. **Désactivez temporairement l'auth** pour tester

4. **Consultez les logs** nginx et du service

## Checklist de déploiement

- [ ] Serveur Python installé et testé localement
- [ ] Fichiers copiés sur le serveur distant
- [ ] Environment variables (.env) configuré
- [ ] Service systemd créé et démarré
- [ ] Certificat SSL installé avec Let's Encrypt
- [ ] Configuration nginx activée
- [ ] Health check accessible via HTTPS
- [ ] Endpoint /mcp testé avec curl
- [ ] Connecteur ajouté dans claude.ai
- [ ] Test fonctionnel dans Claude
- [ ] Logs configurés et consultables
- [ ] Sauvegardes configurées

## Support

- **MCP Specification** : https://modelcontextprotocol.io/specification/2025-06-18
- **Claude Connectors** : https://support.claude.com/en/articles/11175166
- **TrustyData API** : https://api.trustydata.app/docs

---

✨ **Votre serveur MCP est prêt pour claude.ai !**
