# Fiken MCP for Claude på Mac og Windows

Lokal MCP-server for Claude Desktop og Claude Code som leser regnskapet og kan lagre **kjøps- og salgsutkast**, men aldri bokføre. Hver bruker logger inn med sin egen Fiken-konto gjennom **OAuth 2.0 med PKCE (S256)**. Tokens lagres i macOS Nøkkelring eller Windows Credential Manager.

**Pilot:** les bilag, få forslag til full kontering og få forslaget lagret som utkast i Fiken. Claude tolker bilaget og foreslår kontoer og mva; serveren gir datagrunnlag, kontrollerer regnestykket og lagrer utkastet. Du kontrollerer og bokfører selv i Fiken. Ingenting bokføres av serveren. Ikke en offisiell Fiken-integrasjon.

## Nytt i 0.4

- **Kjøps- og salgsutkast.** `fiken_create_purchase_draft` og `fiken_create_sale_draft` lagrer forslaget som utkast i Fiken, tilsvarende «Nytt kjøp» → lagre som utkast. Bilaget fra innboksen legges ved med `inbox_document_id`.
- `fiken_update_*_draft`, `fiken_delete_*_draft`, `fiken_attach_inbox_document_to_draft`, `fiken_list_sale_drafts` og `fiken_get_sale_draft`.
- **Bokføring er sperret i koden.** Skrivetransporten godtar bare `…/purchases/drafts` og `…/sales/drafts`. `createPurchase`/`createSale` og alle andre skrivestier avvises før noe sendes.
- Før lagring kontrolleres det at summen av linjene er lik bilagets total, at linjer uten mva har brutto lik netto, at betalinger stemmer, og at det ikke finnes utkast eller bokført kjøp med samme fakturanummer eller samme beløp og dato.
- Claude får beskjed om å bruke disse verktøyene i stedet for nettleseren når du ber om utkast i Fiken.
- `FIKEN_READ_ONLY=1` skjuler alle skriveverktøy.

## Nytt i 0.3.1

- Windows-støtte med sikker tokenlagring i Credential Manager.
- Fillås på tvers av prosesser fungerer på både Mac og Windows.
- Claude-konfigurasjon velger riktig `.exe` på Windows.

## Nytt i 0.3

- Kontosaldo krever gyldig dato. Alle paginerte listeverktøy gir `data` og `pagination` med neste side og totalantall når API-et oppgir dette.
- Kontoplan kan leses over flere sider. Konteringskontrollen leser automatisk videre.
- Nye leseverktøy for enkeltkjøp, kjøpsvedlegg (inkludert PDF/bilde), kjøpsutkast, leverandører og bankkontoer.
- Leverandørhistorikk og duplikatsøk med kilder, søkeomfang og tydelig melding ved ufullstendig søk.
- Separate kontroller for aritmetikk, kontoplan, gjenkjente mva-koder og mulige duplikater.
- `config` lager Claude-konfigurasjon; `doctor` kontrollerer innlogging og API-tilgang.

## Hva piloten kan gjøre

- Lese foretak, kontoplan, saldoer, kontakter, fakturaer, kjøp, salg og journalposter.
- Lese vedlegg på journalposter, for eksempel mellombalanse bak inngående balanse.
- Lese innboksbilag som PDF, PNG og JPEG; PDF kan leses som tekst eller sidebilder for skannede bilag. Maks 15 MiB per svar.
- Lese strukturerte EHF-fakturaer og kreditnotaer.
- Gi Claude en arbeidsflyt for full kontering med kostnad/eiendel, mva og motkonto, bilagsreferanser, begrunnelse og åpne spørsmål.
- Kontrollere debet/kredit og bruttobeløp for enkle NOK-bilag, at kontoene finnes i foretakets nåværende kontoplan og at numeriske kjøps-mvakoder er gjenkjent. Dette bekrefter ikke skattebehandling eller riktig kontovalg. Mer kompliserte bilag, kreditnota og valuta må vurderes separat.

