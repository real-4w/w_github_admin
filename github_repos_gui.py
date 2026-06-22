"""List GitHub repositories in a GUI with description and status."""

from __future__ import annotations

import os
import sys
import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
from typing import Any, Literal

import requests
from dotenv import load_dotenv, set_key

SCRIPT_DIR = Path(__file__).resolve().parent
ENV_PATH = SCRIPT_DIR / ".env"
GITHUB_API = "https://api.github.com"

ThemeMode = Literal["auto", "dark", "light"]
SortColumn = Literal["name", "status", "updated"]

SORTABLE_COLUMNS: frozenset[SortColumn] = frozenset({"name", "status", "updated"})
COLUMN_LABELS: dict[str, str] = {
    "name": "Repository",
    "description": "Description",
    "status": "Status",
    "updated": "Last Updated",
    "stars": "Stars",
}


@dataclass(frozen=True)
class ThemeColors:
    bg: str
    surface: str
    surface_alt: str
    text: str
    text_muted: str
    border: str
    accent: str
    accent_hover: str
    heading_bg: str
    heading_text: str
    row_alt: str
    scrollbar: str


LIGHT_THEME = ThemeColors(
    bg="#f6f8fa",
    surface="#ffffff",
    surface_alt="#f6f8fa",
    text="#24292f",
    text_muted="#57606a",
    border="#d0d7de",
    accent="#0969da",
    accent_hover="#0550ae",
    heading_bg="#f6f8fa",
    heading_text="#24292f",
    row_alt="#f6f8fa",
    scrollbar="#d0d7de",
)

DARK_THEME = ThemeColors(
    bg="#0d1117",
    surface="#161b22",
    surface_alt="#1c2128",
    text="#e6edf3",
    text_muted="#8b949e",
    border="#30363d",
    accent="#1f6feb",
    accent_hover="#388bfd",
    heading_bg="#21262d",
    heading_text="#e6edf3",
    row_alt="#1c2128",
    scrollbar="#484f58",
)


def is_system_dark_mode() -> bool:
    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
            ) as key:
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return value == 0
        except OSError:
            pass
    return False


def load_theme_mode() -> ThemeMode:
    load_dotenv(ENV_PATH)
    mode = os.getenv("THEME", "auto").strip().lower()
    if mode in ("dark", "light", "auto"):
        return mode  # type: ignore[return-value]
    return "auto"


def save_theme_mode(mode: ThemeMode) -> None:
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not ENV_PATH.exists():
        ENV_PATH.touch()
    set_key(ENV_PATH, "THEME", mode)


def resolve_dark_mode(mode: ThemeMode) -> bool:
    if mode == "dark":
        return True
    if mode == "light":
        return False
    return is_system_dark_mode()


