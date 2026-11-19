# skill-interference

Una skill nuova rompe l'instradamento di quelle che hai già? Questo script confronta nomi e descrizioni delle
tue skill di Claude Code, trova le coppie che si somigliano e ti dice, prima di installare una skill nuova, se
rischia di prendere il posto di una vecchia.

Secondo modulo di **skill-budget-meter**. Un solo file Python · solo libreria standard · sola lettura · nessuna rete.

> **Da leggere per primo: la sonda non è il router di Claude.** Claude sceglie una skill con un modello
> linguistico che legge nomi e descrizioni; questo script conta parole (coseno TF-IDF e BM25). I suoi numeri
> servono a confrontare due versioni dei *tuoi* metadati, prima e dopo una modifica; non certificano che
> Claude sceglierà la skill giusta.

> **Progetto indipendente, non affiliato ad Anthropic.** Metodo adattato da Zhang et al., *SKILL++: Towards
> Lifelong Agents via Routing-Aware Skill Refinement*, [arXiv:2611.00544](https://arxiv.org/abs/2611.00544)
> (31 ottobre 2026). Nessun codice del paper è incluso; le misure lessicali sostituiscono gli embedding del
> paper e le soglie sono dell'autore.

[Read me in English](README.md): opzioni, esempi con l'uscita vera, limiti e codici di uscita.

## In breve

- **Sostituzione**: una skill nuova simile a una vecchia le toglie il posto nella scelta del router.
- **Affollamento**: skill generiche o doppioni riempiono i pochi posti fra cui il router sceglie.

```
python skill_interference.py                                    # controlla <config>/skills
python skill_interference.py --library esempio/library --cases esempio/probe_cases.jsonl
python skill_interference.py --library esempio/library --new esempio/incoming/invoice-audit   # uscita 1 = rischio
python skill_interference.py --library esempio/library --try-descriptions esempio/try_descriptions.json
```

Le clausole di esclusione si riconoscono in inglese e in italiano («Non per …», «Non copre …»). I messaggi
dello script sono in inglese; le opzioni principali hanno anche il nome italiano (`--libreria`, `--casi`,
`--nuova`, `--tetto`, `--uscita`).

## Licenza

MIT, © 2026 Gianluca Vega: vedi [LICENSE](LICENSE).

## Supporta il progetto

Se questo strumento ti ha fatto risparmiare tempo, puoi sostenerne lo sviluppo su Ko-fi:
[ko-fi.com/gianlucavega](https://ko-fi.com/gianlucavega). Grazie!
