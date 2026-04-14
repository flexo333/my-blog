# /draft — Move an idea into posts/ as a draft

**Arguments:** $ARGUMENTS — the idea title/slug (e.g. `/draft my-great-idea`)

If no argument is provided, list files in `ideas/` and ask the user which one to draft.

---

Run:
```bash
make draft IDEA=$ARGUMENTS
```

After creating the draft:
1. Show them the file path: `posts/<slug>.md`
2. Show the current frontmatter
3. Ask: "Would you like me to help you flesh this out? I can expand the idea into a full draft."

If they say yes, read the file content (ideas stub or any notes), then write a full draft
following the blog's voice and style:
- Direct, experience-based, metaphor-driven
- Short paragraphs, good rhythm
- Opinion-forward — no hedging
- Opening earns the reader in the first 2 sentences
- DHH-style: state conclusion up front, then explain why

After writing, show them the draft and ask if they'd like any changes.
