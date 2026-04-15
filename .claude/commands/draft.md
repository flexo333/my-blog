# /draft — Move an idea into posts/ as a draft

**Arguments:** $ARGUMENTS — the idea title/slug (e.g. `/draft my-great-idea`)

If no argument is provided, list files in `ideas/` and ask the user which one to draft.

---

Run:
```bash
make draft IDEA=$ARGUMENTS
```

After creating the draft:
1. Commit the stub immediately so it's recoverable:
   ```bash
   git add posts/<slug>.md
   git commit -m "draft: add stub for <slug>"
   ```
2. Show them the file path: `posts/<slug>.md`
3. Show the current frontmatter
4. Ask: "Would you like me to help you flesh this out? I can expand the idea into a full draft."

If they say yes, read the file content (ideas stub or any notes), then write a full draft
following the blog's voice and style:
- Direct, experience-based, metaphor-driven
- Long connected paragraphs that build on each other — not labelled sections or short punchy fragments
- No bold headers or horizontal dividers — the piece should flow as essay prose
- Opinion-forward — no hedging
- Opening earns the reader in the first 2 sentences
- State conclusion up front, then explain why
- First person style. This blog aims to cover the users lived experience and knowledge, not just abstract opinion.

After writing, commit the full draft and ask if they'd like any changes:
```bash
git add posts/<slug>.md
git commit -m "draft: write <title>"
```
