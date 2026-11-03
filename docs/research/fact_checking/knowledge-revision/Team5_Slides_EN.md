# When Should a Fact-Checking Agent Change Its Mind?
NLP Team 5 · Midterm discussion draft

## T0 | Verify a dated claim and justify whether to revise
**Task.** Given a claim, its target date and an initial packet, choose when to search, open a source or stop. Return SUPPORTED, REFUTED or NOT ENOUGH INFORMATION, the decisive facts and cited passages.
**Paired test.** Start from 50 real-post cases. From the same initial judgment, compare a fixed workflow, standard ReAct and evidence-ledger ReAct. Hold the model, index and budget constant.
**Primary score.** Grounded Success Rate = episodes with the correct verdict and facts, sufficient valid citations and the right time scope / all assigned episodes.
**Read the trade-off.** Report correction among initially wrong decisions, preservation and harmful reversal among initially correct ones, plus actual searches, tokens and time.
**Visual.** Claim + initial packet → Shared initial verdict → Search / open / finish → Cited final verdict

## L01 | Where did the evidence come from?
**Finding.** RAG conditions generation on retrieved passages. ReAct lets a model request a new observation after it sees the previous one. Astute RAG tracks information from internal and external sources during consolidation.
**Our design.** Record the response without documents, the supplied packet and the sources actually opened. This lets us ask which new observation preceded a change in judgment.
**Visual.** No-document probe → Initial packet E₀ → Evidence opened during verification
**Sources.** D17 D18 D04 D16

## L02 | A training cutoff cannot tell us whether a model knows one fact
**Finding.** Dated Data probes which version of a changing resource a model's behavior resembles. FreshLLMs distinguishes questions about stable facts from questions whose answers change over time.
**Our design.** Ask three neutral paraphrases in fresh contexts. Group responses as stable-correct, stable-wrong or unstable, and hide the probe answers from the agent.
**Visual.** Same fact, three paraphrases → Compare substantive answers → Assign a behavioral stratum
**Sources.** D14 D29

## L03 | Agreement can hide the very error we want to detect
**Finding.** In VitaminC, a small edit to evidence can change its relation to a claim. FaithEval tests whether a model follows a supplied context even when it describes a counterfactual world.
**Our design.** Hold the real-world reference fixed. If a false claim and a misleading packet both say “founded in 2022,” a faithful summary can still give the wrong verdict.
**Visual.** Claim: founded in 2022 + Packet: founded in 2022 → Check the dated institutional record
**Sources.** D21 D22 D02 D10

## L04 | Resisting a bad source can make a model resist a good one
**Finding.** In ClashEval Table 3, calibration raises GPT-4o accuracy from .615 to .754 while prior bias rises from .021 to .085. Average accuracy conceals a cost for cases in which the initial answer needs correction.
**Our design.** Give correction and preservation separate denominators. A policy that retains every starting answer would score well on only one side.
**Visual.** Initially wrong → Can it correct? | Initially correct → Can it preserve?
**Sources.** D01 D03

## L05 | Count where the answer lands after it changes
**Finding.** Real Documents gave initially wrong models genuine passages containing the answer. For Llama2-7B, Table 3 averages 1.6% retaining the old error, 77.0% updating correctly and 21.3% switching to another error.
**Our design.** Log whether the agent opened decisive evidence, then score what it did with that evidence. This separates a failed search from a failed interpretation.
**Visual.** Retained error: 1.6% | Correct update: 77.0% | Different error: 21.3%
**Sources.** D03 D01

## L06 | Keep a source attached to the fact it supports
**Finding.** Astute RAG elicits internal information, consolidates it with retrieved evidence and produces an answer. Its consolidation step retains where competing information came from.
**Our design.** Keep one entry per claim requirement with the source, passage and target period. A gap in that entry can determine which document the agent opens next.
**Visual.** Requirement: founding date → Annual report: restructuring date → Open the founding record
**Sources.** D04 D24 D25

