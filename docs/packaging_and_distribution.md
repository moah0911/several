     # Packaging & Distribution Plan

## Several: Universal AI Agent Orchestrator

**Version:** 1.0.0  
**Date:** 2026-02-21  
**Status:** Draft  

---

## 1. Overview

This document outlines the packaging, distribution, and installation strategy for Several. The goal is to make installation as simple as `pip install several` while providing platform-specific options for optimal user experience.

---

## 2. Distribution Channels

### 2.1 Primary Channels

| Channel | Priority | Target Users | Use Case |
|---------|----------|--------------|----------|
| **PyPI** | P0 | Python developers, general users | Universal, cross-platform |
| **Homebrew** | P1 | macOS developers | Native macOS experience |
| **AUR** | P2 | Arch Linux users | Rolling release, bleeding edge |
| **Snap** | P2 | Ubuntu/Debian users | Sandboxed, auto-updating |
| **Binary Releases** | P2 | CI/CD, air-gapped environments | No Python dependency |
| **Docker** | P3 | Containerized workflows | Isolated, reproducible |

### 2.2 Distribution Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     SOURCE CODE                                  │
│                    (GitHub: several-ai/several)                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌────────────┐   ┌────────────┐   ┌────────────┐
    │   PyPI     │   │  Homebrew  │   │   AUR      │
    │  (sdist)   │   │   Formula  │   │  PKGBUILD  │
    │  (wheel)   │   │            │   │            │
    └──────┬─────┘   └──────┬─────┘   └──────┬─────┘
           │               │               │
           └───────────────┼───────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
      [pip install]   [brew install]   [yay -S]
      several         several-ai       several-ai
                           │
                           ▼
                  ┌─────────────────┐
                  │     USERS       │
                  └─────────────────┘
```

---

## 3. PyPI Package (Primary)

### 3.1 Package Structure

```
several-1.0.0/
├── pyproject.toml           # Modern Python packaging
├── README.md
├── LICENSE
├── CHANGELOG.md
├── src/
│   └── several/
│       ├── __init__.py
│       ├── __main__.py      # python -m several
│       ├── cli.py           # Entry point
│       ├── tui/             # Textual UI components
│       ├── core/            # Orchestration logic
│       ├── adapters/        # Agent adapters
│       └── config/          # Default configs
├── tests/
└── docs/
```

### 3.2 pyproject.toml Configuration

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[project]
name = "several"
dynamic = ["version"]
description = "Universal AI Agent Orchestrator - Run Claude, Codex, Gemini, and more in parallel"
readme = "README.md"
license = "MIT"
requires-python = ">=3.9"
authors = [
    { name = "Gowtham Boyina", email = "gowtham@example.com" }
]
keywords = ["ai", "cli", "agent", "orchestrator", "claude", "codex", "gemini", "tui"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Tools",
    "Topic :: Utilities",
]

dependencies = [
    # Core TUI
    "textual>=0.52.0",
    "rich>=13.0.0",
    
    # Async & Process Management
    "asyncio-pty>=0.1.0",
    "anyio>=4.0.0",
    
    # Data & Config
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "PyYAML>=6.0",
    "aiosqlite>=0.19.0",
    
    # CLI & Utilities
    "typer>=0.9.0",
    "click>=8.0.0",
    "structlog>=23.0.0",
    
    # Security
    "cryptography>=41.0.0",
    "keyring>=24.0.0",
    
    # Progress & UX
    "tqdm>=4.65.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
    "textual-dev>=1.0.0",
]
docs = [
    "mkdocs>=1.5.0",
    "mkdocs-material>=9.0.0",
]

[project.scripts]
several = "several.cli:main"
svr = "several.cli:main"  # Short alias

[project.urls]
Homepage = "https://github.com/several-ai/several"
Documentation = "https://several-ai.github.io/several"
Repository = "https://github.com/several-ai/several"
Issues = "https://github.com/several-ai/several/issues"
Changelog = "https://github.com/several-ai/several/blob/main/CHANGELOG.md"

[tool.hatch.version]
source = "vcs"

[tool.hatch.build.targets.sdist]
include = [
    "/src",
    "/tests",
    "/docs",
    "/README.md",
    "/LICENSE",
]

[tool.hatch.build.targets.wheel]
packages = ["src/several"]
```

### 3.3 Installation Methods

```bash
# Standard installation
pip install several

# With all optional dependencies
pip install several[dev,docs]

# User installation (no sudo)
pip install --user several

# Specific version
pip install several==1.0.0

# Development install
git clone https://github.com/several-ai/several.git
cd several
pip install -e ".[dev]"
```

