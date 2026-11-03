# Task and Evaluation Protocol — Draft

**NLP Team 5 · 2 November 2026**
**Working title: Evidence-Grounded Selective Revision for Fact-Checking Agents**

## 1. Research question

**Under a fixed verification budget, can an agent that explicitly tracks unresolved claim requirements, evidence provenance, and temporal scope correct mistaken judgments while preserving correct judgments better than a fixed verification workflow and a standard ReAct agent?**

The main object of study is a *judgment transition supported by evidence*. The study connects knowledge-conflict analysis, tool-assisted correction, and adaptive fact verification. We use “revision” for an observable change in the output; internal belief change is a separate theoretical interpretation.

## 2. Task definition

**Input.** A factual claim, a target date, an initial evidence packet E₀, and the packet's visible source metadata. Each claim has a small set of critical conditions, such as an entity, date, quantity, jurisdiction, or product version.

**Available actions.** Search the shared evidence collection, open a source, and finish with a judgment. Queries and subsequent actions are chosen by the agent in adaptive conditions. Search results expose the same metadata and content across methods.

**Output.** A structured record containing:

- `status`: `decision` or `abstain`;
- `verdict`, when a decision is made: `SUPPORTED`, `REFUTED`, or `NOT_ENOUGH_INFORMATION`;
- the critical factual values and temporal scope used in the decision;
- cited document IDs and supporting or refuting spans;
- a concise evidence-based justification, including why the initial judgment was retained or revised;
- an observable action log, token usage, tool counts, and elapsed time.

`NOT_ENOUGH_INFORMATION` (NEI) is a benchmark judgment established by the annotation protocol. `abstain` is the system declining to decide. A timeout or malformed response is an execution failure. These outcomes have separate fields and denominators.

**Success.** The final judgment and its critical conditions match the adjudicated reference, and the cited evidence is sufficient and valid for the target date. A correct label with an unsupported explanation does not meet the primary success criterion.

## 3. Three information pathways

| Pathway | Observable operationalization | Role in this study |
|---|---|---|
| Parametric response | Fresh-context, evidence-free answers to neutral factual questions | A behavioral prior, measured before the task |
| Given evidence | Initial packet E₀ | The starting external context |
| Acquired evidence | Documents opened through task-time actions | Additional observations available for correction or confirmation |

Given and acquired evidence are both external context. Their distinction is how they enter the episode. Publication time, source origin, and factual validity are annotated separately. The reference judgment is adjudicated independently of the tested model and its retrieval choices.

## 4. Data construction

### Main track: 50 authentic claim cases

Retain the existing FC001–FC050 identifiers and links. For each case, specify an atomic, checkable claim; its target date; the reference verdict; critical factual conditions; and at least one reference evidence set where the claim is decidable. Preserve the relationship to the original post even when the wording is normalized.

Two team members independently label each case and identify decisive evidence. A third member adjudicates disagreements. Record disagreement rates before adjudication. Group cases that concern the same event so that pilot selection and uncertainty estimates respect shared evidence.

The current casebook is an annotation starting point. Its current label distribution should inform sampling; label balance and evidence quality must be checked before interpreting Macro-F1.

### Diagnostic track: matched evidence conditions

Start with 10–12 base facts from the main track. For each, prepare a valid initial packet and a misleading initial packet. A subset explicitly combines a false claim with mutually agreeing false evidence. Keep packet length, source count, and visible formatting as comparable as practicable, and record remaining differences.

The claim/evidence grid is distinct from the model's prior-response stratum:

| Claim truth | Evidence validity | Diagnostic question |
|---|---|---|
| True | Valid | Can the agent reach and preserve a grounded supported judgment? |
| True | Misleading | Can it resist misleading evidence and confirm the true claim? |
| False | Misleading, supporting the false claim | Can it challenge false agreement and find decisive refutation? |
| False | Valid, refuting the claim | Can it interpret the refutation and reject the claim? |

“Evidence validity” concerns the relevant factual assertion and its date/scope. Real documents can contain false assertions, and authentic historical reports can be inapplicable to a later target date. Document authenticity, factual validity, and relevance remain distinct annotations.

Keep results for authentic cases and constructed packets separate. Pairing helps isolate sensitivity to the supplied context; uncontrolled wording and source cues can still affect the comparison.

### Prior-response strata

Ask three neutral paraphrases of the underlying factual question in fresh contexts, without E₀. Define `stable-correct` as three correct responses, `stable-wrong` as the same substantive wrong answer in all three, and `unstable/abstaining` otherwise. Score against the independent reference. Do not feed the probe answers, stratum, or gold correctness flag to the experimental agents.

