# Fiken i Claude – oppsett på Windows

Denne veiledningen kobler Claude til Fiken på din Windows-PC. Da kan Claude lese bilag og lagre kjøp og salg som utkast i Fiken. Du kontrollerer og bokfører alltid selv.

## Før du starter

Du trenger:

- En Windows 10- eller 11-PC der du kan installere programmer.
- Claude-appen, installert og innlogget.
- Din egen Fiken-innlogging, med tilgang til foretaket.
- En **klient-ID**. Den får du av den som administrerer Fiken-koblingen.
- Omtrent 15 minutter.

Alt gjøres ved å kopiere ferdige linjer inn i et program som heter **PowerShell**. Du trenger ikke forstå hva linjene gjør.

**Slik åpner du PowerShell:** Trykk på Windows-tasten, skriv `PowerShell` og trykk Enter. Et blått eller svart vindu åpnes.

**Slik limer du inn:** Kopier de grå linjene i veiledningen. Klikk i PowerShell-vinduet og trykk Ctrl + V. Trykk Enter. Vent til linjen som slutter med `>` dukker opp igjen før du går videre.

Kommer det rød tekst, gå til «Hvis noe går galt» nederst.

## Første gangs oppsett

Gjør stegene i rekkefølge. Hvert steg gjøres bare én gang per PC.

### Steg 1: Installer hjelpeprogrammene

Lim inn disse to linjene i PowerShell:

```powershell
winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
winget install -e --id Git.Git --accept-source-agreements --accept-package-agreements
```

Spør Windows «Vil du tillate at denne appen gjør endringer?», klikker du **Ja**. Når begge er ferdige: **lukk PowerShell-vinduet og åpne et nytt**. Ellers finner ikke PC-en programmene.

### Steg 2: Last ned Fiken-koblingen

Lim inn i det nye PowerShell-vinduet:

```powershell
cd $HOME
git clone https://github.com/dansheik/fiken-mcp.git
cd fiken-mcp
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
```

Dette tar et par minutter. Det er normalt at mye tekst ruller forbi.

### Steg 3: Logg inn i Fiken

Kopier linjene under inn i Notisblokk først. Bytt ut `LIM-INN-KLIENT-ID-HER` med klient-ID-en du har fått. Behold de enkle anførselstegnene. Kopier så alt inn i PowerShell:

```powershell
cd $HOME\fiken-mcp
$env:FIKEN_CLIENT_ID = 'LIM-INN-KLIENT-ID-HER'
.\.venv\Scripts\fiken-mcp.exe login
```

Nettleseren åpner Fiken. Logg inn, kryss av for foretakene du jobber med, og godkjenn. Du har tre minutter på deg. Når nettleseren sier at innloggingen er fullført, går du tilbake til PowerShell.

Sjekk at det virket:

```powershell
.\.venv\Scripts\fiken-mcp.exe doctor
```

Du skal se `"status": "ok"`.

### Steg 4: Koble Fiken til Claude

Bruk **samme PowerShell-vindu** som i steg 3. Lim inn:

```powershell
[Console]::OutputEncoding = [Text.Encoding]::UTF8; $env:PYTHONUTF8 = '1'
.\.venv\Scripts\fiken-mcp.exe config | Set-Clipboard
```

Nå ligger innstillingene for Claude i utklippstavlen. Gjør så dette:

1. Åpne Claude-appen. Klikk på menyen øverst til venstre og velg **Settings** → **Developer** → **Edit Config**.
2. Et mappevindu åpnes med filen `claude_desktop_config.json` markert. Høyreklikk filen og velg **Åpne med** → **Notisblokk**.
3. Se på innholdet i Notisblokk:
    - **Tom fil, eller bare `{}`:** Trykk Ctrl + A, så Ctrl + V, så Ctrl + S. Lukk Notisblokk.
    - **Det står allerede annen tekst der:** Ikke endre noe. Lukk Notisblokk uten å lagre, og kontakt den som administrerer Fiken-koblingen.

### Steg 5: Start Claude på nytt

Det holder ikke å trykke på krysset. Claude må avsluttes helt:

1. Finn Claude-ikonet nede til høyre ved klokken. Ligger det ikke der, klikk på den lille pilen `^`.
2. Høyreklikk ikonet og velg **Quit** (Avslutt).
3. Åpne Claude igjen.

Skriv til Claude: «List foretakene jeg har tilgang til i Fiken.» Får du en liste med foretak, er alt klart.

## Oppdatere til ny versjon

Gjør dette når du får beskjed om at det finnes en ny versjon. Du trenger ikke logge inn på nytt.

Åpne PowerShell og lim inn:

```powershell
cd $HOME\fiken-mcp
git pull
.\.venv\Scripts\python.exe -m pip install .
```

Avslutt deretter Claude helt og åpne det igjen, som i steg 5.

## Slik bruker du det

Si alltid hvilket foretak det gjelder. Eksempler på hva du kan skrive til Claude:

- «Lag konteringsforslag for Hira Trading Company AS: Egil Jensen AS faktura 245458.»
- «Lagre forslaget som kjøpsutkast i Fiken. Ikke bokfør.»
- «Lag salgsutkast for Z-rapport løpenummer 496.»

Claude finner bilaget i innboksen, foreslår konto og mva, og lagrer det som utkast med bilaget vedlagt. Claude kan **ikke** bokføre.

**Kontroller og bokfør selv:** Åpne Fiken, finn utkastet under **Kjøp** eller **Salg**, se over det, og trykk **Bokfør** når alt stemmer.

**Når Claude spør om lov:** Første gang Claude bruker Fiken, kommer det et spørsmål.

| Claude vil … | Velg |
| --- | --- |
| lese noe (list, get, read, find) | **Always allow** |
| lage, endre eller slette et utkast (create, update, delete, attach) | **Allow once**, så godkjenner du hvert utkast |

Spør Claude om å bruke **nettleseren** på fiken.no, klikker du **Deny**. Da kjører du en gammel versjon. Oppdater som beskrevet over.

## Hvis noe går galt

| Du ser | Gjør dette |
| --- | --- |
| `winget`, `git` eller `py` «is not recognized» | Lukk PowerShell og åpne et nytt vindu. Hjelper ikke det, gjør steg 1 på nytt og start PC-en på nytt. |
| «fiken-mcp.exe is not recognized» eller «cannot find path» | Du står i feil mappe. Lim inn `cd $HOME\fiken-mcp` og prøv igjen. |
| «destination path 'fiken-mcp' already exists» | Koblingen er allerede lastet ned. Hopp over steg 2. |
| «Sett FIKEN_CLIENT_ID til ID-en …» | Klient-ID-en mangler i dette vinduet. Gjør steg 3 på nytt, og steg 4 i samme vindu. |
| Innloggingen stopper eller «timed out» | Kjør steg 3 på nytt og fullfør innloggingen i nettleseren innen tre minutter. |
| HTTP 401 | Innloggingen er utløpt. Gjør steg 3 på nytt. Det samme gjelder «Ikke innlogget» eller «Fiken avviste innlogging». |
| HTTP 403 | Foretaket mangler API-tilgang i Fiken. Kontakt den som administrerer Fiken. |
| Claude kjenner ikke Fiken | Avslutt Claude helt via ikonet ved klokken (steg 5), og åpne igjen. |
| Claude vil bruke nettleseren på fiken.no | Klikk **Deny** og oppdater koblingen. |

Sitter du fast, ta et skjermbilde av PowerShell-vinduet og send det til den som administrerer Fiken-koblingen.
