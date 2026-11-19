# skill-budget-meter

Quanto del tuo **elenco delle skill** di Claude Code sta nel suo budget? Questo script lo misura dalle
trascrizioni già presenti sul tuo computer, nomina le skill rimaste senza descrizione e ti fa simulare
descrizioni più corte prima di installare qualsiasi cosa.

Un solo file Python · solo libreria standard · sola lettura · nessuna rete.

> **Progetto indipendente, non affiliato ad Anthropic.** Il budget è descritto nella documentazione ufficiale
> di Claude Code, [Skill descriptions are cut short](https://code.claude.com/docs/en/skills#skill-descriptions-are-cut-short):
> l'1% della finestra di contesto del modello. Il valore predefinito di 30.000 caratteri usato qui è una misura
> dell'autore (13 novembre 2026) con modelli da 1M di token di contesto: con un altro modello o altre
> impostazioni il tuo tetto è diverso, e qualsiasi aggiornamento può cambiare i dettagli.

[Read me in English](README.md)

> **Secondo modulo: [interference/](interference/).** Una skill nuova prende il posto di una vecchia
> nell'instradamento? Controllo lessicale in sola lettura di nomi e descrizioni delle tue skill,
> da fare prima di installare (metodo adattato da SKILL++,
> [arXiv:2611.00544](https://arxiv.org/abs/2611.00544)).

## Perché conta

All'avvio di una sessione Claude Code passa al modello l'elenco delle skill disponibili, una voce per skill:
`- nome: descrizione`. Il modello sceglie da sé una skill soltanto se la descrizione gli dice a che cosa serve.

Che cosa dice la documentazione ufficiale (la sezione citata sopra, letta il 13 novembre 2026):

- l'elenco ha un budget in caratteri pari all'**1% della finestra di contesto del modello**;
- i nomi delle skill ci sono sempre tutti, ma quando l'elenco sfora Claude Code toglie le descrizioni
  **cominciando dalle skill che invochi di meno**;
- ogni voce, `description` più `when_to_use`, ha un tetto di **1.536 caratteri**, qualunque sia il budget;
- il budget si alza con l'impostazione `skillListingBudgetFraction` (per esempio `0.02` = 2%) o si fissa in
  caratteri con la variabile d'ambiente `SLASH_COMMAND_TOOL_CHAR_BUDGET`; il tetto per voce è
  `skillListingMaxDescChars`; una skill impostata a `"name-only"` in `skillOverrides` compare senza
  descrizione. Le skill dei plugin non risentono di `skillOverrides`: si gestiscono con `/plugin`.

Due conseguenze, nella lettura dell'autore: una skill appena installata non è mai stata invocata, quindi è
facile che sia fra le prime a perdere la descrizione; e una skill poco importante impostata a `"name-only"`
lascia il suo spazio alle altre.

Una skill elencata con il solo nome resta installata, ma il modello ne vede solo il nome, quindi difficilmente
la sceglierà da sé. È facile non accorgersene.

## Accanto a /doctor e /context

Claude Code stesso stima in `/doctor` quanto contesto occupa l'elenco e chi pesa di più, mostra in
`/skill-doctor` quanto costa e quanto si usa ogni skill (dalla v2.1.252), riporta nella riga Skills di
`/context` la dimensione dell'elenco dopo il budget (dalla v2.1.196; prima contava ogni descrizione per
intero) e scrive un avviso nel log di debug (`--debug`) quando l'elenco supera il budget. Questo script
mostra:

- i **nomi** delle skill mostrate senza descrizione adesso;
- quanto sarebbe lungo l'elenco **con tutte le descrizioni**, così sai quanto tagliare;
- lo spazio che resta per le **tue** skill, separate da quelle dei plugin e da quelle integrate;
- lo **storico** dei tuoi elenchi e un tetto stimato (`--storico`);
- una **simulazione** di descrizioni nuove o più corte prima di installare o modificare qualsiasi cosa
  (`--simula`).

## Che cosa è stato misurato

Le sessioni dell'autore fino al 13/11/2026, 18:18 UTC, lette con questo script (`--storico --recenti 0`) e
aggregate dall'autore:

| | |
|---|---|
| Elenchi esaminati | 166 elenchi iniziali, dal 23/09 al 13/11/2026, Claude Code dalla 2.1.280 alla 2.1.321 (164 dall'app desktop, 2 dalla CLI) |
| Elenchi con almeno una skill senza descrizione | 163, **tutti fra 29.934 e 30.001 caratteri** (da 77 a 93 skill, da 1 a 37 senza descrizione) |
| Elenchi in cui stavano tutte le descrizioni | 3, fra 6.698 e 7.989 caratteri (da 15 a 17 skill) |
| 13/11/2026, 15:49 UTC | 30.001 caratteri, 91 skill, **37 senza descrizione** |
| Stesso giorno, 18:18 UTC, dopo aver accorciato le descrizioni dell'autore | 29.992 caratteri, 91 skill, **1 senza descrizione**; con tutte le descrizioni l'elenco sarebbe di 30.065 caratteri |

I modelli usati in queste sessioni hanno una finestra di contesto di 1M di token: circa 30.000 caratteri è ciò
che valeva il budget dell'1% in questa configurazione.

### Com'è andata dopo: da 37 skill senza descrizione a 0

La stessa configurazione, comprese le sessioni successive, letta con `--storico --recenti 0` il 19/11/2026 (Claude
Code da 2.1.321 a 2.1.326):

| Quando (UTC) | Elenco | Skill | Senza descrizione |
|---|---|---|---|
| 13/11/2026, 15:49 | 30.001 caratteri | 91 | **37** |
| 13/11/2026, 18:18 | 29.992 caratteri | 91 | **1** |
| 13/11/2026, 19:23 | 28.553 caratteri | 86 | **0** |
| 18/11/2026, 23:12 | 28.895 caratteri | 89 | **0** |

Che cosa ha cambiato l'autore nel frattempo (resoconto suo: lo script mostra solo il risultato), in quest'ordine:
ha accorciato le descrizioni a una riga ciascuna, provando ogni modifica con `--simula` prima di installarla, e le
skill senza descrizione sono scese da 37 a 1; ha tolto cinque skill d'esempio che non usava (da 91 a 86 skill); ha
alzato `skillListingBudgetFraction` a `0.02`. Gli 81 elenchi dalle 19:17 UTC del 13/11 alle 23:12 UTC del 18/11 (da
27.654 a 29.327 caratteri, da 74 a 90 skill) hanno tenuto tutte le descrizioni e sarebbero stati anche nel vecchio
budget di circa 30.000 caratteri: qui la frazione alzata è margine, non ciò che ha portato a 0. È la configurazione
di un solo utente, non una promessa per la tua: lancia lo script sulle tue trascrizioni.

## Per cominciare

Serve Python 3.10 o successivo. Scarica `skill_budget_meter.py` e lancia:

```
python skill_budget_meter.py --prime 5
```

Su macOS e Linux usa `python3 skill_budget_meter.py --prime 5`; su Windows va bene anche `py`. Con Python
dalla 3.7 alla 3.9 lo script dice che serve la 3.10 e si ferma; le versioni più vecchie si fermano con un
errore di sintassi. Esempio di uscita (dati sintetici, prodotti dallo script stesso):

```
skill-budget-meter 1.1.0 · elenco iniziale del 2026-01-15 09:00 UTC · Claude Code 2.1.0 (claude-desktop) · sessione demo0001
Elenco reale: 29.620 caratteri (tetto 30.000) · 90 skill · con descrizione 84 · SENZA 6
  Senza descrizione: car-service, pet-care, gift-ideas, event-planner, letter-writer, project-diary
Con tutte le descrizioni: 31.335 caratteri · obiettivo 29.400 (tetto 30.000 meno margine 600) · OLTRE di 1.935
  tue          20 skill ·   5.951 caratteri · senza descrizione 6
  di terzi     55 skill ·  18.179 caratteri · senza descrizione 0
  integrate    15 skill ·   7.206 caratteri · senza descrizione 0
  Spazio per le tue skill: 4.016 caratteri; oggi ne usano 5.951 (da tagliare 1.935)
Descrizioni più lunghe:
   1.  1.390  review-changes  (integrate)
   2.  1.180  chart-maker  (integrate)
   3.  1.150  schedule-runner  (integrate)
   4.    610  loop-runner  (integrate)
   5.    455  dev-kit:skill-08  (di terzi)
Esito: skill senza descrizione: 6. Il modello ne vede solo il nome, quindi difficilmente le sceglierà da sé: accorcia le descrizioni più lunghe e verifica con --simula.
```

I messaggi seguono la lingua del sistema (italiano o inglese); per sceglierla usa `--lingua it` o `--lingua en`.

## Opzioni

Ogni opzione tranne `--json` ha due nomi, uno italiano e uno inglese.

| Opzione | Predefinito | Che cosa fa |
|---|---|---|
| `--simula` / `--simulate FILE` | | Simula descrizioni nuove, cambiate o tolte (vedi sotto) |
| `--modello` / `--template` | | Stampa in JSON le tue skill con le descrizioni attuali, pronte da modificare |
| `--storico` / `--history` | | Una riga per ogni elenco iniziale trovato, poi il tetto stimato (vedi Limiti) |
| `--tetto` / `--cap N` | 30000 | Tetto dell'elenco in caratteri. Il budget è l'1% della finestra di contesto, che si conta in token: misura il tuo tetto con `--storico` invece di calcolarlo |
| `--margine` / `--margin N` | 600 | Margine di sicurezza: l'obiettivo è il tetto meno il margine |
| `--max-voce` / `--entry-cap N` | 1536 | Tetto di ogni voce, descrizione più `when_to_use`, come `skillListingMaxDescChars` |
| `--prime` / `--top N` | 10 | Quante descrizioni più lunghe mostrare |
| `--mie` / `--mine MODELLO` | | Segna come tue delle skill di plugin, per esempio `"mio-plugin:*"` (ripetibile; ammesse le virgole) |
| `--cartella` / `--dir CARTELLA` | | Cartella in più dove cercare i `SKILL.md` (ripetibile) |
| `--trascrizioni` / `--transcripts CARTELLA` | `<config>/projects` | Dove sono le trascrizioni |
| `--recenti` / `--recent N` | 40 | Quante sessioni recenti leggere (0 = tutte) |
| `--json` | | Uscita per i programmi |
| `--lingua` / `--lang it\|en` | del sistema | Lingua dei messaggi |
| `--versione` / `--version` | | Mostra la versione |

`<config>` è `$CLAUDE_CONFIG_DIR` se è impostata, altrimenti `~/.claude`.

## Simula prima di installare

1. `python skill_budget_meter.py --modello > nuove.json` stampa le tue skill con le descrizioni attuali
   (tutte le skill, se nessuna viene riconosciuta come tua).
2. Modifica `nuove.json`: accorcia le descrizioni, aggiungi `"plugin:skill-nuova": "..."` per una skill che
   vuoi installare, metti `null` a una skill per simularne la rimozione. Vedi `examples/simulate.example.json`.
3. `python skill_budget_meter.py --simula nuove.json` confronta il totale simulato con l'obiettivo. Il
   rapporto nomina le skill che tratta come nuove, così un nome scritto male non diventa in silenzio una skill
   nuova.

Con `--simula` il codice di uscita riflette solo la simulazione: 0 entro l'obiettivo, 3 oltre, anche quando
nell'elenco misurato ci sono skill senza descrizione.

Un nome senza il prefisso del plugin vale per la skill con quel nome corto, purché sia una sola ad averlo.
Il file può essere in UTF-8 o in UTF-16, come lo scrive Windows PowerShell 5.

Esempio (stessi dati sintetici, le 20 skill dell'utente accorciate a circa 110 caratteri ciascuna; ultime
righe dell'uscita):

```
Elenco misurato: skill senza descrizione: 6.
Simulazione (nuove.json): 27.925 caratteri · cambiate 20 · nuove 0 · tolte 0 · ENTRO, restano 1.475
Esito della simulazione: entro l'obiettivo (uscita 0: riflette solo la simulazione).
```

## Come scrivere descrizioni più corte

- Una riga: che cosa fa la skill e quando usarla; le parole che la attivano in fondo.
- L'uso principale va per primo: oltre 1.536 caratteri (descrizione più `when_to_use`) la voce viene tagliata
  comunque.
- Niente numeri di versione, date o changelog: stanno nel corpo del `SKILL.md`.
- Anche procedure, esempi e dettagli vanno nel corpo: il modello lo legge solo dopo aver scelto la skill.
- Dai più spazio alle skill su cui conti di più. La regola pratica dell'autore: circa 170 caratteri per le
  skill fondamentali, circa 80 per le altre.
- Dopo l'installazione misura di nuovo in una sessione nuova: l'elenco si forma quando la sessione parte, e
  una skill nuova, mai invocata, è facile che sia fra le prime a perdere la descrizione.

## Come funziona

- Legge `<config>/projects/*/*.jsonl`, le trascrizioni che Claude Code scrive (per default le 40 più recenti).
- Cerca gli allegati di tipo `skill_listing`. Misura solo gli elenchi **iniziali**: gli aggiornamenti a metà
  sessione (`isInitial: false`) contengono solo le skill cambiate, e misurarne uno darebbe un falso «tutto
  bene». Gli elenchi dei sotto-agenti sono esclusi.
- Prende l'elenco iniziale più recente e lo divide in skill con il suo campo `names`: una descrizione può
  occupare più righe. Se quel campo non corrisponde al testo, divide con lo schema `- nome:` e lo segnala.
- Se l'elenco ha skill senza descrizione ma è più corto del 90% del tetto, il rapporto avvisa che il tetto è
  probabilmente sbagliato per il tuo modello, oppure che quelle skill sono name-only.
- Per una skill mostrata senza descrizione cerca il testo completo nei `SKILL.md`: in `<config>/skills`, nella
  cartella `.claude/skills` del progetto della sessione, in `<config>/plugins` e in `--cartella` (fino a 7
  livelli di profondità, seguendo i link simbolici, ogni cartella una volta sola), e accanto alle skill
  caricate nelle sessioni recenti (le skill vicine e quelle dei plugin accanto al loro). Un `SKILL.md` con la
  descrizione vuota non conta. Altrimenti usa l'elenco più recente, di qualsiasi sessione letta su questo
  computer, in cui la skill era mostrata.
- Il testo completo di una voce è la sua `description`, uno spazio e il suo `when_to_use`, tagliato al tetto
  per voce.
- Classi: **tue** (skill personali e di progetto, più `--mie`), **di terzi** (skill dei plugin),
  **integrate** (senza prefisso di plugin e senza `SKILL.md` trovato).

## Limiti

- Il formato delle trascrizioni non è un'interfaccia documentata e un aggiornamento può cambiarlo. Lo script
  avvisa quando non riesce a ricostruire l'elenco al carattere.
- Il tetto dipende dal tuo modello e dalle tue impostazioni: 30.000 è la misura dell'autore, non una costante.
  La finestra di contesto si conta in token e il tetto in caratteri, quindi il tetto va misurato e non
  calcolato: `--storico` ne dà una stima dai tuoi elenchi.
- Quella stima vale solo se nessuna tua skill è name-only o priva di descrizione; con più modelli è il tetto
  più alto visto.
- Quali descrizioni vengono tolte dipende da quanto invochi ogni skill, e lo script non può vederlo: riporta
  le skill nascoste adesso e il totale pieno, non quali saranno nascoste dopo.
- Il totale pieno è una stima quando usa il testo dei `SKILL.md`, che può differire da quello mostrato
  nell'elenco (modificato dopo, o scritto diversamente): il rapporto dice quante descrizioni mostrate
  differiscono dal loro `SKILL.md`. Anche il modo in cui l'app unisce `description` e `when_to_use` non è
  documentato: lo script le unisce con uno spazio.
- I caratteri sono contati come punti di codice Unicode. Se l'app conta in unità UTF-16, un'emoji vale due;
  il rapporto mostra entrambi i conteggi quando differiscono.
- Legge solo le sessioni salvate su questo computer. Il tetto è stato osservato nell'app desktop; nella CLI
  l'autore non ha mai avuto abbastanza skill per raggiungerlo.
- Una skill nascosta senza `SKILL.md` sul disco e senza un elenco precedente rende il totale pieno una stima
  per difetto: il rapporto la nomina.
- Provato su Windows 10 con Python 3.14; non ancora provato su macOS e Linux. I test controllano anche che la
  sintassi si legga con Python 3.7, perché le versioni più vecchie arrivino al controllo della versione.

## Privacy

- Legge solo file locali, non scrive nulla e non usa mai la rete. I test controllano che nel sorgente non ci
  siano chiamate di rete, di processi o di scrittura.
- Le cartelle delle skill vengono prese solo dai messaggi con cui l'app carica le skill, mai da risultati di
  strumenti o pagine web finiti in una trascrizione. I percorsi di rete UNC trovati nelle trascrizioni (come
  `\\server\share`, comunque scritti) sono ignorati.
- L'uscita contiene i nomi delle tue skill, le loro descrizioni (con `--modello`) e l'id della sessione
  (intero con `--json`): guardala prima di condividerla.

## Codici di uscita

| Codice | Significato |
|---|---|
| 0 | Fatto, niente da segnalare; anche `--storico` e `--modello` quando trovano un elenco |
| 1 | Nessun elenco iniziale trovato |
| 2 | Errore d'uso o di input |
| 3 | Una skill senza descrizione nell'elenco misurato, qualunque sia il motivo (budget, name-only, descrizione assente) |

Con `--simula` il codice di uscita riflette solo la simulazione: 0 entro l'obiettivo, 3 oltre.

## Test

```
python -m unittest discover -s tests -v
```

Su macOS e Linux usa `python3`. I test usano solo trascrizioni sintetiche, compreso un aggiornamento a metà
sessione da ignorare; nessun test legge la tua vera cartella di Claude. Il test dei link usa un link simbolico
o, su Windows senza il permesso di crearlo, una giunzione; viene saltato solo dove non si può né l'uno né
l'altra.

## Kit Regia

Questo strumento viene dal **Kit Regia** dell'autore, un insieme personale di skill e script che, prima di
ogni compito, sceglie le skill, il modello e l'effort giusti e tiene bassi i costi. Domande, idee o interesse
per il kit: apri una Issue in questo repository.

## Licenza

MIT, © 2026 Gianluca Vega: vedi [LICENSE](LICENSE).
