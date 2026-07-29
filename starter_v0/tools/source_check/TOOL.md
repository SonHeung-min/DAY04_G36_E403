# source_check

Local tool for checking whether one or more URLs look suitable for research, citation, or external publishing.

Use this tool when the user asks to review source quality, citation suitability, domain credibility, or publication risk for explicit URLs. Do not use it to read the page content; use `fetch` when the user asks to summarize or extract the article text. Do not use it when no URL is provided; ask `clarify` for the URL first.

Arguments:

- `urls`: list of explicit URLs to assess.
- `purpose`: one of `research`, `citation`, or `publishing`. Default is `research`.
- `max_items`: maximum number of URLs to check. Default is `5`.

This tool has no side effects and does not require confirmation.
