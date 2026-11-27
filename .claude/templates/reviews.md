<!--
Review log template. Copy next to the plan file: <id>-plan.md -> <id>-reviews.md (same folder). One row per agent per
round, written by the main session after it has verified the findings (/review step 4, /multi-review step 5,
/close-out step 2b); a regression found later is added by /triage step 5. `tools/closeout_check.py --plan` checks the
rows. The column names and step names are fixed (the tool reads them); the Note column may be in any language.

Date               YYYY-MM-DD
Step               review | multi-review | close-out | after-close-out
Round              1, 2 ... (review rounds per plan: at most 2); "-" for after-close-out
Agent              scope-counter | devils-advocate | closeout-auditor | developer (after-close-out)
Findings           devils-advocate / closeout-auditor: rows of the agent's index table;
                   scope-counter: differences between your own count and the agent's, plus findings in its answers
                   to the extra questions (removed calls, every caller, restored state, tenant condition);
                   after-close-out: problems the job caused that were found after the commit
Accepted           of those, the ones you opened in the source and found real (after-close-out: confirmed) — whatever
                   became of them: a plan step, a test step or a question to the developer. Write the split in
                   Note ("plan 3 / test 2 / question 2"), so a high count is not read as "the plan grew by that much"
Accepted critical  accepted with severity "critical" (wrong amount / data loss); scope-counter: 0
Not opened         findings you could not open yourself ("reported by the review, not verified by me")
Note               one line: what changed in the plan, why findings were rejected; "\|" for a literal bar

The counts are the developer's and the session's judgement, not a score of the agent: a low acceptance rate may mean
weak findings or a session that pushed back too easily. Read them in the monthly review, not as a gate.
Delete this comment in the copy.
-->

| Date | Step | Round | Agent | Findings | Accepted | Accepted critical | Not opened | Note |
|---|---|---|---|---|---|---|---|---|
