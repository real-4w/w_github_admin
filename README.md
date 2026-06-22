# GitHub Repositories GUI

A small Python desktop app that lists your GitHub repositories in a table with description, status, last updated date, and star count. Supports dark mode and saves your settings in a local `.env` file.

## Quick start

1. Install dependencies:

```powershell
pip install -r requirements.txt
```

2. Run the app:

```powershell
python github_repos_gui.py
```

3. On first launch, enter your GitHub username. It is saved to `.env` as `GITHUB_HANDLE`.

## Environment variables

Create a `.env` file in this folder (or let the app create it for you):

```env
GITHUB_HANDLE=your-username
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
THEME=auto
```

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_HANDLE` | Yes | Your GitHub username |
| `GITHUB_TOKEN` | No | Personal access token for private repos and higher API rate limits |
| `THEME` | No | `auto` (default), `dark`, or `light` |

Without a token, only **public** repositories are listed. With a token, the app can also list **private** repositories you have access to.

---

## How to obtain a GitHub token

A **Personal Access Token (PAT)** acts like a password for the GitHub API. This app uses it only to read your repository list.

> **Keep your token secret.** Never commit it to git, share it, or paste it into public issues. The `.env` file is already listed in `.gitignore`.

### Option A: Fine-grained token (recommended)

Fine-grained tokens are limited to specific repositories and permissions.

1. Sign in to [GitHub](https://github.com).
2. Open **Settings** → **Developer settings** → **Personal access tokens** → **Fine-grained tokens**.  
   Direct link: [github.com/settings/personal-access-tokens](https://github.com/settings/personal-access-tokens)
3. Click **Generate new token**.
4. Set:
   - **Token name:** e.g. `github-repos-gui`
   - **Expiration:** choose a duration you are comfortable with (e.g. 90 days)
   - **Resource owner:** your personal account
   - **Repository access:**  
     - **All repositories** — lists every repo you own  
     - **Only select repositories** — limits access to chosen repos
5. Under **Permissions → Repository permissions**, set:
   - **Metadata:** `Read-only`  
     This is enough for listing repositories.
6. Click **Generate token**.
7. Copy the token immediately. GitHub will not show it again.

Add it to `.env`:

```env
GITHUB_TOKEN=github_pat_xxxxxxxxxxxx
```

### Option B: Classic token

Classic tokens use broad scopes. Use this if fine-grained tokens are not available in your organization.

1. Sign in to [GitHub](https://github.com).
2. Open **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**.  
   Direct link: [github.com/settings/tokens](https://github.com/settings/tokens)
3. Click **Generate new token (classic)**.
4. Set:
   - **Note:** e.g. `github-repos-gui`
   - **Expiration:** your preferred expiry
   - **Scopes:** enable **`repo`**  
     Required to list private repositories.  
     If you only need public repos, you can skip the token entirely.
5. Click **Generate token**.
6. Copy the token immediately.

Add it to `.env`:

```env
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
```

### Verify the token works

After saving `.env`, restart the app and click **Refresh**. You should see private repositories appear if your token has the correct access.

If you get an error:

- **Invalid GITHUB_TOKEN** — the token is wrong, expired, or revoked. Generate a new one.
- **Rate limit exceeded** — wait a few minutes, or ensure `GITHUB_TOKEN` is set (authenticated requests get a much higher limit).
- **Access denied** — check that the token has **Metadata (read)** for fine-grained tokens, or **`repo`** for classic tokens.

### Revoking a token

If a token is exposed or no longer needed:

1. Go to [github.com/settings/tokens](https://github.com/settings/tokens) (fine-grained or classic, depending on which you created).
2. Find the token and click **Delete** or **Revoke**.
3. Remove it from your `.env` file.

## Features

- Repository name, description, status (Public/Private, Archived, Fork), last updated, stars
- Double-click a row to open the repo in your browser
- Dark mode with automatic Windows theme detection
- Manual light/dark toggle (saved to `.env`)