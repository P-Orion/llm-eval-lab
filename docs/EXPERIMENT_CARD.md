# Experiment card
Dataset: original [GSM8K](https://github.com/openai/grade-school-math), MIT, upstream revision in data/manifest.json. Public test set has potential training contamination.
Latest run: 045f66a720b14e312674; dataset SHA-256 3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14; model qwen3.5:9b, digest 6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7.
Fixed question IDs, prompt text, schema, temperature 0.6, context 4096, generation limit 512, seed 42, thinking false, runtime version and source hash are in the manifest. Raw responses are retained.
Tracks: delimiter pilot, frozen 100-question delimiter experiment, then an exploratory JSON-format experiment on the same frozen questions. Both successes and failures remain available.
The legacy 20-question pilot did not record source hash or Ollama version. The full 100-question experiments record both and retain matching source snapshots; those fields have not been retroactively invented for the pilot.
Metric: completed AND verifiable final answer AND numerically correct, divided by all scheduled tasks. Completed-only accuracy is separately labeled. Failure/truncation can appear as an extraction failure; the current schema does not separately certify all runtime termination reasons.
Paired interval bootstraps questions, grouping repeated seeds. It does not establish causal prompt benefit outside this protocol.
No answer-based retry, no scoring with a second LLM, no arbitrary expression execution. Late task workers are fenced by attempt generation.
Limits: one seed, public contamination, model-specific capacity, exploratory tracks added after format failure, local concurrent-load latency. Separate historical source snapshots preserve the code used for each recorded run.
