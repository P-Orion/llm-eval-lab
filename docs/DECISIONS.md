# Decisions and interview walkthrough
1. Why scheduled-task success? Excluding timeouts or format failures can make a failing pipeline look accurate.
2. Why separate extraction and verification? A correct number in unstructured reasoning does not establish a reliable final-answer interface.
3. Why content-addressed manifests? Changed data, prompts, settings or model versions require a new experiment identity.
4. Why leases and generation fencing? A process may die after inference but before committing a response. Recovery can repeat the call, while stale completions cannot overwrite newer work.
5. Why preserve the delimiter failure? The result revealed interface reliability problems; deleting it would hide the actual engineering lesson.
6. Why no prompt conclusion from a tiny sample? Paired confidence intervals and benchmark contamination constrain what the result supports.
