# /idea — Save a quick idea for a future post

**Arguments:** $ARGUMENTS — the idea title or a short description (e.g. `/idea why deploys should be boring`)

---

1. Slugify $ARGUMENTS: lowercase, spaces to hyphens, strip special characters.
2. Create `ideas/<slug>.md` with the raw $ARGUMENTS text as a one-line note inside.
   Do not add frontmatter — ideas are just stubs.
3. Commit the new file:
   ```bash
   git add ideas/<slug>.md
   git commit -m "idea: <slug>"
   ```
4. Confirm: show the file path and the content saved.
5. Remind them: run `/draft <slug>` when they're ready to turn it into a post.

If no argument is provided, list all files in `ideas/` so the user can see what's already there.