---

## 4. Homebrew (macOS)

### 4.1 Formula (several-ai/homebrew-tap)

```ruby
# Formula/several.rb
class Several < Formula
  desc "Universal AI Agent Orchestrator - Run Claude, Codex, Gemini in parallel"
  homepage "https://github.com/several-ai/several"
  url "https://github.com/several-ai/several/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "SHA256_HASH_HERE"
  license "MIT"
  head "https://github.com/several-ai/several.git", branch: "main"

  depends_on "python@3.11"
  depends_on "rust" => :build  # If we add Rust components later

  resource "textual" do
    url "https://files.pythonhosted.org/packages/.../textual-0.52.0.tar.gz"
    sha256 "..."
  end

  # ... other resources or use poetry/pip for deps

  def install
    virtualenv_install_with_resources
    
    # Install shell completions
    generate_completions_from_executable(bin/"several", "--generate-completion")
    
    # Create default config directory
    (var/"several").mkpath
  end

  def post_install
    # Remind users to install agent CLIs
    ohai "Several installed!"
    ohai "Remember to install AI agent CLIs:"
    puts "  - Claude Code: npm install -g @anthropic-ai/claude-code"
    puts "  - OpenAI Codex: npm install -g @openai/codex"
    puts "  - Google Gemini: gemini install (see docs)"
  end

  test do
    system "#{bin}/several", "--version"
    system "#{bin}/several", "agents", "list"
  end
end
```

### 4.2 Installation

```bash
# Add tap
brew tap several-ai/tap

# Install
brew install several-ai

# Or install from source
brew install --HEAD several-ai

# Upgrade
brew upgrade several-ai
```

---

## 5. Arch Linux (AUR)

### 5.1 PKGBUILD

```bash
# PKGBUILD
pkgname=several-ai
pkgver=1.0.0
pkgrel=1
pkgdesc="Universal AI Agent Orchestrator - Run Claude, Codex, Gemini in parallel"
arch=('any')
url="https://github.com/several-ai/several"
license=('MIT')
depends=(
    'python>=3.9'
    'python-textual'
    'python-rich'
    'python-pydantic'
    'python-pyyaml'
    'python-aiosqlite'
    'python-typer'
    'python-structlog'
    'python-cryptography'
    'python-keyring'
    'python-tqdm'
)
makedepends=('python-build' 'python-installer' 'python-wheel' 'python-hatchling')
optdepends=(
    'claude-code: Anthropic Claude support'
    'openai-codex: OpenAI Codex support'
    'google-gemini-cli: Google Gemini support'
    'qwen-code: Alibaba Qwen support'
)
source=("$pkgname-$pkgver.tar.gz::https://github.com/several-ai/several/archive/v$pkgver.tar.gz")
sha256sums=('SKIP')

build() {
    cd "$srcdir/several-$pkgver"
    python -m build --wheel --no-isolation
}

package() {
    cd "$srcdir/several-$pkgver"
    python -m installer --destdir="$pkgdir" dist/*.whl
    
    # Install license
    install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
    
    # Install docs
    install -Dm644 README.md "$pkgdir/usr/share/doc/$pkgname/README.md"
    
    # Install shell completions
    install -Dm644 completions/several.bash "$pkgdir/usr/share/bash-completion/completions/several"
    install -Dm644 completions/several.zsh "$pkgdir/usr/share/zsh/site-functions/_several"
    install -Dm644 completions/several.fish "$pkgdir/usr/share/fish/vendor_completions.d/several.fish"
}
```

### 5.2 Installation

```bash
# Using yay
yay -S several-ai

# Using paru
paru -S several-ai

# Build from source
git clone https://aur.archlinux.org/several-ai.git
cd several-ai
makepkg -si
```

---

## 6. Snap Package

### 6.1 snapcraft.yaml

```yaml
name: several-ai
base: core22
version: '1.0.0'
summary: Universal AI Agent Orchestrator
description: |
  Several is a TUI application that allows you to orchestrate multiple 
  AI coding agents (Claude Code, Codex, Gemini CLI, Qwen Code, etc.) 
  from a single unified interface. Run tasks in parallel with real-time 
  progress tracking.

grade: stable
confinement: classic  # Required for accessing user-installed CLIs

parts:
  several:
    plugin: python
    source: .
    python-packages:
      - textual
      - rich
      - pydantic
      - pyyaml
      - aiosqlite
      - typer
      - structlog
      - cryptography
      - keyring
      - tqdm
    stage-packages:
      - git
      - libsqlite3-0

apps:
  several:
    command: bin/several
    environment:
      PYTHONPATH: $SNAP/lib/python3.10/site-packages
    plugs:
      - home
      - removable-media
      - ssh-keys  # For git operations

  svr:
    command: bin/svr
    environment:
      PYTHONPATH: $SNAP/lib/python3.10/site-packages
```

