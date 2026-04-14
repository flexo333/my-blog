# /edit — Edit a post: feedback, improvements, sanitising

**Arguments:** $ARGUMENTS — post slug (e.g. `/edit my-post`). If omitted, list drafts and ask.

---

## Step 1 — Find the post

If `$ARGUMENTS` is provided, read `posts/<slug>.md`.
If not, list files in `posts/` and ask which to edit.

Read the full post content.

---

## Step 2 — Assess and give honest feedback

Before touching anything, give the author your honest read. Cover:

**Content**
- What's the core argument? Is it clear?
- Does the opening earn the reader in the first 2 sentences, or does it throat-clear?
- Is there anything that drags, repeats, or adds nothing?
- Does it end strongly, or trail off?

**Voice**
- Is there hedging or corporate filler that should go? ("it's important to note that...", "of course, YMMV")
- Are the verbs weak? ("This can be used to enable" → "This enables")
- Is the metaphor (if any) doing real work, or introduced and dropped?

**Safety — employer/people references**
Check for anything that could be sensitive:
- Employer names, client names, product names, team names
- Named individuals (colleagues, managers, clients)
- Specific dollar figures, headcounts, timelines that could be identifying
- Internal project codenames or non-public strategy

Flag anything that fails the newspaper front page test:
*"If this appeared in a major publication tomorrow, attributed to the author by name,
would it embarrass their employer, expose confidential information, or harm a named individual?"*

---

## Step 3 — Offer a plan before touching anything

Summarise what you'd change and why, in 3-5 bullet points. Ask:
"Want me to make these changes? (yes / just the safety fixes / just the feedback, I'll edit myself)"

---

## Step 4 — Edit (if approved)

Apply only what was agreed. In order:

1. **Sanitise first** — replace identifying specifics with generalisations:
   - Employer/client/product names → "my team", "the company", "a large fintech"
   - Named individuals → "a senior engineer", "the CTO", or remove the anecdote
   - Specific figures → order-of-magnitude ("a nine-figure programme", "a team of ~80")
   - Internal codenames → "the initiative", "the platform rewrite"

2. **Cut padding** — delete sentences that restate or add nothing. Aim to cut ~20% of words.

3. **Sharpen verbs** — replace weak constructions:
   - "This can be used to enable" → "This enables"
   - "We were able to deliver" → "We delivered"
   - "It is important to note that" → delete

4. **Opening** — if it throat-clears, rewrite it. State the conclusion first, then explain why.

5. **Ending** — if it trails off, sharpen the last sentence. It should feel final.

6. **Title** — if vague, suggest a sharper one. Specific > vague:
   - Good: "A Plan Is a Guess", "Defensiveness Is Death"
   - Bad: "Thoughts on Planning", "Some Notes on Leadership"

---

## Step 5 — Show the diff

Show what changed. Don't reprint the whole post — just the key edits and why.

Ask: "Happy with this? Want anything changed back or pushed further?"

---

## What NOT to do

- Don't change the core argument — polish the expression, not the idea
- Don't make it more formal or academic
- Don't add corporate hedges mid-post
- Don't add subheadings unless the piece is genuinely long (1500+ words)
- Don't add a summary paragraph ("In this post I will...")
- Don't remove emotional stakes — the conflict, difficulty, and stakes are what make it worth reading