These strata measure observed response stability. A published training cutoff helps select temporal cases, but it does not establish whether a particular fact was in training. Three probes do not prove training membership or a near-certain internal probability. See [Dated Data](https://arxiv.org/html/2403.12958v2).

## 5. Comparison conditions

All methods share the same backbone, initial judgment a₀, evidence interface, tool implementation, index snapshot, generation settings, and hard budget. Generate a₀ once from the claim and E₀, then fork isolated episodes. This answers a conditional question: how well do different verification policies improve the same starting judgment?

| Condition | Policy | Purpose |
|---|---|---|
| B1 — Fixed Verification | A preregistered sequence of claim search, counterevidence search, and primary-source checking, followed by synthesis | A strong non-adaptive workflow baseline |
| B2 — Standard ReAct | General evidence-based search/open/finish instructions and a rolling observation history | Adaptive action selection without an explicit evidence ledger |
| P — Evidence-Ledger ReAct | The same actions, plus an updated ledger of requirements, evidence relations, origins, and unresolved questions | Test whether explicit state organization improves selective revision |

The proposed ledger has four fields: **claim requirement; supporting/refuting evidence with temporal scope; source-origin relation; unresolved verification question and next-action purpose**. It stores concise observable summaries, not private chain-of-thought.

Choose the next action by the unresolved requirement with the highest expected decision relevance. When the evidence jointly supports a decision, finish; when a critical gap remains but the budget ends, distinguish a justified NEI decision from abstention.

**Draft cap for a pilot:** at most four searches, six document opens, and eight agent-model requests per episode. Fix per-request and total-token limits after measuring the pilot. Record actual use as well as the cap. Charge the shared initial-response cost consistently to every condition. Equal caps do not imply equal realized costs.

Use a frozen, searchable evidence snapshot for the main reproducible comparison. The agent still chooses queries and document opens. A later live-web extension tests freshness separately, with retrieved pages and timestamps preserved. This retains adaptive retrieval while controlling which information was available.

If resources permit, add one focused ablation: remove provenance fields from P while retaining claim requirements and unresolved-question tracking. This distinguishes the contribution of source relations from the benefit of structured notes in general.

## 6. Scoring variables

For case i, let `D₀ᵢ` and `Dᶠᵢ` indicate a valid initial/final decision. Let `C₀ᵢ` and `Cᶠᵢ` indicate that the verdict **and critical factual conditions** are correct. Define C = 0 for abstention or execution failure, but use D to keep those states out of the “valid wrong decision” category.

Let `Sᶠᵢ` indicate a sufficient cited evidence set, `Vᶠᵢ` valid evidence for the relevant assertions, and `Tᶠᵢ` a correct temporal and contextual match. Human raters use a case-specific evidence checklist. Equivalent decisive sources are allowed; a matching URL is not required.

For reference-NEI cases, sufficiency means documenting the specified unresolved component and the bounded checks required by the annotation protocol. A bare statement that nothing was found is insufficient. The reference describes what is unresolved within the evaluation scope rather than asserting an unknowable universal absence of evidence.

## 7. Primary and supporting metrics

| Metric | Definition | Why it fits this task |
|---|---|---|
| **Grounded Success Rate (GSR)** | Σ(Cᶠᵢ × Sᶠᵢ × Vᶠᵢ × Tᶠᵢ) / N assigned episodes | Requires a correct, evidenced, time-appropriate judgment; distinguishes lucky labels from successful verification |
| **Correction Rate (CR)** | Correct final decisions among initially valid wrong decisions / number of initially valid wrong decisions | Measures useful revision after a mistaken starting point |
| **Preservation Rate (PR)** | Correct final decisions among initially correct decisions / number of initially correct decisions | Measures whether verification preserves correct judgments |
| **Harmful Revision Rate (HRR)** | Valid wrong final decisions among initially correct decisions / number of initially correct decisions | Isolates an actual wrong reversal; abstention and runtime failure are reported separately |
| **Decision coverage and Macro-F1** | Coverage = valid final decisions / assigned episodes; Macro-F1 on those decisions, using the fixed three-label set and gold labels | Describes label quality and class imbalance together with completion; high F1 at low coverage is visible |
| **Verification cost** | Searches, opens, model requests, input/output tokens, wall-clock time, and available billed cost per episode | Tests the value of selective verification and exposes operational failures |

Use all assigned episodes in the GSR denominator, including runtime failures. If a conditional denominator is zero, report `N/A (n = 0)`. Report a numerator and denominator alongside every conditional percentage. Set class F1 to zero for an undefined precision/recall case and declare this convention in advance; report per-class support and confusion counts.

CR and PR are answer-level transition measures; GSR supplies the evidence requirement. As a secondary diagnostic, report *grounded correction*: initially wrong episodes that finish with Cᶠ × Sᶠ × Vᶠ × Tᶠ = 1, divided by initially valid wrong episodes. This prevents an unsupported corrected guess from appearing equivalent to verified correction.

HRR is not generally 1 − PR because initially correct episodes may end in abstention or execution failure. Publish the complete transition table: correct, valid-wrong, abstain, and execution-failure states.

### Academic rationale

- [ClashEval](https://proceedings.neurips.cc/paper_files/paper/2024/hash/3aa291abc426d7a29fb08418c1244177-Abstract.html) motivates measuring both resistance to misleading context and correction of prior errors. Our CR/PR definitions are protocol-specific, not renamed copies of its bias metrics.
- [Real Documents](https://arxiv.org/html/2404.16032v2) separates correct updates from incorrect updates, motivating transition-based evaluation rather than answer-change rates.
- [CRITIC](https://arxiv.org/html/2305.11738) and [FIRE](https://aclanthology.org/2025.findings-naacl.158/) motivate external feedback and cost-aware sequential verification.
- [Evidence Laundering](https://aclanthology.org/2026.emnlp-main.509/) motivates source-relation checks: agreement between documents can reinforce an error.
- [Astute RAG](https://aclanthology.org/2025.acl-long.1476/), [Micro-Act](https://arxiv.org/html/2506.05278v2), and [BeliefRAG](https://arxiv.org/html/2609.39139) are close methodological precedents. They motivate a narrow empirical contribution and a comparison against structured conflict handling, rather than a claim that stateful verification is new.

GSR is our proposed operational composite. Its evidence checklist must be calibrated on pilot cases; it is not presented as an established universal metric.

## 8. Diagnostic decomposition

1. **Evidence acquisition:** among cases with a decisive set available in the shared environment, did the agent actually open a sufficient gold-equivalent set?
2. **Evidence interpretation:** among cases where such a set was opened, how often did it reach a correct final decision?
3. **Evidence use:** do the cited spans support each material claim in the final explanation?
4. **Source dependence:** was the apparent corroboration derived from the same original assertion, or from independently relevant observations?
5. **Temporal mismatch:** did the failure come from the target date, the document date, or a changed fact?

These diagnostics explain errors in GSR and transitions. Their denominators are conditional and must be shown; they are not interchangeable overall performance rankings.

**Why judge the evidence separately?** [FEVER](https://aclanthology.org/N18-1074/) distinguishes label accuracy from retrieving a sufficient evidence set. [AVeriTeC](https://proceedings.neurips.cc/paper_files/paper/2023/hash/cd86a30526cd1aff61d6f89f107634e4-Abstract-Datasets_and_Benchmarks.html) ties a real claim to verification questions and time-appropriate web evidence. [ALCE](https://aclanthology.org/2023.emnlp-main.398/) evaluates attribution separately from answer correctness; [Ev2R](https://arxiv.org/abs/2411.05375) compares both reference facts and support for the gold verdict. These motivate separate annotation fields and a joint success rule. GSR is our operational definition, not an implementation of any one benchmark score. Faithfulness to a supplied counterfactual document, as tested by [FaithEval](https://arxiv.org/abs/2410.03727), may be a factual error under our independent reference judgment.

## 9. Analysis plan and scale

Use 50 claims × 3 methods = **150 main-track episodes**. A 10–12-case, two-packet diagnostic adds **60–72 episodes** if both packets are run for all three methods. Three prior probes per base claim add **150 model requests**. An episode can contain multiple requests. For example, an eight-request ceiling yields up to 1,200 policy requests for the main track before probes, pilot work, and diagnostics; reuse of a shared initial response must be accounted for explicitly.

Start with a small disjoint pilot to finalize prompts, annotation rules, logging, and limits. Freeze these decisions before the main evaluation. If pilot cases come from FC001–FC050, remove them from the held-out comparison and replace them or label the final evaluation exploratory.

Compare methods within the same case and starting response. Report paired differences and uncertainty intervals resampled at the event group; keep packet variants and repeated runs in the same cluster. With 50 cases, emphasize effect sizes, counts, and error examples. Treat the small diagnostic subset as exploratory and avoid rankings based on tiny strata.

Present one joint view of GSR, CR, PR/HRR, and cost. A method that corrects more errors while damaging more correct answers exhibits a trade-off. A method that succeeds more often only by using more resources needs a cost-qualified conclusion.

## 10. Contribution and scope

**Proposed contribution:** a reproducible, provenance- and time-aware evaluation of selective judgment revision on a small authentic claim collection, with matched misleading-evidence diagnostics and a transparent evidence-ledger policy.

The literature already studies knowledge conflicts, tool-assisted correction, provenance-aware reasoning, and adaptive retrieval. The potential contribution is the particular task operationalization, paired evidence conditions, transition analysis, and measured trade-offs. Whether the ledger helps is the experimental question.

This file is a design draft. Model selection, final budgets, gold adjudication, and numerical findings belong to subsequent stages. The midterm presentation can defend metric definitions and academic rationale before reporting results at the final stage.
