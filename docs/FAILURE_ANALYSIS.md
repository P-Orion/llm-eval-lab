# Failure analysis

Recorded run `045f66a720b14e312674`: `qwen3.5:9b`, 100 questions, JSON schema, thinking disabled, and a 512-token generation limit. All scheduled requests completed. Completion alone does not establish a usable answer.

| Condition | Responses at token limit | Those without a valid answer payload | Answer key appears before work key |
| --- | ---: | ---: | ---: |
| direct | 1 | 1 | 100/100 |
| reasoned | 32 | 32 | 100/100 |

These counts are computed from saved responses and runtime token counts. Reaching the configured token limit is an observed association with extraction failure, not a separately recorded termination reason. Other invalid JSON or non-numeric answers also fail extraction.

The model emits the answer field before its work field in this run. Some later work conflicts with the already emitted answer. The scorer uses the declared answer field: it does not search the work for a more favorable number. Inspect question #80, reasoned, in the raw responses for an example of this interface disagreement.

The paired interval includes zero, so this run does not establish a prompt benefit. The 0.6B model, delimiter trials, and legacy pilot remain available rather than being replaced by the larger-model run.

## A next experiment, not a claimed improvement

Use a separate validation subset from the GSM8K training partition to investigate reasoning-before-answer serialization, a sufficient generation budget, and explicit termination diagnostics. Freeze the chosen protocol before a newly declared evaluation. Keep the present test runs labeled exploratory and unchanged. Do not silently repair malformed responses or move the scorer into reasoning text to improve the reported accuracy.

This toolkit's useful result is a traceable diagnosis: transport, formatting, verification, and scheduled-task success can fail at different layers. The measured outcome does not establish broad model capability.
