# Prompt: Add Bitcoin Orange Favicon to Web UI
Generated: 2026-03-30T00:42:00Z
Task Type: feature

## Context Section
**Project Overview:** BitbotV7 is a cryptocurrency trading bot with a Flask-based web UI running on Raspberry Pi 3B. The application provides real-time price charts, trade logs, and bot controls.

**Current State:** The web UI at `src/ui/templates/index.html` displays "BitbotV7" as the tab title. There's already a Bitcoin-style "B" symbol in the navbar (line 82) styled with orange color `#f7931a`.

## Task Section
Add a **favicon** that appears in browser tabs and bookmarks, displaying a Bitcoin-style icon with:
- Orange circular background (`#f7931a`)
- White "B" character centered

## Requirements Section
- Use inline SVG data URI (no external file needed)
- Follow existing code style in `index.html`
- Place the favicon link in the `<head>` section after the title tag
- The icon should be visible immediately without page reload

## Code Reference Section
**File to modify:** `src/ui/templates/index.html`

**Current state (line 6):**
```html
<title>BitbotV7</title>
```

**Exact change needed - add after line 6:**
```html
<link rel="icon" href='data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="48" fill="%23f7931a"/><text x="50" y="68" font-size="70" text-anchor="middle" fill="white" font-family="Arial, sans-serif" font-weight="bold">B</text></svg>' type="image/svg+xml">
```

## Success Criteria Section
- [ ] Favicon link tag added to `<head>` section in `index.html`
- [ ] Uses valid inline SVG data URI format
- [ ] Orange circle with white "B" character visible
- [ ] No syntax errors introduced
- [ ] Page still renders correctly after change
