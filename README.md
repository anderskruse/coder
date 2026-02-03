# KK-code

```
██░  ██░  ██░  ██░           ████░   ████░   ████░   █████░
██░ ██░   ██░ ██░           █░      █░   █░  █░  █░  █░
█████░    █████░   ██████░  █░      █░   █░  █░  █░  ████░
██░ ██░   ██░ ██░           █░      █░   █░  █░  █░  █░
██░  ██░  ██░  ██░           ████░   ████░   ████░   █████░
```

AI-drevet kodningsassistent til kommandolinjen med Scaleway AI.

## Installation

### Første gang

**Option A: Fra Azure Artifacts (Anbefalet)**

```bash
uv tool install KK-code \
  --index-url https://pkgs.dev.azure.com/kkkit/_packaging/kk-code/pypi/simple/ \
  --extra-index-url https://pypi.org/simple
```

Det er det! Scriptet installerer alt automatisk.

### Efter installation

Start kkcode:

```bash
kkcode
```

**Første gang du kører det**, bliver du bedt om at indtaste:

1. **Din Scaleway API endpoint URL**
   ```
   https://api.scaleway.ai/DIT-PROJECT-ID/v1
   ```
   _(Få det fra din administrator eller Scaleway Console → AI → Generative APIs)_

2. **Din Scaleway API nøgle**
   ```
   scw_xxxxxxxxxxxxx
   ```
   _(Få det fra Scaleway Console → IAM → API Keys)_

Begge gemmes automatisk, så du behøver kun at gøre det én gang.

---

## VS Code / Cursor Integration (Valgfrit)

Hvis du bruger VS Code eller Cursor, kan du installere kkcode som en ACP-agent direkte i din editor:

```bash
kkcode-setup-vscode
```

Dette installerer automatisk VS Code ACP extension og viser dig hvordan du konfigurerer det.

**Fordele ved VS Code integration:**
- ✅ Filer åbnes automatisk i editoren mens AI'en arbejder
- ✅ Se præcise diffs før ændringer anvendes
- ✅ Godkend/afvis værktøjer direkte i editoren
- ✅ Integreret chat i VS Code

**Hvis du foretrækker terminalen**, kan du bare bruge `kkcode` som normalt.

---

## Brug

### Start en samtale

```bash
kkcode
```

Så kan du chatte med AI'en:

```
> Kan du hjælpe mig med at refaktorere denne funktion?

> Læs filen @src/main.py og forklar hvad den gør

> Skriv en test til min login-funktion

> Find alle TODO-kommentarer i projektet
```

### Tips

- **Flerlinjers input**: Tryk `Ctrl+J` eller `Shift+Enter` for at tilføje en ny linje
- **Fil-stier**: Brug `@` for autofuldførelse af filer (f.eks. `@src/`)
- **Shell-kommandoer**: Prefix med `!` for at køre direkte i shell (f.eks. `!ls -l`)

### Slash-kommandoer

```
/models    - Skift mellem tilgængelige modeller
/help      - Vis hjælp
/mode      - Skift tilstand (standard, auto-approve, plan)
```

---

## Opdatering

Når der kommer en ny version:

```bash
# Hvis du installerede fra Azure Artifacts (anbefalet):
uv tool upgrade KK-code

# Eller hvis du brugte install-script:
export AZURE_DEVOPS_PAT="dit-pat-token"
curl -sSL "https://:${AZURE_DEVOPS_PAT}@dev.azure.com/kkkit/YOURPROJECT/_apis/git/repositories/mistral-vibe/items?path=/releases/install-kkcode.sh&download=true" | bash
```

---

## Konfiguration (Valgfrit)

Konfigurationsfilen er her: `~/.kkcode/config.toml`

### Skift standardmodel

```toml
active_model = "qwen3-coder"  # Standard
```

### Værktøjstilladelser

```toml
[tools.bash]
permission = "ask"  # Valgmuligheder: "always", "ask", "never"

[tools.write_file]
permission = "ask"

[tools.read_file]
permission = "always"
```

### Miljøvariabler

Du kan kontrollere adfærd ved hjælp af følgende miljøvariabler:

- `KKCODE_ENABLE_TRUST_CHECK=1` - Aktiverer trust-check i CLI (viser "trust this folder" prompt)

---

## Tilgængelige Modeller

| Model | Udbyder | Beskrivelse |
|-------|---------|-------------|
| `qwen3-coder` | Scaleway | Qwen3 Coder 30B (standard) |
| `devstral-2` | Mistral | Devstral 2 (hvis du har Mistral API-nøgle) |
| `devstral-small` | Mistral | Mindre og hurtigere |

Skift model i samtale:
```
> /models
```

---

## Hvor Gemmes Data?

- **Konfiguration**: `~/.kkcode/config.toml`
- **API-nøgler**: `~/.kkcode/.env`
- **Samtalehistorik**: `~/.kkcode/logs/`

---

## Fejlfinding

### "Kommandoen 'kkcode' ikke fundet"

Tilføj til din PATH:

