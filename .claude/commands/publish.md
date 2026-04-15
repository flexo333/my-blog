# /publish — Mark a post ready to publish

**Arguments:** $ARGUMENTS — the post slug (e.g. `/publish my-great-idea`)

If no argument provided, list files in `posts/` with `draft: true` and ask which to publish.

---

Run:
```bash
make publish POST=$ARGUMENTS
```

After publishing:
1. Show the updated frontmatter
2. Remind them to check `title:` and `description:` are set (the script adds placeholders)
3. Ask: "Ready to deploy? I can commit and push to trigger CI."

If they say yes, commit the post file and push to main:
```bash
git add posts/<slug>.md
git commit -m "Publish: <title>"
git push
```

Show the live URL when done: `https://<their-domain>/blog/<slug>`
