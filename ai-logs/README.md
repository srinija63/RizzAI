## AI logs (REQUIRED)

This project requires **ongoing AI conversation logs** in `./ai-logs/`.

### What you need to do (Cursor)

- Open **Chat** panel
- Click **"..." → Export conversation**
- Save the export as a `.txt` file into `./ai-logs/`

Suggested naming:

- `cursor-chat-YYYY-MM-DD.txt`
- `cursor-chat-YYYY-MM-DD-2.txt` (if multiple exports in one day)

### When to update logs

- Export and save after each meaningful build session (or at least daily).
- Keep older exports — do not overwrite.

### Git workflow (after exporting into `ai-logs/`)

```bash
git add ai-logs
git commit -m "chore(ai-logs): add Cursor chat export"
git push
```