def apply_theme(root: tk.Tk, style: ttk.Style, dark: bool) -> ThemeColors:
    colors = DARK_THEME if dark else LIGHT_THEME
    root.configure(bg=colors.bg)

    style.theme_use("clam")
    style.configure(".", background=colors.bg, foreground=colors.text)
    style.configure("TFrame", background=colors.bg)
    style.configure("Surface.TFrame", background=colors.surface)
    style.configure(
        "TLabel",
        background=colors.bg,
        foreground=colors.text,
    )
    style.configure(
        "Muted.TLabel",
        background=colors.bg,
        foreground=colors.text_muted,
    )
    style.configure(
        "Heading.TLabel",
        background=colors.bg,
        foreground=colors.text,
    )
    style.configure(
        "TButton",
        background=colors.surface_alt,
        foreground=colors.text,
        bordercolor=colors.border,
        focuscolor=colors.accent,
        padding=(10, 4),
    )
    style.map(
        "TButton",
        background=[("active", colors.border), ("pressed", colors.border)],
        foreground=[("disabled", colors.text_muted)],
    )
    style.configure(
        "Accent.TButton",
        background=colors.accent,
        foreground="#ffffff",
        bordercolor=colors.accent,
    )
    style.map(
        "Accent.TButton",
        background=[
            ("active", colors.accent_hover),
            ("pressed", colors.accent_hover),
        ],
    )
    style.configure(
        "Treeview",
        background=colors.surface,
        foreground=colors.text,
        fieldbackground=colors.surface,
        bordercolor=colors.border,
        lightcolor=colors.border,
        darkcolor=colors.border,
        rowheight=28,
    )
    style.configure(
        "Treeview.Heading",
        background=colors.heading_bg,
        foreground=colors.heading_text,
        bordercolor=colors.border,
        relief="flat",
        padding=(6, 4),
    )
    style.map(
        "Treeview",
        background=[("selected", colors.accent)],
        foreground=[("selected", "#ffffff")],
    )
    style.map(
        "Treeview.Heading",
        background=[("active", colors.surface_alt)],
    )
    style.configure(
        "Vertical.TScrollbar",
        background=colors.surface_alt,
        troughcolor=colors.bg,
        bordercolor=colors.border,
        arrowcolor=colors.text_muted,
    )
    style.configure(
        "Horizontal.TScrollbar",
        background=colors.surface_alt,
        troughcolor=colors.bg,
        bordercolor=colors.border,
        arrowcolor=colors.text_muted,
    )
    style.map(
        "Vertical.TScrollbar",
        background=[("active", colors.scrollbar)],
    )
    style.map(
        "Horizontal.TScrollbar",
        background=[("active", colors.scrollbar)],
    )

    return colors


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
    def __init__(self, root: tk.Tk, handle: str, theme_mode: ThemeMode) -> None:
        self.root = root
        self.handle = handle
        self.theme_mode = theme_mode
        self.dark_mode = resolve_dark_mode(theme_mode)
        self.style = ttk.Style(root)
        self.colors = apply_theme(root, self.style, self.dark_mode)

        self.root.title(f"GitHub Repositories — @{handle}")
        self.root.geometry("1100x600")
        self.root.minsize(800, 400)
        self.repos: list[dict[str, Any]] = []
        self.sort_column: SortColumn = "updated"
        self.sort_reverse = True

        self._build_ui()
        self._load_repositories()

    def _toggle_theme(self) -> None:
        self.dark_mode = not self.dark_mode
        self.theme_mode = "dark" if self.dark_mode else "light"
        save_theme_mode(self.theme_mode)
        self.colors = apply_theme(self.root, self.style, self.dark_mode)
        self.tree.tag_configure("even", background=self.colors.surface)
        self.tree.tag_configure("odd", background=self.colors.row_alt)
        self.theme_button.configure(text=self._theme_button_label())
        self.heading_label.configure(style="Heading.TLabel")
        self.status_label.configure(style="Muted.TLabel")
        self._refresh_row_tags()

    def _theme_button_label(self) -> str:
        return "Light mode" if self.dark_mode else "Dark mode"

    def _refresh_row_tags(self) -> None:
        for index, item in enumerate(self.tree.get_children()):
            url_tags = self.tree.item(item, "tags")
            url = url_tags[0] if url_tags else ""
            row_tag = "even" if index % 2 == 0 else "odd"
            self.tree.item(item, tags=(url, row_tag))

    def _build_ui(self) -> None:
        toolbar = ttk.Frame(self.root, padding=(8, 8, 8, 0))
        toolbar.pack(fill=tk.X)

        self.heading_label = ttk.Label(
            toolbar,
            text=f"@{self.handle}",
            style="Heading.TLabel",
            font=("Segoe UI", 11, "bold"),
        )
        self.heading_label.pack(side=tk.LEFT)

        self.theme_button = ttk.Button(
            toolbar,
            text=self._theme_button_label(),
            command=self._toggle_theme,
        )
        self.theme_button.pack(side=tk.RIGHT, padx=(8, 0))

        ttk.Button(toolbar, text="Refresh", command=self._load_repositories).pack(
            side=tk.RIGHT
        )

        self.status_var = tk.StringVar(value="Loading repositories...")
        self.status_label = ttk.Label(
            self.root,
            textvariable=self.status_var,
            style="Muted.TLabel",
            padding=(8, 4),
        )
        self.status_label.pack(anchor=tk.W)

        table_frame = ttk.Frame(self.root, padding=8)
        table_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("name", "description", "status", "updated", "stars")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        self._configure_column_headings()

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

        self.tree.tag_configure("even", background=self.colors.surface)
        self.tree.tag_configure("odd", background=self.colors.row_alt)
        self.tree.bind("<Double-1>", self._open_selected_repo)

    def _configure_column_headings(self) -> None:
        for column, label in COLUMN_LABELS.items():
            text = label
            if column == self.sort_column:
                text += " ▼" if self.sort_reverse else " ▲"
            if column in SORTABLE_COLUMNS:
                self.tree.heading(
                    column,
                    text=text,
                    command=lambda col=column: self._sort_by(col),  # type: ignore[arg-type]
                )
            else:
                self.tree.heading(column, text=text)

    def _sort_key(self, repo: dict[str, Any], column: SortColumn) -> str:
        if column == "name":
            return (repo.get("name") or "").lower()
        if column == "status":
            return repo_status(repo).lower()
        return repo.get("updated_at") or ""

    def _sorted_repos(self) -> list[dict[str, Any]]:
        return sorted(
            self.repos,
            key=lambda repo: self._sort_key(repo, self.sort_column),
            reverse=self.sort_reverse,
        )

    def _sort_by(self, column: SortColumn) -> None:
        if column not in SORTABLE_COLUMNS:
            return
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = column == "updated"
        self._configure_column_headings()
        self._render_table()

    def _clear_table(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _render_table(self) -> None:
        self._clear_table()
        for index, repo in enumerate(self._sorted_repos()):
            updated = (repo.get("updated_at") or "")[:10]
            row_tag = "even" if index % 2 == 0 else "odd"
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
                tags=(repo.get("html_url", ""), row_tag),
            )
        self.status_var.set(f"{len(self.repos)} repositories loaded for @{self.handle}")

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
        self.repos = repos
        self._render_table()

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
    theme_mode = load_theme_mode()
    apply_theme(root, ttk.Style(root), resolve_dark_mode(theme_mode))
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
    GitHubReposApp(root, handle, theme_mode)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())