```bash
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### "API-nøgle fejl"

Kontroller din API-nøgle:

```bash
cat ~/.kkcode/.env
```

For at nulstille konfigurationen:

```bash
rm -rf ~/.kkcode
kkcode  # Vil spørge efter konfiguration igen
```

### "Kan ikke forbinde til Scaleway"

- Kontroller at din API endpoint URL er korrekt
- Kontroller at din API-nøgle er gyldig
- Kontroller internetforbindelse

---

## Sikkerhed

- Din API-nøgle gemmes kun lokalt på din computer (`~/.kkcode/.env`)
- Den sendes aldrig til andre end Scaleway's API
- Hver bruger har sin egen nøgle og konfiguration
- Samtalehistorik gemmes kun lokalt

---

## Eksempler

### Læs og forklar kode

```bash
kkcode "Læs @src/auth.py og forklar hvordan autentificering virker"
```

### Skriv ny kode

```bash
kkcode "Skriv en funktion der validerer email-adresser med regex"
```

### Refaktorer

```bash
kkcode "Refaktorer denne funktion til at være mere læsbar"
```

### Fejlfinding

```bash
kkcode "Find alle steder hvor vi kalder getUserById og tjek for null-checks"
```

### Generer tests

```bash
kkcode "Skriv unit tests til min Calculator-klasse"
```

---

## Support

**Problemer med installation eller brug?**
- Tjek denne README først
- Kontakt din administrator
- Se log-filer: `~/.kkcode/logs/`

**Vil du ændre API endpoint eller nøgle?**
```bash
rm ~/.kkcode/.env ~/.kkcode/config.toml
kkcode  # Vil spørge igen
```

---

## Hurtig Reference

```bash
# Installer (fra Azure Artifacts)
uv tool install KK-code \
  --index-url https://pkgs.dev.azure.com/kkkit/_packaging/kk-code/pypi/simple/ \
  --extra-index-url https://pypi.org/simple

# Opsæt VS Code integration (valgfrit)
kkcode-setup-vscode

# Kør
kkcode

# Opdater
uv tool upgrade KK-code

# Hjælp
kkcode --help
```

---

## For Administratorer: Opdatering fra Mistral

Når Mistral udgiver nye funktioner, skal du opdatere KK-code:

### Opdateringsworkflow

```bash
# 1. Gå til din lokale klon
cd kk-code

# 2. Hent og merge Mistrals opdateringer
git checkout main
git pull upstream main

# 3. Håndter konflikter (hvis nogen)
# Mest sandsynligt i: vibe/core/config.py
# Behold BÅDE din Scaleway config OG deres nye ting

# 4. Push til Azure DevOps
git push origin main

# 5. Byg ny wheel
uv build

# 6. Opdater releases folder
cp dist/KK_code-*.whl releases/KK-code-latest.whl
git add releases/KK-code-latest.whl
git commit -m "Opdater til version 1.x.x"
git push
```

### Publicer til Azure Artifacts (Valgfrit)

Hvis I bruger Azure Artifacts feed i stedet for git-filer:

**Først: Opret PAT token**

1. Gå til Azure DevOps → User Settings (øverst til højre) → Personal access tokens
2. Klik "+ New Token"
3. Udfyld:
   - **Name:** KK-code Publishing
   - **Organization:** Vælg din organisation
   - **Expiration:** 90 dage (eller custom)
   - **Scopes:** Custom defined
4. Scroll ned og vælg:
   - **Packaging** → **Read & write** ✓
5. Klik "Create" og kopier tokenet (du ser det ikke igen!)

**Publicer pakken:**

```bash
# Installer twine
uv tool install twine

# Byg pakken
uv build

# Upload til Azure Artifacts (brug dit PAT token)
# VIGTIGT: --username skal være dit projectnavn
twine upload --repository-url https://kkkit.pkgs.visualstudio.com/0a5adc50-1e83-49a4-8692-3bd54a5536b3/_packaging/kk-code/pypi/upload/ \
  --username "kkkit" \
  --password "YOUR_PAT_TOKEN" \
  dist/*
```

Så kan brugere installere direkte fra Azure Artifacts:
```bash
uv tool install KK-code \
  --index-url https://pkgs.dev.azure.com/kkkit/_packaging/kk-code/pypi/simple/ \
  --extra-index-url https://pypi.org/simple
```

### Håndtering af konflikter

Hvis der er konflikter i `vibe/core/config.py`:

1. Åbn filen i en editor
2. Find konfliktmarkøren (`<<<<<<<`)
3. Behold BÅDE din Scaleway konfiguration OG Mistrals nye features
4. Gem filen
5. Kør: `git add vibe/core/config.py`
6. Kør: `git commit -m "Merge Mistral opdateringer"`
7. Fortsæt fra trin 4 ovenfor

### Første gang: Opsætning af upstream

Hvis du ikke allerede har gjort det:

```bash
cd mistral-vibe
git remote add upstream https://github.com/mistralai/mistral-vibe.git
git fetch upstream
```

Nu kan du altid hente Mistrals opdateringer med `git pull upstream main`

---

Bygget på [Mistral Vibe](https://github.com/mistralai/mistral-vibe) med Scaleway AI-support.
