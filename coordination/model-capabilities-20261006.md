# Model evidence for task allocation

Checked 2026-10-06. This supports TEAM-STRUCTURE-001; it does not configure models.

## Identity and recent changes

The operator identifies Codex as Astra 6 and Claude as Fable 5.1. This execution
does not independently attest those runtime identities. Claude keeps its runtime
identifier in its private operator channel. Hermes publicly reports configuration
and scheduled-runtime evidence for `claude-sonnet-5-5`, with no configured fallback
([receipt](https://github.com/scottonchain/microcredit-agent-testbed/issues/15#issuecomment-6019837874)).
That receipt does not prove every past or future run uses the same model.

Anthropic released Sonnet 5.5 on September 28. Its release describes a faster,
lower-cost model suited to bounded everyday work; it does not support describing
Hermes as simply an older generation. Fable 5.1 was released September 1.

## What the published numbers establish

All differences below are percentage points, not intelligence multipliers.
Scores depend on effort, tools, task versions and evaluation harnesses.

| Evaluation | Astra 6 | Fable 5.1 | Sonnet 5.5 | Interpretation |
| --- | ---: | ---: | ---: | --- |
| FrontierMath Tier 4 v2 | 97.6 | 87.8 | Not established here | Astra leads Fable by 9.8 points in OpenAI's table. This is not a Hermes comparison. |
| Terminal-Bench Science 0.1 | 64.6 | 52.6 | Not established here | Astra leads Fable by 12.0 points in OpenAI's table. Relevant to scientific checking, not a project success rate. |
| FrontierCode 1.1 Main | 53.3 | 50.9 | 52.1 at Xhigh; 46.2 at Max | Astra versus Sonnet's best published score differs by only 1.2 points across reports. Too weak to establish a practical advantage here. |
| Terminal-Bench 4.0 | 57.9 | 55.8 | 70.6 | Sonnet's published score is 12.7 points higher than Astra's across reports. This contradicts a universal Astra-over-Hermes ordering. |
| Humanity's Last Exam, tools | 57.2 | 65.0 | 64.5 | Another counterexample to a universal ordering. Vendor setups and tool access matter. |

Sources: [OpenAI Astra evaluation table](https://openai.com/index/gpt-6-astra/),
[Anthropic Sonnet 5.5 release and evaluation table](https://www.anthropic.com/claude-sonnet-5-5),
[Fable 5.1 release](https://www.anthropic.com/claude-fable-and-mythos-5-1).
OpenAI reports maxima across effort settings. Anthropic notes that Sonnet's Max
setting can lose FrontierCode points through extra scope and timeouts. These are
vendor-reported measurements, not a controlled trial of these three workers.
The Sonnet system-card link failed to load during this check; no missing
math/science score is inferred. Different vendor reports also give slightly
different Fable FrontierCode values; this table consistently uses OpenAI's Fable
column and does not combine its variants into a precision claim.

## Allocation consequence

The evidence supports using Astra for difficult synthesis, experiment design and
math/science challenge when that runtime is available. It does not quantify an
overall advantage over the actual Hermes model. Claude's demonstrated authoring,
long-running tool environment and safe publication path support its technical
ownership. Hermes's exclusive Moltbook, A2A, wallet and RPC access makes bounded
relationship and receipt work a better use of its time than duplicated research
or simulation runs.

README reassignment follows the operator's instruction, observed writing problem
and workload, not a claim that Sonnet cannot write. Preserve separate author and
checker for consequential technical conclusions. Record rework and missed
obligations from normal work for a seven-day allocation review. No synthetic IQ,
task-speed multiplier or confidence percentage is justified by these sources.

Capabilities must be checked per execution: git read is not git push, prompts do
not set model/effort, and model quality cannot create credentials or permission.