## L07 | A shorter verification question can change the claim
**Finding.** ClaimDecomp exposes implicit requirements through subquestions. Decomposition Dilemmas shows how a decomposition can lose meaning, including the conditions under which a comparison holds.
**Our design.** Keep the original claim beside each subquestion. Before accepting its answer, check that the entity, period and comparison group still match.
**Visual.** “Highest in the region in 2022” → Check the region + year + comparison group
**Sources.** D30 D31 D05

## L08 | Give the model an observation that could change its answer
**Finding.** CRITIC uses tool feedback to critique and revise an output. Work on intrinsic self-correction reports that reconsideration alone can degrade reasoning performance in the settings tested.
**Our design.** Record the document or passage acquired between two judgments. Gold correctness flags stay outside the loop so the agent must decide when to check.
**Visual.** Draft answer → External observation → Evidence-based revision
**Sources.** D06 D07 D18

## L09 | Is another search worth its cost?
**Finding.** FIRE alternates verification with query generation. Its cost comparisons depend on the baseline workflow and whether the unit counted is a model call or a search.
**Our design.** Give each policy the same caps and record actual use. Compare grounded decisions alongside search calls, opened documents, tokens and elapsed time.
**Visual.** Same budget ceiling → Different actions taken → Grounded success and cost
**Sources.** D08 D18 D13

## L10 | Which part of the claim still lacks evidence?
**Finding.** The FEVER example needs facts from two pages to complete a justification. AVeriTeC uses real claims, verification questions and dated evidence. Both motivate asking whether the cited set covers the decisive conditions.
**Our design.** Mark each required fact and its supporting span. A passage that identifies the right institution can still leave its founding year unresolved.
**Visual.** Institution identified ✓ | Founding date unresolved ? → Search for the missing fact
**Sources.** D19 D20 D23 D09

## L11 | Three outlets may repeat one original error
**Finding.** In Evidence Laundering's controlled publication task, the false-publication rate was .71 for a single false page and .83 for a repeating bundle in its A–C comparison.
**Our design.** Trace who first asserted the fact. On the false-agreement diagnostic, check whether the agent finds an independently informative record before it stops.
**Visual.** Three articles → One shared press release → One originating assertion
**Sources.** D10 D28

## L12 | A contradictory hit is a reason to inspect the source
**Finding.** FVA-RAG retrieves possible counterevidence against a draft answer. Fact2Fiction studies poisoning in automated fact-checking, where persuasive retrieved material can itself carry the error.
**Our design.** Apply the same source, scope and date checks to a contradiction as to a supporting passage. Reverse the verdict only when the new evidence warrants it.
**Visual.** Counterevidence found → Check origin and target date → Retain or revise
**Sources.** D11 D28 D01

## L13 | What would a small evidence ledger actually add?
**Finding.** BeliefRAG already tracks gaps, conflict, sufficiency and cost to control retrieval. Its ablation points to corrective re-retrieval as an important part of the gains it reports.
**Our design.** Compare ordinary ReAct and ledger ReAct from the same starting answer, with the same tools. Test whether naming a missing fact improves the next action and the final cited verdict.
**Visual.** Same initial answer → Rolling history | Explicit ledger → Paired verdicts
**Sources.** D12 D04 D05

## L14 | Stop when the decisive question is resolved
**Finding.** SEAC treats stopping or asking for clarification as a decision with costs. Search Wisely examines over-search and under-search. Both motivate measuring the value of the next action.
**Our design.** A dated record can close a gap and justify stopping. When the search budget expires with a gap still open, distinguish a justified NEI verdict, abstention and execution failure.
**Visual.** Decisive gap open → Targeted search | Requirement resolved → Finish with citations
**Sources.** D13 D15 D08 D23

## L15 | Can a policy correct mistakes without damaging justified answers?
**Finding.** Real Documents separates correct and incorrect updates. ALCE evaluates answer quality and citation quality separately. FEVER and Ev2R show why evidence must be evaluated against what a claim requires.
**Our design.** Compare three policies on matched cases. Report grounded success, correction, preservation, harmful reversal and cost. For a failure, ask whether the source was missed, misread or cited beyond its scope.
**Visual.** Judgment transition × Evidence quality × Verification cost
**Sources.** D03 D26 D19 D27 D20 D01
