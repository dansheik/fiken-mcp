# Fiken MCP for Claude på Mac

Lokal, skrivebeskyttet MCP-server for Claude Desktop og Claude Code. Hver bruker logger inn med sin egen Fiken-konto gjennom **OAuth 2.0 med PKCE (S256)**. Tokens lagres i macOS Nøkkelring.

**Pilot:** les bilag og få forslag til full kontering. Claude tolker bilaget og foreslår kontoer og mva; serveren gir datagrunnlag og kontrollerer regnestykket. Ingenting bokføres, endres, slettes eller sendes i Fiken. Ikke en offisiell Fiken-integrasjon.

## Hva piloten kan gjøre

- Lese foretak, kontoplan, saldoer, kontakter, fakturaer, kjøp, salg og journalposter.
- Lese innboksbilag som PDF, PNG og JPEG; PDF kan leses som tekst eller sidebilder for skannede bilag. Maks 15 MiB per svar.
- Lese strukturerte EHF-fakturaer og kreditnotaer.
- Gi Claude en arbeidsflyt for full kontering med kostnad/eiendel, mva og motkonto, bilagsreferanser, begrunnelse og åpne spørsmål.
- Kontrollere debet/kredit og bruttobeløp for enkle NOK-bilag. Kontrollen bekrefter ikke skattebehandling eller kontovalget. Mer kompliserte bilag og valuta må vurderes separat.

## 1. Registrer Fiken-appen én gang

Repoeier registrerer en offentlig app i Fiken og deler dens **Client ID** med pilotbrukerne. Hver bruker gir deretter sin egen tilgang. Alternativt kan en bruker registrere sin egen app.

1. Aktiver utvikler under **Rediger konto → Profil → Andre innstillinger**.
2. Opprett app under **Brukerinnstillinger → API**.
3. Velg **Avanserte innstillinger → Uten client secret (PKCE)** ved opprettelse.
4. Registrer nøyaktig denne redirect-adressen: `http://127.0.0.1:8765/callback`.
5. Ta vare på Client ID. Den er offentlig, men er ikke forhåndsutfylt i dette repoet.

Brukere må ha Fiken API-tilgang til foretakene sine. Fiken dokumenterer inntil fem brukere i utviklingsfasen, og krever 2–3 reelle pilotbrukere før søknad om produksjonstilgang. Se [Fikens API-dokumentasjon](https://api.fiken.no/api/v2/docs/) for gjeldende vilkår og appregistrering.

## 2. Installer lokalt

Krever macOS, Git og Python 3.11 eller nyere. Har du Homebrew, kan Python installeres med `brew install python@3.12`.

```bash
git clone https://github.com/dansheik/fiken-mcp.git
cd fiken-mcp
python3.12 -m venv .venv
.venv/bin/python -m pip install .
export FIKEN_CLIENT_ID='DIN_OFFENTLIGE_CLIENT_ID'
.venv/bin/fiken-mcp login
```

Innloggingen åpner nettleseren. Velg hvilke foretak appen skal få tilgang til. Callback-serveren lytter bare på `127.0.0.1:8765` under innlogging, og venter i inntil tre minutter. Nøkkelring kan be om lokal tilgang. Ingen token skal kopieres til Claude-konfigurasjonen.

## 3. Koble til Claude Desktop

Åpne **Settings → Developer → Edit Config**. Konfigurasjonsfilen på Mac heter `~/Library/Application Support/Claude/claude_desktop_config.json`.

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

Se [Claude Codes MCP-dokumentasjon](https://code.claude.com/docs/en/mcp).

## Bruk

Start med: «List foretakene jeg har tilgang til i Fiken.» Velg foretak uttrykkelig. Deretter:

> Les ubrukte bilag i innboksen for foretaket. Analyser ett bilag om gangen. Les alle sider, hent kontoplanen og foreslå full kontering med konto, debet, kredit, mva, motkonto og begrunnelse. Oppgi usikkerheter og kontroller for duplikat. Ikke bokfør noe.

MCP-prompten `foresla_kontering` gir denne arbeidsflyten med `company_slug` og `document_id`. Verktøyet `fiken_validate_posting_proposal` tar et strukturert forslag fra Claude og returnerer alltid et utkast som krever menneskelig kontroll. Beløp er heltall i øre. Listeverktøy har nullbasert `page`; les videre til en tom side. PDF-sider starter på 1. Kontoplanverktøyet følger API-ets egne kontofiltre.

## Personvern og sikkerhetsgrenser

- OAuth er per macOS-bruker og Client ID. Ingen personlig API-token eller client secret brukes.
- Tilgangs- og refresh-token lagres samlet i Nøkkelring. Rotering og API-kall serialiseres mellom lokale prosesser med fillås. Bytte av Fiken-bruker gjøres med ny `login`.
- Regnskaps-API-et har bare GET-transport. OAuth-tokenutveksling er eneste HTTP POST. Fiken-tillatelsen kan være bredere enn lesetilgangen serveren tilbyr; sperren ligger i denne klienten.
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

Tester dekker PKCE, refresh-rotasjon, offentlig OAuth-klient, GET-sperre, omdirigeringer, adresseregler, bilagslesing, konteringsbalanse og en virkelig MCP-stdio-oppstart. GitHub Actions kjører på macOS med Python 3.11–3.13.

**Gjenstår før reell pilotgodkjenning:** registrer Fiken-appen, prøv innlogging og refresh med en testbruker, kontroller PDF/EHF mot testforetak, og prøv installasjonen i Claude Desktop. Ingen slike live-kontroller er dokumentert som bestått ennå. Repoet er en installerbar pilot, ikke en produksjonsgodkjent integrasjon.

MIT-lisens. Se [LICENSE](LICENSE). Sikkerhetsrapportering: se [SECURITY.md](SECURITY.md).
