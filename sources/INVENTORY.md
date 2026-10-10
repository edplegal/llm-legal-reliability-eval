# Sources inventory

This repository ingests no external datasets. Its inputs are author-written
and live at the repository root so that the pipeline can read them from
its base directory.

| path | type | generated | producer | authority | supersedes | description |
|------|------|-----------|----------|-----------|------------|-------------|
| ../prompts.json | source | 2026-05-21 | author, with AI drafting assistance (see the report's authorship note) | authoritative | — | the sixty questions with category, domain, risk level, and pair metadata; `prompts_hash` `1e34d3f487ef` |
| ../rubric.md | source | 2026-04-03 | author | authoritative | — | the six-dimension scoring rubric, human-readable |
| ../judge_prompt_template.txt | config | 2026-05-21 | author | authoritative | — | the judge prompt with the rubric inlined and the JSON output contract |
| ../config.json | config | 2026-07-01 | author | authoritative | — | the six-model grid and output caps |
| ../config/bridge_config.json | config | 2026-07-03 | author | authoritative | — | the two frozen judges at temperature 0.0 |
