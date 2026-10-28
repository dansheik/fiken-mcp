# Endringslogg

## Uutgitt

- Lagt til `fiken_get_journal_entry` og `fiken_read_journal_entry_attachment` for å lese journalposter og vedlegg, f.eks. mellombalanse ved inngående balanse.

## 0.3.0 – 2026-10-28

- Rettet manglende obligatorisk dato for kontosaldoer.
- Paginerte lister returnerer nå data og sidemetadata. Kontoplan støtter sidevalg.
- Lagt til lesing av enkeltkjøp, kjøpsutkast, vedlegg, kontakter og bankkontoer.
- Lagt til leverandørhistorikk og heuristisk duplikatsøk uten datogrense.
- Konteringskontroll sjekker normalt kontoplan og mulige duplikater i Fiken,
  og skiller disse fra aritmetikk og gjenkjenning av numeriske kjøps-mvakoder.
- Automatisk lesing har eksplisitt sidegrense og rapporterer ufullstendige søk.
- Lagt til lokale `config`- og `doctor`-kommandoer for Claude-oppsett.
- Beholder GET-sperre, OAuth/PKCE og Nøkkelring. Ingen skriveverktøy.

Endringer som påvirker klienter: listeformat er `{data, pagination}`, `date`
er obligatorisk for kontosaldo, og validering bruker nettverk som standard.
`check_fiken=false` beholder lokal aritmetikk-/kodekontroll.

Ekte Fiken-innlogging, bilagsflyt og Claude Desktop må fortsatt testes med en
registrert PKCE-app. Ingen produksjonsgodkjenning eller skattefaglig godkjenning.
