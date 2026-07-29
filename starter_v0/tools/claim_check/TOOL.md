# claim_check

Local tool for triaging a factual claim before research or fact-checking.

Use this tool when the user provides a claim and asks whether it is believable, risky, worth verifying, or what evidence is needed. The tool does not verify the claim by itself; it classifies the claim, identifies missing context, recommends evidence types, and suggests next research tools such as `lookup`, `papers`, or `fetch`.

Do not use this tool when the user asks to search the web directly; use `lookup`. Do not use it to read a URL; use `fetch`. If the user asks to check "this claim" but does not provide the claim, use `clarify`.

Arguments:

- `claim`: factual statement to triage.
- `domain`: one of `auto`, `current_events`, `scientific`, `product`, or `general`. Default is `auto`.
- `urgency`: one of `low`, `normal`, or `high`. Default is `normal`.

This tool has no side effects and does not require confirmation.
