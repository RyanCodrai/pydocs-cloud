# Sourced.dev

[![Website](https://img.shields.io/badge/Website-sourced.dev-blue)](https://sourced.dev)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![PyPI Packages](https://img.shields.io/badge/PyPI_Packages-800k+-orange)](https://sourced.dev)
[![npm Packages](https://img.shields.io/badge/npm_Packages-3M+-yellow)](https://sourced.dev)
[![MCP](https://img.shields.io/badge/MCP-Compatible-purple)](https://modelcontextprotocol.io)

Source code search for every package on PyPI and npm.

Sourced.dev provides coding agents with direct access to dependency source code through the [Model Context Protocol](https://modelcontextprotocol.io) (MCP). Instead of relying on training data or web searches, agents can read, search, and navigate the actual source of any package — as if it were on your local machine.

Currently tracking all 800,000+ Python packages and all 3,000,000+ npm packages. New releases are indexed within 5 minutes of publication.

## Quick Start

Install the MCP server in one command. It authenticates via GitHub and configures your coding agents automatically:

```sh
curl -sL sourced.dev/install | sh
```

The installer will:

1. Authorize with GitHub.
2. Create an API key.
3. Configure the MCP server for your selected agents.

Restart your coding agents after installation to start using Sourced.

## Supported Agents

The following coding agents are supported out of the box:

- [Claude Code](https://claude.ai/claude-code)
- [Claude Desktop](https://claude.ai/download) (macOS)
- [Cursor](https://cursor.sh)
- [VS Code](https://code.visualstudio.com)
- [Windsurf](https://codeium.com/windsurf)
- [Codex](https://github.com/openai/codex)
- [Gemini CLI](https://github.com/google-gemini/gemini-cli)
- [Kiro](https://kiro.dev)
- [Zed](https://zed.dev)
- [OpenCode](https://opencode.ai)
- [Copilot CLI](https://githubnext.com/projects/copilot-cli)
- [Antigravity](https://github.com/google-gemini/antigravity)

## Capabilities

Sourced.dev exposes the following tools to your coding agent via MCP:

| Tool | Description |
|------|-------------|
| `read` | Read a file from a package's source code with line numbers. |
| `grep` | Search for a regex pattern across a package's source tree. |
| `glob` | Find files matching a glob pattern within a package. |

All tools accept an `ecosystem` (e.g. `pypi`, `npm`), a `package_name`, and an optional `version` (defaults to latest).

## Ecosystem Support

- **PyPI** — 800,000+ packages
- **npm** — 3,000,000+ packages
- Maven/Gradle — planned
- RubyGems — planned
- Crates.io (Rust) — planned

## Next Steps

- Visit [sourced.dev](https://sourced.dev) to learn more.
- View the [Issues](https://github.com/RyanCodrai/sourced/issues) page to see open tasks or report a bug.
- Open a [Pull Request](https://github.com/RyanCodrai/sourced/pulls) to contribute.

## License

MIT License — see [LICENSE](LICENSE) for details.
