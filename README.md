# PyDocs

> Open-source service mapping Python packages to their GitHub source code, enabling AI coding agents to access dependency context via MCP.

## What is PyDocs?

PyDocs solves a common problem for AI coding agents: when you use a Python package in your code, the agent needs to understand how that package works to help you effectively. Instead of guessing or hallucinating, PyDocs provides direct access to the actual source code.

## How It Works

```
┌─────────────────┐
│  Coding Agent   │
│  (e.g. Claude)  │
└────────┬────────┘
         │ "I need context for 'requests' package"
         ↓
┌─────────────────┐
│  PyDocs MCP     │
│  Local Client   │
└────────┬────────┘
         │ Query: package name → GitHub repo
         ↓
┌─────────────────┐
│  PyDocs Cloud   │
│  API Service    │
└────────┬────────┘
         │ Returns: github.com/psf/requests
         ↓
┌─────────────────┐
│  MCP Client     │
│  Clones Repo    │
└────────┬────────┘
         │ Reads source files
         ↓
┌─────────────────┐
│  Coding Agent   │
│  Now has actual │
│  source context │
└─────────────────┘
```

## The Flow

1. **Agent needs context**: When you ask Claude (or another AI agent) to help with code that uses a package like `pandas`, the agent recognizes it needs to understand how that package works

2. **Package lookup**: The local MCP client queries PyDocs API: "What's the GitHub repo for `pandas`?"

3. **Mapping**: PyDocs returns the mapping: `pandas` → `https://github.com/pandas-dev/pandas`

4. **Source access**: The MCP client clones the repo and indexes the source code

5. **Contextual assistance**: The agent can now read the actual source files to understand usage patterns, APIs, and implementation details - just like it does when exploring your codebase

## Why This Matters

- **No hallucinations**: Agents work with real source code, not outdated training data
- **Up-to-date**: Always points to the latest source, even for newly released packages
- **Deep understanding**: Agents can read implementation details to provide accurate help
- **Same workflow**: Agents interact with dependencies the same way they interact with your code

## Components

### Cloud Infrastructure (This Repo)
- **Data Pipeline**: Ingests PyPI releases and maps packages to GitHub repos
- **API Service**: Provides fast lookups via REST API
- **Database**: PostgreSQL for package metadata and user management
- **Processing**: Cloud Functions for automated data updates

### MCP Client (Separate Repo)
- Local server that runs on developer's machine
- Connects AI agents to PyDocs API
- Handles repo cloning and source indexing
- Implements Model Context Protocol (MCP) spec

## Roadmap

- [x] PyPI package support
- [ ] npm package support
- [ ] Maven/Gradle support
- [ ] RubyGems support
- [ ] Crates.io (Rust) support

## Architecture

This repository contains the cloud infrastructure:

- `terraform/` - GCP infrastructure as code
- `backend/` - FastAPI service for package lookups
- `functions/` - Cloud Functions for data processing
- `queries/` - BigQuery SQL for data exports

## Contributing

This is an open-source project. Contributions welcome! Check the [Issues](../../issues) page for tasks or the [Project Board](../../projects) for current work.

## License

MIT License - see LICENSE file for details
