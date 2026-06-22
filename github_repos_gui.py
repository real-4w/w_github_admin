"""List GitHub repositories in a GUI with description and status."""

from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
from typing import Any

import requests
from dotenv import load_dotenv, set_key

SCRIPT_DIR = Path(__file__).resolve().parent
ENV_PATH = SCRIPT_DIR / ".env"
GITHUB_API = "https://api.github.com"


def load_github_handle() -> str | None:
    load_dotenv(ENV_PATH)
    handle = os.getenv("GITHUB_HANDLE", "").strip()
    return handle or None


def save_github_handle(handle: str) -> None:
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not ENV_PATH.exists():
        ENV_PATH.touch()
    set_key(ENV_PATH, "GITHUB_HANDLE", handle)


def prompt_for_handle(root: tk.Tk) -> str | None:
    handle = simpledialog.askstring(
        "GitHub Handle",
        "Enter your GitHub username (handle):",
        parent=root,
    )
    if handle is None:
        return None
    handle = handle.strip().lstrip("@")
    if not handle:
        messagebox.showerror("Invalid Handle", "GitHub handle cannot be empty.", parent=root)
        return None
    return handle


def repo_status(repo: dict[str, Any]) -> str:
    parts: list[str] = []
    if repo.get("archived"):
        parts.append("Archived")
    if repo.get("disabled"):
        parts.append("Disabled")
    if repo.get("fork"):
        parts.append("Fork")
    parts.append("Private" if repo.get("private") else "Public")
    return " · ".join(parts)


def fetch_repositories(handle: str, token: str | None) -> list[dict[str, Any]]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Authenticated requests include private repos; public API is public-only.
    url = f"{GITHUB_API}/user/repos" if token else f"{GITHUB_API}/users/{handle}/repos"

    repos: list[dict[str, Any]] = []
    page = 1
    per_page = 100

    while True:
        response = requests.get(
            url,
            headers=headers,
            params={
                "per_page": per_page,
                "page": page,
                "sort": "updated",
                "direction": "desc",
                "affiliation": "owner,collaborator,organization_member",
            },
            timeout=30,
        )
        if response.status_code == 404:
            raise ValueError(f"GitHub user '{handle}' was not found.")
        if response.status_code == 401:
            raise ValueError("Invalid GITHUB_TOKEN in .env.")
        if response.status_code == 403:
            raise ValueError(
                "GitHub API rate limit exceeded or access denied. "
                "Add GITHUB_TOKEN to .env for higher limits and private repos."
            )
        response.raise_for_status()

        batch = response.json()
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < per_page:
            break
        page += 1

    return repos


class GitHubReposApp:
    def __init__(self, root: tk.Tk, handle: str) -> None:
        self.root = root
        self.handle = handle
        self.root.title(f"GitHub Repositories — @{handle}")
        self.root.geometry("1100x600")
        self.root.minsize(800, 400)

        self._build_ui()
        self._load_repositories()

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self.root, padding=(8, 8, 8, 0))
        toolbar.pack(fill=tk.X)

        ttk.Label(toolbar, text=f"@{self.handle}", font=("Segoe UI", 11, "bold")).pack(
            side=tk.LEFT
        )
        ttk.Button(toolbar, text="Refresh", command=self._load_repositories).pack(
            side=tk.RIGHT
        )

        self.status_var = tk.StringVar(value="Loading repositories...")
        ttk.Label(self.root, textvariable=self.status_var, padding=(8, 4)).pack(
            anchor=tk.W
        )

        table_frame = ttk.Frame(self.root, padding=8)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("name", "description", "status", "updated", "stars")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("name", text="Repository")
        self.tree.heading("description", text="Description")
        self.tree.heading("status", text="Status")
        self.tree.heading("updated", text="Last Updated")
        self.tree.heading("stars", text="Stars")

        self.tree.column("name", width=200, minwidth=120, stretch=False)
        self.tree.column("description", width=480, minwidth=200)
        self.tree.column("status", width=160, minwidth=120, stretch=False)
        self.tree.column("updated", width=130, minwidth=100, stretch=False)
        self.tree.column("stars", width=70, minwidth=60, stretch=False, anchor=tk.CENTER)

        y_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self._open_selected_repo)

    def _clear_table(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _populate_table(self, repos: list[dict[str, Any]]) -> None:
        self._clear_table()
        for repo in repos:
            updated = (repo.get("updated_at") or "")[:10]
            self.tree.insert(
                "",
                tk.END,
                values=(
                    repo.get("name", ""),
                    repo.get("description") or "(no description)",
                    repo_status(repo),
                    updated,
                    repo.get("stargazers_count", 0),
                ),
                tags=(repo.get("html_url", ""),),
            )
        self.status_var.set(f"{len(repos)} repositories loaded for @{self.handle}")

    def _load_repositories(self) -> None:
        self.status_var.set("Loading repositories...")
        self.tree.configure(cursor="watch")
        self.root.update_idletasks()

        token = os.getenv("GITHUB_TOKEN", "").strip() or None

        def worker() -> None:
            try:
                repos = fetch_repositories(self.handle, token)
            except requests.RequestException as exc:
                self.root.after(0, lambda: self._on_load_error(str(exc)))
                return
            except ValueError as exc:
                self.root.after(0, lambda: self._on_load_error(str(exc)))
                return

            self.root.after(0, lambda: self._on_load_success(repos))

        threading.Thread(target=worker, daemon=True).start()

    def _on_load_success(self, repos: list[dict[str, Any]]) -> None:
        self.tree.configure(cursor="")
        self._populate_table(repos)

    def _on_load_error(self, message: str) -> None:
        self.tree.configure(cursor="")
        self.status_var.set("Failed to load repositories.")
        messagebox.showerror("Error", message, parent=self.root)

    def _open_selected_repo(self, _event: tk.Event) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        tags = self.tree.item(selection[0], "tags")
        if tags:
            import webbrowser

            webbrowser.open(tags[0])


def main() -> int:
    root = tk.Tk()
    root.withdraw()

    handle = load_github_handle()
    if not handle:
        handle = prompt_for_handle(root)
        if not handle:
            root.destroy()
            return 1
        save_github_handle(handle)

    load_dotenv(ENV_PATH)
    root.deiconify()
    GitHubReposApp(root, handle)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())