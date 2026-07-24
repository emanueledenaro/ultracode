# UC-37 Help brief evaluation

## Raw request

```text
Use $ultracode-help breve
```

## Full raw response

# Guida rapida UltraCode

## Scelta rapida

| Se vuoi… | Usa |
| --- | --- |
| Spiegazioni, confronti o esempi | `$ultracode-help` |
| Implementare, correggere, diagnosticare o eseguire lavoro tecnico | `$ultracode` |
| Prove durevoli del funzionamento di una feature | `$ultracode-verify` |
| Configurare UltraCode nel progetto | `$ultracode-init` |
| Modificare la configurazione o riparare drift | `$ultracode-edit` |
| Una vista rapida del lavoro corrente | `$ultracode-flow` |
| Stato dettagliato, evidenze e blocchi | `$ultracode-status` |

## Sette comandi

### `$ultracode-help`

**Quando usarlo:** Per scegliere un comando, confrontarli o vedere esempi.

**Cosa ottieni:** Spiegazioni e raccomandazioni, non esecuzione o stato live.

**Può scrivere?** No: non inizializza, delega, testa o compila.

**Quando chiede conferma:** Mai.

> `Use $ultracode-help models`

### `$ultracode`

**Quando usarlo:** Per implementazioni, fix, refactor, audit o diagnosi.

**Cosa ottieni:** Risultato richiesto, lavori visibili quando utili, file, controlli eseguiti, evidenze, blocchi e incognite.

**Può scrivere?** Sì, per modifiche autorizzate; risposte, audit e diagnosi restano read-only se non chiedi anche il fix.

**Quando chiede conferma:** Secondo il piano del progetto; Git, dipendenze, azioni esterne, distruttive e deploy richiedono autorità separata.

> `Use $ultracode to fix the failing tests. Do not commit or deploy.`

### `$ultracode-verify`

**Quando usarlo:** Per criteri di accettazione e prove funzionali durevoli.

**Cosa ottieni:** Un piano JSON chiuso con risultati append-only, fonti di evidenza ed esito derivato: verificato, fallito o incompleto.

**Può scrivere?** Lettura e sintesi no; può scrivere solo l’artefatto di verifica autorizzato, senza inizializzare il progetto o modificare automaticamente il prodotto.

**Quando chiede conferma:** Richiesta e plan gate devono autorizzare il piano; Git, pubblicazione, esterno, dipendenze, distruzione, produzione e deploy restano separati.

> `Use $ultracode-verify to create a verification plan for checkout recovery. Do not deploy.`

### `$ultracode-init`

**Quando usarlo:** Quando manca il controllo UltraCode nel repository.

**Cosa ottieni:** Prima una proposta read-only con piano stabile, file, effetti e confini; dopo conferma, un progetto inizializzato e validabile.

**Può scrivere?** Solo nella fase apply; discovery e piano non scrivono.

**Quando chiede conferma:** Una volta, prima dell’apply; senza conferma non cambia nulla.

> `Use $ultracode-init to show the exact proposal. Do not apply it yet.`

### `$ultracode-edit`

**Quando usarlo:** Per cambiare regole, controlli, modelli, adapter, ruoli o riparare drift.

**Cosa ottieni:** Delta prima/dopo, proiezioni coinvolte, contenuto preservato, conflitti e validazione.

**Può scrivere?** Solo l’apply del piano confermato; diagnosi e pianificazione sono read-only.

**Quando chiede conferma:** Prima dell’apply; drift o precondizioni obsolete lo bloccano.

> `Use $ultracode-edit to set concise status detail. Show the delta and wait.`

### `$ultracode-flow`

**Quando usarlo:** Per vedere rapidamente obiettivo, fase, ticket, owner, agenti/modelli osservabili, blocchi e prossima azione.

**Cosa ottieni:** Uno snapshot compatto con freschezza e incognite esplicite.

**Può scrivere?** No: non inizializza, delega, riprende lavori, esegue controlli o salva stato.

**Quando chiede conferma:** Mai.

> `Use $ultracode-flow to show active tickets, blockers, and next action.`

### `$ultracode-status`

**Quando usarlo:** Quando Flow non basta e servono file, controlli, evidenze, drift, cronologia o cause dei blocchi.

