# Configuration pour claude.ai (Version Web)

Ce guide vous explique comment utiliser le serveur MCP TrustyData avec claude.ai (la version web de Claude).

## Différences entre Claude Desktop et claude.ai

- **Claude Desktop** : Utilise le protocole MCP via stdio (entrée/sortie standard)
- **claude.ai (Web)** : Nécessite un serveur HTTP/SSE accessible publiquement

## Prérequis

1. Python 3.10 ou supérieur
2. Un compte ngrok (gratuit) pour exposer votre serveur localement
3. Votre clé API TrustyData

## Installation étape par étape

### 1. Installer les dépendances

```bash
cd /home/htristram/dev/trusty_claude_connect
venv/bin/pip install -r requirements.txt
```

Cela installera les dépendances supplémentaires nécessaires pour le serveur HTTP :
- `starlette` : Framework web pour Python
- `uvicorn` : Serveur ASGI
- `sse-starlette` : Support Server-Sent Events

### 2. Installer ngrok (si pas déjà fait)

#### Option A : Via snap (recommandé pour Linux)
```bash
sudo snap install ngrok
```

#### Option B : Téléchargement manuel
```bash
# Télécharger ngrok
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz

# Extraire
tar xvzf ngrok-v3-stable-linux-amd64.tgz

# Déplacer dans /usr/local/bin
sudo mv ngrok /usr/local/bin/
```

#### Option C : Via le site web
Visitez https://ngrok.com/download et suivez les instructions pour votre plateforme.

### 3. Configurer ngrok

1. Créez un compte gratuit sur https://ngrok.com
2. Récupérez votre token d'authentification depuis https://dashboard.ngrok.com/get-started/your-authtoken
3. Configurez ngrok avec votre token :

```bash
ngrok authtoken VOTRE_TOKEN_ICI
```

## Démarrage du serveur

### Méthode simple : Utiliser le script automatique

```bash
cd /home/htristram/dev/trusty_claude_connect
./start_web_server.sh
```

Le script vous demandera si vous voulez exposer le serveur via ngrok. Répondez `y` pour oui.

Le script affichera une URL publique comme :
```
Public URL: https://abcd-1234-5678-9abc.ngrok-free.app
SSE Endpoint: https://abcd-1234-5678-9abc.ngrok-free.app/sse
```

**⚠️ IMPORTANT : Notez cette URL, vous en aurez besoin pour configurer claude.ai**

### Méthode manuelle

Si vous préférez démarrer le serveur manuellement :

1. Démarrez le serveur HTTP :
```bash
export TRUSTYDATA_API_KEY="trusty_ad_287513577b2fca54bc4998dcc931463e4b307a3721bdbfc2dea11937ce1d200e"
venv/bin/python server_http.py
```

2. Dans un autre terminal, démarrez ngrok :
```bash
ngrok http 8000
```

3. Récupérez l'URL publique affichée par ngrok (ligne "Forwarding")

## Configuration dans claude.ai

Malheureusement, **claude.ai (la version web) ne supporte pas encore officiellement les serveurs MCP personnalisés**.

Les serveurs MCP sont actuellement supportés uniquement sur :
- **Claude Desktop** (macOS, Windows, Linux)
- **Applications tierces** qui implémentent le protocole MCP

### Solutions alternatives

#### Option 1 : Utiliser Claude Desktop (Recommandé)

Claude Desktop supporte nativement les serveurs MCP. Vous avez déjà la configuration pour Claude Desktop dans votre fichier `claude_desktop_config.json`.

Pour l'utiliser :
1. Installez Claude Desktop depuis https://claude.ai/download
2. Utilisez la configuration existante dans `claude_desktop_config.json`
3. Redémarrez Claude Desktop

#### Option 2 : Utiliser l'API Claude directement

Si vous devez absolument utiliser l'API Claude (non la version web), vous pouvez :

1. Créer un script Python qui :
   - Appelle votre serveur MCP local
   - Utilise l'API Claude (avec une clé API)
   - Fait le pont entre les deux

2. Exemple de script :

```python
import anthropic
import httpx

# Fonction pour appeler votre serveur MCP
async def search_localities(query_params):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/messages",
            json={
                "tool": "search_localities",
                "arguments": query_params
            }
        )
        return response.json()

# Utiliser avec l'API Claude
client = anthropic.Anthropic(api_key="votre_clé_api_claude")

# Votre code ici...
```

#### Option 3 : Attendre le support MCP dans claude.ai

Anthropic travaille sur l'intégration des serveurs MCP dans la version web de claude.ai. Cette fonctionnalité pourrait être disponible dans le futur.

## Vérification que le serveur fonctionne

Pour tester que votre serveur HTTP fonctionne correctement :

```bash
# Test local
curl http://localhost:8000/sse

# Test avec l'URL ngrok
curl https://VOTRE_URL_NGROK.ngrok-free.app/sse
```

Vous devriez recevoir une réponse indiquant que le serveur MCP est en écoute.

## Sécurité

### ⚠️ Points importants

1. **Votre clé API TrustyData est exposée** dans le code et visible dans les variables d'environnement
2. **Ngrok expose votre serveur publiquement** - n'importe qui avec l'URL peut l'utiliser
3. **Pas d'authentification** sur le serveur actuellement

### Recommandations

Pour une utilisation en production :

1. **Ajoutez une authentification** au serveur HTTP :
```python
# Dans server_http.py
@app.middleware("http")
async def verify_token(request: Request, call_next):
    token = request.headers.get("Authorization")
    if token != f"Bearer {os.getenv('SERVER_TOKEN')}":
        return Response("Unauthorized", status_code=401)
    return await call_next(request)
```

2. **Utilisez HTTPS** avec un certificat SSL valide (ngrok le fait automatiquement)

3. **Limitez l'accès** par IP si possible

4. **Stockez la clé API** dans un service de gestion de secrets (AWS Secrets Manager, etc.)

## Dépannage

### Le serveur ne démarre pas

```bash
# Vérifiez que toutes les dépendances sont installées
venv/bin/pip list | grep -E "(starlette|uvicorn|sse-starlette)"

# Réinstallez si nécessaire
venv/bin/pip install -r requirements.txt --force-reinstall
```

### Ngrok ne fonctionne pas

```bash
# Vérifiez que ngrok est installé
which ngrok

# Vérifiez la configuration
ngrok config check

# Vérifiez votre token
cat ~/.config/ngrok/ngrok.yml
```

### Erreur "Address already in use"

Le port 8000 est déjà utilisé. Changez le port :

```bash
PORT=8001 ./start_web_server.sh
```

## Résumé

Pour utiliser TrustyData MCP avec la version web de Claude :

1. ✅ **Serveur HTTP créé** : `server_http.py`
2. ✅ **Script de démarrage prêt** : `start_web_server.sh`
3. ❌ **claude.ai ne supporte pas encore les MCP personnalisés**

**Recommandation** : Utilisez Claude Desktop qui supporte parfaitement votre serveur MCP via la configuration `claude_desktop_config.json`.

## Support et ressources

- Documentation MCP : https://modelcontextprotocol.io
- Claude Desktop : https://claude.ai/download
- Documentation Anthropic : https://docs.anthropic.com
- Ngrok : https://ngrok.com/docs