## Utkast i Fiken (kjøp og salg)

Si for eksempel: «Lag kjøpsutkast i Fiken for Hira Trading: Egil Jensen AS faktura 245458. Ikke bokfør.»

Claude finner bilaget i innboksen, lager konteringsforslaget og kaller `fiken_create_purchase_draft`. Utkastet dukker opp under **Kjøp** i Fiken (salg under **Salg**) med leverandør, dato, fakturanummer, forfall, linjer, mva og vedlagt bilag. Du åpner det, kontrollerer og trykker selv på «Bokfør».

Viktig om feltene:

- Beløp er heltall i øre. Hver linje har `net_ore` og `gross_ore`. Fradrag, gebyr og øreavrunding kan være negative linjer.
- `vat_type` bruker Fikens navn: `HIGH` (25 %), `MEDIUM` (15 %), `LOW` (12 %), `NONE`, `EXEMPT`, `OUTSIDE` osv. Dette er ikke de numeriske kodene som `fiken_validate_posting_proposal` bruker.
- `expected_gross_ore` er totalen på bilaget. Stemmer ikke linjene med totalen, lagres ingenting.
- Betalt bilag: `paid=true` og `payments` med dato, betalingskonto (f.eks. `1920:10001`) og beløp. Kontantkjøp: `cash=true`.
- Mulig duplikat stopper lagringen. `allow_duplicate=true` brukes bare når du har bekreftet at det ikke er et duplikat.
- Fiken kontrollerer selv kontoer og kombinasjoner av konto og mva. Feilmeldingen fra Fiken vises til Claude, så forslaget kan rettes.
- Foretaket må ha API-tilgang aktivert i Fiken.

### Tillatelser i Claude

Lesing og skriving er separate verktøy. Lesing er merket skrivebeskyttet og kan settes til **Always allow** i Claude. Verktøy som lager, endrer eller sletter utkast er merket som skrivende. La dem stå på **Allow once** hvis du vil godkjenne hvert utkast før det lagres.

Hvis Claude spør om å bruke nettleseren på fiken.no for å lage utkast, kjører du en eldre versjon uten utkastverktøy. Oppdater (se under) og start Claude på nytt.

### Oppdater til 0.4

```bash
git pull --ff-only
.venv/bin/python -m pip install .
```

Windows:

```powershell
git pull --ff-only
.\.venv\Scripts\python.exe -m pip install .
```

Avslutt Claude helt og åpne på nytt. Innloggingen beholdes.

## 1. Registrer Fiken-appen én gang

Repoeier registrerer en offentlig app i Fiken og deler dens **Client ID** med pilotbrukerne. Hver bruker gir deretter sin egen tilgang. Alternativt kan en bruker registrere sin egen app.

1. Aktiver utvikler under **Rediger konto → Profil → Andre innstillinger**.
2. Opprett app under **Brukerinnstillinger → API**.
3. Velg **Avanserte innstillinger → Uten client secret (PKCE)** ved opprettelse.
4. Registrer nøyaktig denne redirect-adressen: `http://127.0.0.1:8765/callback`.
5. Ta vare på Client ID. Den er offentlig, men er ikke forhåndsutfylt i dette repoet.