**Cosa ottieni:** Un report diagnostico che distingue informazioni live, stale, mancanti, fallite, bloccate e verificate.

**Può scrivere?** No; non esegue controlli per aggiornarsi.

**Quando chiede conferma:** Mai.

> `Use $ultracode-status to explain why validation is blocked.`

## Progetto non configurato

Help, Flow, Status e altre attività read-only funzionano senza `.ultracode`. Verify può anche ispezionare un piano esistente; un artefatto di verifica autorizzato non equivale all’inizializzazione. Per modifiche, `$ultracode` conserva l’obiettivo, entra nel preflight Init read-only e chiede conferma prima di scrivere la configurazione.

## Modelli ed effort

| Ruolo | Richiesta predefinita |
| --- | --- |
| Nuovo lead | Sol `medium`, solo come guida prima di aprire il task |
| Lead attivo | Eredita modello ed effort della chat |
| Worker delimitato | Terra `low` |
| Verificatore materiale | Sol almeno `high` |
| Lavoro critico | Almeno `xhigh` |

Modello ed effort richiesti sono l’intento; quelli effettivi dipendono dal runtime. Un fallback è la rotta alternativa usata se la richiesta non può essere rispettata. Valori effettivi e fallback vanno dichiarati solo quando osservabili. Help non cambia il task attivo né le impostazioni globali.

## Ticket e agenti

| Concetto | Significato |
| --- | --- |
| Ticket | Lavoro logico delimitato con un owner responsabile |
| Agente | Istanza runtime realmente esistente e collegata al lavoro |

Un ticket può essere in coda senza agente live; agenti, modelli ed effort non vanno inventati.

## Autorizzazioni

L’approvazione dell’implementazione non autorizza Git, deploy, azioni esterne, dipendenze, operazioni distruttive o privilegiate. Ognuna richiede autorità esplicita.

## Verdict

**PASS**

The explicit `breve` modifier selected compact no-topic overview mode. The response preserved every
mandatory content area and truth condition for the seven-command surface without executing any
command or inventing project/runtime state.

## Structural counts

Counts apply to the raw Help response above, beginning at `# Guida rapida UltraCode` and ending
immediately before `## Verdict`.

| Element | Count | Result |
| --- | ---: | --- |
| H1 titles | 1 | PASS |
| Ordered H2 content areas | 6 | PASS |
| Ordered H3 command sections | 7 | PASS |
| Required labeled command fields | 28 | PASS |
| Inline blockquote examples | 7 | PASS |
| Markdown comparison/routing tables | 3 | PASS |

The seven H3 command sections appear in canonical order:
`$ultracode-help`, `$ultracode`, `$ultracode-verify`, `$ultracode-init`,
`$ultracode-edit`, `$ultracode-flow`, and `$ultracode-status`.

## Side-effect checklist

These observations apply to the evaluated Help invocation, before this separately authorized
evidence artifact was persisted.

| Side effect | Observed | Evidence |
| --- | --- | --- |
| Initialized project control | No | Help stayed explanatory and did not invoke Init. |
| Delegated work | No | No agent or ticket was created for the Help response. |
| Ran project checks, tests, or builds | No | Only read-only source inspection and Git status commands were used. |
| Changed global model or effort settings | No | Model guidance remained descriptive; no setting action was invoked. |
| Wrote files | No | The evaluated Help invocation used no file-write operation. |

Persisting this Markdown file is a later, explicitly authorized evaluation-evidence write and is
not a side effect of the raw Help invocation.

## Source file references

- `plugins/ultracode/skills/ultracode-help/SKILL.md`:
  read-only boundary, compact-mode selection, mandatory overview hierarchy, seven command fields,
  model/runtime honesty, and completion checklist.
- `plugins/ultracode/skills/ultracode/references/command-guide.md`:
  canonical ordering, per-command semantics, unconfigured-project behavior, model routing,
  ticket/agent distinction, and authority boundaries.
- `plugins/ultracode/skills/ultracode/references/eval-prompts.md`:
  exact UC-37 three-context evaluation request and evaluator inspection requirements.
- `plugins/ultracode/skills/ultracode/references/behavioral-contract.md`:
  UC-37 acceptance contract for compact Help and absence of side effects.
