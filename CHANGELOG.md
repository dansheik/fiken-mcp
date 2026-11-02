# Endringslogg

## 0.4.0 – 2026-11-02

- Nye skriveverktøy, bare for utkast: `fiken_create_purchase_draft`, `fiken_create_sale_draft`,
  `fiken_update_purchase_draft`, `fiken_update_sale_draft`, `fiken_attach_inbox_document_to_draft`,
  `fiken_delete_purchase_draft` og `fiken_delete_sale_draft`.
- Nye leseverktøy: `fiken_list_sale_drafts` og `fiken_get_sale_draft`.
- Skrivetransporten har en hviteliste for utkast-stier. Bokføring (`createPurchase`/`createSale`)
  og all annen skriving avvises før forespørselen sendes.
- Lokal kontroll før lagring: linjesum mot bilagets total, mva-frie linjer, betalinger, forfall
  og mulige duplikater blant utkast og bokførte kjøp/salg.
- Innboksbilag legges ved utkastet. Godtar ikke Fiken direkte kobling, lastes en kopi opp.
- Serverinstruksjonene ber Claude bruke utkastverktøyene i stedet for nettleseren.
- `FIKEN_READ_ONLY=1` gir den gamle skrivebeskyttede oppførselen.

## 0.3.1 – 2026-10-30

- Windows-støtte med Credential Manager, plattformuavhengig prosesslås og riktig `.exe` i Claude-konfigurasjon.
- PowerShell-instruksjoner og forklaring av lokal HTTP-redirect for offentlige PKCE-apper.
- Testmatrise på macOS og Windows.

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