Brukere må ha Fiken API-tilgang til foretakene sine. Fiken dokumenterer inntil fem brukere i utviklingsfasen, og krever 2–3 reelle pilotbrukere før søknad om produksjonstilgang. Se [Fikens API-dokumentasjon](https://api.fiken.no/api/v2/docs/) for gjeldende vilkår og appregistrering.

### Hvis Fiken krever HTTPS i redirect-feltet

Den offentlige [Fiken-dokumentasjonen](https://api.fiken.no/api/v2/docs/) sier at
**offentlige PKCE-klienter** kan registrere en lokal loopback-redirect. Appen må
opprettes med **Avanserte innstillinger → Uten client secret (PKCE)**. Dette valget
kan ifølge Fiken bare gjøres ved opprettelse. Har appen en klienthemmelighet,
opprett en ny offentlig PKCE-app og bruk den nye Client ID-en.

Denne serveren bruker nøyaktig `http://127.0.0.1:8765/callback`. Ikke endre bare
prefikset til `https`: callback-serveren tilbyr HTTP og har ikke et TLS-sertifikat.
En tilfeldig HTTPS-nettside vil heller ikke sende innloggingen tilbake til denne
lokale serveren. Hvis en ny offentlig PKCE-app fortsatt avviser loopback-adressen,
må registreringen avklares med Fiken; HTTPS krever et annet callback-oppsett enn
det denne piloten implementerer.

## 2. Installer lokalt

Krever macOS eller Windows, Git og Python 3.11 eller nyere.

### Mac
 Har du Homebrew, kan Python installeres med `brew install python@3.12`.

```bash
git clone https://github.com/dansheik/fiken-mcp.git
cd fiken-mcp
python3.12 -m venv .venv
.venv/bin/python -m pip install .
export FIKEN_CLIENT_ID='DIN_OFFENTLIGE_CLIENT_ID'
.venv/bin/fiken-mcp login
```

### Windows (PowerShell)

**Ikke-tekniske brukere:** følg den enkle trinnvise veiledningen i [WINDOWS.md](WINDOWS.md).

Åpne PowerShell i mappen der prosjektet skal klones. Har du allerede klonet, gå inn
på prosjektmappen og kjør `git pull --ff-only` før installasjonen.

```powershell
git clone https://github.com/dansheik/fiken-mcp.git
cd fiken-mcp
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
$env:FIKEN_CLIENT_ID = 'DIN_OFFENTLIGE_CLIENT_ID'
.\.venv\Scripts\fiken-mcp.exe login
.\.venv\Scripts\fiken-mcp.exe doctor
.\.venv\Scripts\fiken-mcp.exe config
```

Bruk en installert Python-versjon 3.11 eller nyere hvis `py -3.12` ikke finnes.
Ingen aktivering av miljøet eller endring av PowerShell execution policy trengs.
Windows-tokenet lagres i Credential Manager. Låsefilen (uten tokens) ligger i
`%LOCALAPPDATA%\fiken-mcp`.

Innloggingen åpner nettleseren. Velg hvilke foretak appen skal få tilgang til. Callback-serveren lytter bare på `127.0.0.1:8765` under innlogging, og venter i inntil tre minutter. Nøkkelring kan be om lokal tilgang. Ingen token skal kopieres til Claude-konfigurasjonen.

Etter innlogging kan du kontrollere tilgangen og få ferdig konfigurasjon med riktig lokal sti:

```bash
.venv/bin/fiken-mcp doctor
.venv/bin/fiken-mcp config
```

`doctor` gjør et lesekall til Fiken, og kan fornye OAuth-token. `config` skriver kun JSON til terminalen og overskriver ingen innstillinger.

## 3. Koble til Claude Desktop

Åpne **Settings → Developer → Edit Config**. Konfigurasjonsfilen på Mac heter `~/Library/Application Support/Claude/claude_desktop_config.json`. På Windows ligger den i `%APPDATA%\Claude\claude_desktop_config.json`.

På Windows: bruk JSON fra `.\.venv\Scripts\fiken-mcp.exe config`; den setter korrekt absolutt sti og JSON-escaping for Windows.

Legg til `fiken` i eksisterende `mcpServers`, og behold eventuelle andre servere. Bruk den **absolutte** stien til `.venv/bin/fiken-mcp` i klonen din og samme Client ID som ved innlogging:

```json
{
  "mcpServers": {
    "fiken": {
      "command": "/ABSOLUTT/STI/fiken-mcp/.venv/bin/fiken-mcp",
      "args": ["serve"],
      "env": {"FIKEN_CLIENT_ID": "DIN_OFFENTLIGE_CLIENT_ID"}
    }
  }
}
```

Avslutt Claude helt og åpne på nytt. Serveren bruker lokal stdio, ikke en ekstern MCP-URL. `.env` lastes ikke automatisk.

### Claude Code

Fra klonen, etter innlogging:

```bash
claude mcp add --scope user --transport stdio --env FIKEN_CLIENT_ID="$FIKEN_CLIENT_ID" fiken -- "$PWD/.venv/bin/fiken-mcp" serve
```

På Windows PowerShell, fra klonen etter innlogging:

```powershell
claude mcp add --scope user --transport stdio --env "FIKEN_CLIENT_ID=$env:FIKEN_CLIENT_ID" fiken -- "$PWD\.venv\Scripts\fiken-mcp.exe" serve
```

Se [Claude Codes MCP-dokumentasjon](https://code.claude.com/docs/en/mcp).

## Bruk

Start med: «List foretakene jeg har tilgang til i Fiken.» Velg foretak uttrykkelig. Deretter:

> Les ubrukte bilag i innboksen for foretaket. Analyser ett bilag om gangen. Les alle sider, hent kontoplanen og foreslå full kontering med konto, debet, kredit, mva, motkonto og begrunnelse. Oppgi usikkerheter og kontroller for duplikat. Ikke bokfør noe.

MCP-prompten `foresla_kontering` gir denne arbeidsflyten med `company_slug` og `document_id`. Verktøyet `fiken_validate_posting_proposal` tar et strukturert forslag fra Claude og returnerer alltid et utkast som krever menneskelig kontroll. Beløp er heltall i øre. Paginerte listeverktøy har nullbasert `page` og returnerer `{data, pagination}`. Følg `pagination.next_page` til den er `null`. Mangler API-et sidetall, avsluttes søket først ved en tom side. PDF-sider starter på 1.

### Kontroller og historikk

- `fiken_list_account_balances` krever `date`, for eksempel `2026-09-30`.
- `fiken_purchase_history` bruker en verifisert `supplier_id` og gir tidligere kjøp med dato, ID og linjer. Valgfrie datofiltre avgrenser historikken.
- `fiken_find_duplicate_purchases` sammenligner fakturanummer (trimmet, uten forskjell på store/små bokstaver), eller NOK-beløp og dato, innen samme leverandør-ID. Den søker på tvers av datoer, men inkluderer ikke kjøpsutkast, innboks eller andre leverandør-ID-er. Slettede kjøp ignoreres. Treff er kandidater for kontroll, ikke bevis.
- Automatisk historikk-/kontoplanlesing stopper etter `max_pages` (standard 20, maks 100, 100 poster per side). `complete=false` og `next_page` viser at søket ikke er ferdig. Avgrens historikk eller les videre med listeverktøyene. Registre i endring kan endre seg mellom sidene; dette er ikke et øyeblikksbilde.
- `fiken_validate_posting_proposal` bruker normalt Fiken GET for kontoplan og duplikatsøk. Oppgi `supplier_id` for duplikatsjekk. `check_fiken=false` gir bare lokal kontroll; øvrige sjekker merkes `not_checked`.
- Resultatet skiller `arithmetic_valid`, `account_check`, `vat_check` og `duplicate_check`. Ukjente mva-koder blir `unresolved`. Gjenkjent kode er aldri en bekreftelse på fradragsrett eller sats. Bruk numeriske kjøps-mvakoder fra [Fiken-dokumentasjonen](https://api.fiken.no/api/v2/docs/), ikke `vatType`-navn som `HIGH`. Kodene er kontrollert mot dokumentasjonen 28. oktober 2026.
- Kontoplanen er for inneværende år. Historisk kontogyldighet kontrolleres ikke. Forslaget er alltid et manuelt utkast, ikke et payload for bokføring; separate mva-linjer må ikke sendes som en automatisk Fiken-postering.

### Oppdater fra 0.2 til 0.3

Kjør i klonen og start Claude på nytt:

```bash
git pull --ff-only
.venv/bin/python -m pip install .
```

OAuth-oppsettet er uendret. **Endret verktøyformat:** paginerte lister returnerer nå `data` + `pagination`, kontosaldo krever `date`, og konteringsvalidering leser som standard fra Fiken. Ingen endringer gjøres i regnskapet.

## Personvern og sikkerhetsgrenser

- OAuth er per OS-bruker og Client ID. Ingen personlig API-token eller client secret brukes.
- Tilgangs- og refresh-token lagres samlet i systemets legitimasjonslager. Rotering og API-kall serialiseres mellom lokale prosesser med fillås. Bytte av Fiken-bruker gjøres med ny `login`.
- Lesing bruker GET. Skriving er begrenset til en hviteliste: `POST`/`PUT`/`DELETE` på `companies/{foretak}/purchases/drafts` og `…/sales/drafts`, og vedlegg på utkast. Endepunktene som gjør utkast om til bokført kjøp eller salg (`createPurchase`, `createSale`), og alle andre skrivestier, avvises lokalt. Fiken-tillatelsen er bredere enn dette; sperren ligger i denne klienten. `FIKEN_READ_ONLY=1` slår av all skriving.
- Nedlasting godtar bare HTTPS på `fiken.no` og `api.fiken.no`, uten omdirigeringer. Ukjente dokumentverter avvises.
- Bilag lagres ikke på disk av serveren. Bilag og regnskapsdata som Claude leser sendes til Claude og omfattes av brukerens Claude-avtale. Det er ingen ekstra AI-tjeneste eller analyse-API i denne serveren.
- Dokumenttekst er ubetrodd innhold. Arbeidsflyten instruerer Claude om å ignorere instruksjoner i bilag, men menneskelig kontroll er fortsatt nødvendig.
- `fiken-mcp logout` sletter lokal innlogging. Tilbakekall appens tilgang under **Rediger konto → Sikkerhet → Apper du har gitt tilgang til** i Fiken for å ugyldiggjøre tilgangen hos Fiken.

## Feilsøking

- Manglende Client ID: sett `FIKEN_CLIENT_ID` både i terminalen og Claude-konfigurasjonen.
- HTTP 401 eller utløpt refresh-token: kjør `login` på nytt. Ved feil under lagring av rotert token må du også logge inn på nytt.
- HTTP 403: kontroller API-modul og appens foretakstilgang i Fiken.
- Port 8765 opptatt: avslutt en annen pågående innlogging og prøv igjen.
- Serveren er stille i Terminal: `serve` venter på MCP over standard input/output; dette er normalt.
- Skannet PDF uten tekst: be Claude bruke `fiken_read_document` med `as_image=true` for hver side.

## Utvikling og pilotstatus

```bash
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q
```

Tester dekker PKCE, refresh-rotasjon, offentlig OAuth-klient, skrivesperre utenfor utkast, utkastfelt og duplikatstopp, omdirigeringer, adresseregler, bilagslesing, datoer, sidegrenser, kontoplan på senere sider, ukjente mva-koder, duplikater og en virkelig MCP-stdio-oppstart. Alle regnskapsscenarier i testene er syntetiske; de dokumenterer ikke kvaliteten på Claudes tolkning av reelle bilag. GitHub Actions kjører på macOS og Windows med Python 3.11–3.13.

**Gjenstår før reell pilotgodkjenning:** registrer Fiken-appen, prøv innlogging og refresh med en testbruker, kontroller PDF/EHF mot testforetak, og prøv installasjonen i Claude Desktop. Ingen slike live-kontroller er dokumentert som bestått ennå. Repoet er en installerbar pilot, ikke en produksjonsgodkjent integrasjon.

MIT-lisens. Se [LICENSE](LICENSE). Sikkerhetsrapportering: se [SECURITY.md](SECURITY.md).
