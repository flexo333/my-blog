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
3. Ask: "Ready to deploy? Run `make deploy` or `git push` to trigger CI."

If they say deploy now:
```bash
make deploy
```

Show the live URL when done: `https://<their-domain>/blog/<slug>`