### 6.2 Installation

```bash
# Install
sudo snap install several-ai --classic

# Update
sudo snap refresh several-ai

# Remove
sudo snap remove several-ai
```

---

## 7. Binary Releases

### 7.1 PyInstaller Build

```python
# build-binary.py
import PyInstaller.__main__
import platform

def build():
    system = platform.system().lower()
    arch = platform.machine().lower()
    
    name = f"several-{system}-{arch}"
    
    PyInstaller.__main__.run([
        'several.spec',
        '--name', name,
        '--onefile',
        '--clean',
    ])

if __name__ == "__main__":
    build()
```

### 7.2 GitHub Actions Release Workflow

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        include:
          - os: ubuntu-latest
            target: linux-x64
          - os: macos-latest
            target: macos-x64
          - os: macos-14
            target: macos-arm64
          - os: windows-latest
            target: windows-x64

    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install pyinstaller
          pip install -e .
      
      - name: Build binary
        run: python build-binary.py
      
      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: several-${{ matrix.target }}
          path: dist/several-*

  release:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v4
      
      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: several-*/several-*
          generate_release_notes: true
```

---

## 8. Docker Distribution

### 8.1 Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim as builder

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install build && \
    python -m build --wheel

# Runtime image
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy wheel from builder
COPY --from=builder /app/dist/*.whl /tmp/
RUN pip install /tmp/*.whl && rm /tmp/*.whl

# Create non-root user
RUN useradd -m -u 1000 several
USER several

# Default to TUI (requires -it)
ENTRYPOINT ["several"]
CMD ["--help"]
```

### 8.2 Usage

```bash
# Build
docker build -t several-ai:latest .

# Run TUI (interactive)
docker run -it --rm \
  -v $(pwd):/workspace \
  -v ~/.several:/home/several/.local/share/several \
  several-ai:latest

# Run CLI mode
docker run --rm \
  -v $(pwd):/workspace \
  -v ~/.several:/home/several/.local/share/several \
  several-ai:latest task -a claude "Refactor auth module"
```

---

## 9. Installation Verification

### 9.1 Post-Install Checks

```bash
# Verify installation
several --version
# Output: several 1.0.0

# Check dependencies
several doctor
# Output:
# ✓ Python 3.11.4
# ✓ Textual 0.52.0
# ✓ SQLite 3.42.0
# ✓ Git 2.42.0
# ✓ Terminal supports truecolor

# Detect available agents
several agents list --installed
# Output:
# ✓ claude (v0.2.45)
# ✓ codex (v1.0.0)
# ✗ gemini (not installed)
```

### 9.2 Shell Completion Installation

```bash
# Bash
several --generate-completion bash | sudo tee /etc/bash_completion.d/several

# Zsh
several --generate-completion zsh | sudo tee /usr/share/zsh/site-functions/_several

# Fish
several --generate-completion fish | tee ~/.config/fish/completions/several.fish
```

---

## 10. Update Mechanism

### 10.1 Version Check

```python
# several/update.py
import requests
from packaging import version

def check_update() -> Optional[str]:
    """Check if update is available."""
    try:
        response = requests.get(
            "https://pypi.org/pypi/several/json",
            timeout=5
        )
        data = response.json()
        latest = data["info"]["version"]
        current = get_version()
        
        if version.parse(latest) > version.parse(current):
            return latest
    except Exception:
        pass
    return None
```

### 10.2 Auto-Update (Optional)

```bash
# Check for updates on startup (can disable)
several config set check_updates true

# Manual update
pip install --upgrade several

# Or platform-specific
brew upgrade several-ai
yay -Syu several-ai
sudo snap refresh several-ai
```

---

## 11. Uninstallation

### 11.1 Clean Removal

```bash
# PyPI
pip uninstall several
rm -rf ~/.local/share/several
rm -rf ~/.config/several

# Homebrew
brew uninstall several-ai
rm -rf ~/.local/share/several

# AUR
yay -R several-ai
rm -rf ~/.local/share/several

# Snap
sudo snap remove several-ai
```

### 11.2 Data Preservation

Before uninstall, users can export data:

```bash
# Export all sessions
several sessions export-all --output ./several-backup/

# Export config
cp -r ~/.local/share/several/config ./several-config-backup/
```

---
