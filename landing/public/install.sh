#!/bin/sh
set -e

# sourced.dev MCP server installer
# Usage: curl -sL sourced.dev/install | sh

GITHUB_CLIENT_ID="Ov23licLaZ5SAKAW8vZO"
API_BASE="${API_BASE:-https://api.sourced.dev}"
MCP_URL="${MCP_URL:-https://mcp.sourced.dev/mcp}"
PORT=8123
REDIRECT_URI="http://localhost:${PORT}/callback"

# --- Formatting ---

BOLD=''
DIM=''
GREEN=''
BOLD_GREEN=''
RED=''
ORANGE=''
GRAY=''
STRIKE=''
RESET=''
HIDE_CURSOR=''
SHOW_CURSOR=''

if [ -t 1 ]; then
  BOLD='\033[1m'
  DIM='\033[2m'
  GREEN='\033[0;32m'
  BOLD_GREEN='\033[1;32m'
  RED='\033[0;31m'
  ORANGE='\033[38;2;255;153;51m'
  GRAY='\033[38;2;119;119;119m'
  STRIKE='\033[9m'
  RESET='\033[0m'
  HIDE_CURSOR='\033[?25l'
  SHOW_CURSOR='\033[?25h'
fi

STEP1="Authorize with GitHub"
STEP2="Create API key"
STEP3="Configure MCP"

# Number of step lines (used for cursor movement)
NSTEPS=3

# --- Helpers ---

# Print all steps. Args: status1 status2 status3
# status: pending | active | done | fail
draw_steps() {
  i=1
  for status in "$1" "$2" "$3"; do
    case $i in
      1) label="$STEP1" ;;
      2) label="$STEP2" ;;
      3) label="$STEP3" ;;
    esac
    case $status in
      pending) printf "   ${DIM}□ %s${RESET}\033[K\n" "$label" ;;
      active)  printf "   ${ORANGE}■ ${BOLD}%s${RESET}\033[K\n" "$label" ;;
      done)    printf "   ${GREEN}✓${RESET} ${DIM}${STRIKE}%s${RESET}\033[K\n" "$label" ;;
      fail)    printf "   ${RED}✗ %s${RESET}\033[K\n" "$label" ;;
    esac
    i=$((i + 1))
  done
}

# Move cursor up N lines and redraw steps
update_steps() {
  printf "\033[${NSTEPS}A"
  draw_steps "$1" "$2" "$3"
}

# Get display name for an agent id
agent_label() {
  case $1 in
    claude_code) echo "Claude Code" ;;
    claude_desktop) echo "Claude Desktop" ;;
    cursor) echo "Cursor" ;;
    vscode) echo "VS Code" ;;
    windsurf) echo "Windsurf" ;;
    codex) echo "Codex" ;;
    gemini_cli) echo "Gemini CLI" ;;
    kiro) echo "Kiro CLI" ;;
    zed) echo "Zed" ;;
    opencode) echo "OpenCode" ;;
    copilot_cli) echo "Copilot CLI" ;;
    antigravity) echo "Antigravity" ;;
    *) echo "$1" ;;
  esac
}

# --- Check dependencies ---

if ! command -v curl > /dev/null 2>&1; then
  printf "${RED}error${RESET}: curl is required. Install it and try again.\n"
  exit 1
fi

if ! command -v nc > /dev/null 2>&1; then
  printf "${RED}error${RESET}: netcat (nc) is required. Install it and try again.\n"
  printf "  macOS:  included by default\n"
  printf "  Linux:  sudo apt install netcat-openbsd\n"
  exit 1
fi

if ! command -v python3 > /dev/null 2>&1; then
  printf "${RED}error${RESET}: python3 is required. Install it and try again.\n"
  printf "  macOS:  xcode-select --install\n"
  printf "  Linux:  sudo apt install python3\n"
  exit 1
fi

# --- Welcome ---

printf "\n"
printf "${BOLD}sourced.dev${RESET}\n"
printf "${DIM}Give your coding agent access to dependency source code${RESET}\n"
printf "\n"
printf "${BOLD}Install sourced.dev MCP...${RESET}\n"

# Show all steps as pending
draw_steps pending pending pending

printf "\n"
printf "${DIM}Ready?${RESET}\n"

# Yes/No selector
_rdy_cur=1  # 1=Yes, 2=No
_rdy_render() {
  printf "\033[4A" > /dev/tty
  if [ "$_rdy_cur" = "1" ]; then
    printf "  › ${BOLD}Yes${RESET}\033[K\n" > /dev/tty
    printf "    No\033[K\n" > /dev/tty
  else
    printf "    Yes\033[K\n" > /dev/tty
    printf "  › ${BOLD}No${RESET}\033[K\n" > /dev/tty
  fi
  printf "\n" > /dev/tty
  printf "${GRAY}\033[3m↑↓ to navigate · Enter to confirm · Esc to cancel\033[23m${RESET}\033[K\n" > /dev/tty
}

# Print 4 blank lines (Yes, No, blank, hint), then render
printf "\n\n\n\n" > /dev/tty
printf "$HIDE_CURSOR" > /dev/tty
_rdy_render

_old_stty_rdy=$(stty -g < /dev/tty)
_rdy_cleanup() {
  stty "$_old_stty_rdy" < /dev/tty 2>/dev/null
  printf "$SHOW_CURSOR" > /dev/tty
}
trap '_rdy_cleanup' INT TERM

_rdy_done=false
while [ "$_rdy_done" = false ]; do
  stty raw -echo < /dev/tty
  _key=$(dd bs=1 count=1 2>/dev/null < /dev/tty)
  stty "$_old_stty_rdy" < /dev/tty

  case "$_key" in
    "$(printf '\033')")
      stty raw -echo min 0 time 1 < /dev/tty
      _k2=$(dd bs=1 count=1 2>/dev/null < /dev/tty)
      stty "$_old_stty_rdy" < /dev/tty
      if [ "$_k2" = "[" ]; then
        stty raw -echo < /dev/tty
        _k3=$(dd bs=1 count=1 2>/dev/null < /dev/tty)
        stty "$_old_stty_rdy" < /dev/tty
        case "$_k3" in
          A) _rdy_cur=1 ;;  # Up → Yes
          B) _rdy_cur=2 ;;  # Down → No
        esac
      else
        # Bare escape — cancel
        _rdy_cleanup
        printf "\nCancelled.\n" > /dev/tty
        exit 0
      fi
      ;;
    "$(printf '\r')"|"")  # Enter
      _rdy_done=true
      ;;
  esac
  _rdy_render
done

_rdy_cleanup

if [ "$_rdy_cur" = "2" ]; then
  printf "Cancelled.\n"
  exit 0
fi

# Clear the Ready selector (blank + Ready? + Yes + No + blank + hint = 6 lines)
printf "\033[6A\033[J"

# Move up past the steps to redraw them
update_steps active pending pending

# --- Step 1: Authorize with GitHub ---

auth_url="https://github.com/login/oauth/authorize?client_id=${GITHUB_CLIENT_ID}&redirect_uri=${REDIRECT_URI}&scope=user:email"

if command -v open > /dev/null 2>&1; then
  open "$auth_url"
elif command -v xdg-open > /dev/null 2>&1; then
  xdg-open "$auth_url"
else
  printf "\n  ${DIM}Open: %s${RESET}\n" "$auth_url"
fi

# Listen for OAuth callback using netcat, redirect browser to sourced.dev/authenticated
_response="HTTP/1.1 302 Found\r\nLocation: https://sourced.dev/authenticated\r\nConnection: close\r\n\r\n"
code=$(printf '%b' "$_response" | nc -l "$PORT" | head -1 | sed -n 's/.*code=\([^ &]*\).*/\1/p')

if [ -z "$code" ]; then
  update_steps fail pending pending
  printf "\n${RED}Failed to get authorization code from GitHub.${RESET}\n\n"
  exit 1
fi

update_steps done active pending

# --- Step 2: Create API key ---

auth_response=$(curl -s -X POST "${API_BASE}/api/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d "{\"code\": \"${code}\", \"redirect_uri\": \"${REDIRECT_URI}\"}")

api_key=$(echo "$auth_response" | grep -o '"api_key":"[^"]*"' | cut -d'"' -f4)

if [ -z "$api_key" ]; then
  update_steps done fail pending
  printf "\n${RED}Failed to create API key.${RESET}\n"
  printf "${DIM}%s${RESET}\n\n" "$auth_response"
  exit 1
fi

update_steps done done active

# --- Step 3: Configure MCP ---

OS=$(uname -s)

# --- All supported agents ---

ALL_AGENTS="claude_code cursor vscode windsurf codex gemini_cli kiro zed opencode copilot_cli antigravity"
# Claude Desktop is macOS-only
if [ "$OS" = "Darwin" ]; then
  ALL_AGENTS="claude_code claude_desktop cursor vscode windsurf codex gemini_cli kiro zed opencode copilot_cli antigravity"
fi

DETECTED=""
DETECTED_COUNT=0
for _id in $ALL_AGENTS; do
  if [ -z "$DETECTED" ]; then
    DETECTED="$_id"
  else
    DETECTED="$DETECTED $_id"
  fi
  DETECTED_COUNT=$((DETECTED_COUNT + 1))
done

# Resolve config directories for agents that need them
_cursor_dir="$HOME/.cursor"
if [ ! -d "$_cursor_dir" ] && [ -d "$HOME/.config/cursor" ]; then _cursor_dir="$HOME/.config/cursor"; fi
if [ "$OS" = "Darwin" ]; then _vscode_dir="$HOME/Library/Application Support/Code/User"; else _vscode_dir="$HOME/.config/Code/User"; fi
_windsurf_dir="$HOME/.codeium/windsurf"
if [ ! -d "$_windsurf_dir" ] && [ -d "$HOME/.config/windsurf" ]; then _windsurf_dir="$HOME/.config/windsurf"; fi

# --- Interactive agent selector ---

STEP3="Select agents"
update_steps done done active

{
  # Store agents in numbered variables for indexing
  _sel_n=0
  for _id in $DETECTED; do
    _sel_n=$((_sel_n + 1))
    eval "_sel_id_${_sel_n}=\$_id"
    eval "_sel_on_${_sel_n}=0"
    eval "_sel_label_${_sel_n}=\"\$(agent_label \$_id)\""
  done
  _sel_cur=1
  _sel_total=$_sel_n

  # Total lines used by selector (agents + blank + hint)
  _sel_lines=$((_sel_total + 2))

  # Render the selector to /dev/tty, nested under the step line
  _sel_render() {
    _sel_count=0
    _si=1
    while [ "$_si" -le "$_sel_total" ]; do
      eval "_v=\$_sel_on_${_si}"
      [ "$_v" = "1" ] && _sel_count=$((_sel_count + 1))
      _si=$((_si + 1))
    done
    # Move up to top of selector
    printf "\033[${_sel_lines}A" > /dev/tty
    _si=1
    while [ "$_si" -le "$_sel_total" ]; do
      eval "_lbl=\$_sel_label_${_si}"
      eval "_on=\$_sel_on_${_si}"
      if [ "$_on" = "1" ]; then
        _check="${GREEN}●${RESET}"
      else
        _check="${DIM}○${RESET}"
      fi
      if [ "$_si" = "$_sel_cur" ]; then
        printf "\r   › ${_check} ${BOLD}%s${RESET}\033[K\n" "$_lbl" > /dev/tty
      else
        printf "\r     ${_check} %s\033[K\n" "$_lbl" > /dev/tty
      fi
      _si=$((_si + 1))
    done
    printf "\n" > /dev/tty
    if [ "$_sel_count" = "0" ]; then
      printf "\r${GRAY}\033[3m↑↓ move · space select · enter confirm · esc cancel\033[23m${RESET}\033[K\n" > /dev/tty
    else
      printf "\r${GRAY}\033[3m↑↓ move · space select · enter confirm · esc cancel — %s selected\033[23m${RESET}\033[K\n" "$_sel_count" > /dev/tty
    fi
  }

  # Print blank lines to make room, then render
  _ri=0
  while [ "$_ri" -lt "$_sel_lines" ]; do
    printf "\n" > /dev/tty
    _ri=$((_ri + 1))
  done
  printf "$HIDE_CURSOR" > /dev/tty

  _sel_render

  # Save terminal settings and switch to raw mode
  _old_stty=$(stty -g < /dev/tty)
  _sel_cleanup() {
    stty "$_old_stty" < /dev/tty 2>/dev/null
    printf "$SHOW_CURSOR" > /dev/tty
  }
  trap '_sel_cleanup' INT TERM

  _sel_done=false
  while [ "$_sel_done" = false ]; do
    # Read a single key in raw mode
    stty raw -echo < /dev/tty
    _key=$(dd bs=1 count=1 2>/dev/null < /dev/tty)
    stty "$_old_stty" < /dev/tty

    case "$_key" in
      # Escape sequence — read next byte with timeout (arrow keys) or bare esc to cancel
      "$(printf '\033')")
        stty raw -echo min 0 time 1 < /dev/tty
        _k2=$(dd bs=1 count=1 2>/dev/null < /dev/tty)
        stty "$_old_stty" < /dev/tty
        if [ "$_k2" = "[" ]; then
          stty raw -echo < /dev/tty
          _k3=$(dd bs=1 count=1 2>/dev/null < /dev/tty)
          stty "$_old_stty" < /dev/tty
          case "$_k3" in
            A) # Up
              if [ "$_sel_cur" -gt 1 ]; then
                _sel_cur=$((_sel_cur - 1))
              else
                _sel_cur=$_sel_total
              fi
              ;;
            B) # Down
              if [ "$_sel_cur" -lt "$_sel_total" ]; then
                _sel_cur=$((_sel_cur + 1))
              else
                _sel_cur=1
              fi
              ;;
          esac
        else
          # Bare escape — cancel
          _sel_cleanup
          printf "\nCancelled.\n" > /dev/tty
          exit 0
        fi
        ;;
      " ") # Space — toggle
        eval "_cur_on=\$_sel_on_${_sel_cur}"
        if [ "$_cur_on" = "1" ]; then
          eval "_sel_on_${_sel_cur}=0"
        else
          eval "_sel_on_${_sel_cur}=1"
        fi
        ;;
      "$(printf '\r')"|"") # Enter
        _any=false
        _ei=1
        while [ "$_ei" -le "$_sel_total" ]; do
          eval "_v=\$_sel_on_${_ei}"
          [ "$_v" = "1" ] && _any=true
          _ei=$((_ei + 1))
        done
        if [ "$_any" = true ]; then
          _sel_done=true
        fi
        ;;
    esac

    [ "$_sel_done" = false ] && _sel_render
  done

  _sel_cleanup

  # Clear the selector UI
  printf "\033[${_sel_lines}A" > /dev/tty
  _ci=0
  while [ "$_ci" -lt "$_sel_lines" ]; do
    printf "\r\033[K\n" > /dev/tty
    _ci=$((_ci + 1))
  done
  printf "\033[${_sel_lines}A" > /dev/tty

  # Rebuild DETECTED from selection
  DETECTED=""
  DETECTED_NAMES=""
  DETECTED_COUNT=0
  _ri=1
  while [ "$_ri" -le "$_sel_total" ]; do
    eval "_on=\$_sel_on_${_ri}"
    if [ "$_on" = "1" ]; then
      eval "_id=\$_sel_id_${_ri}"
      _lbl=$(agent_label "$_id")
      if [ -z "$DETECTED" ]; then
        DETECTED="$_id"
        DETECTED_NAMES="$_lbl"
      else
        DETECTED="$DETECTED $_id"
        DETECTED_NAMES="$DETECTED_NAMES, $_lbl"
      fi
      DETECTED_COUNT=$((DETECTED_COUNT + 1))
    fi
    _ri=$((_ri + 1))
  done

  STEP3="Configure MCP ($DETECTED_COUNT agents)"
  update_steps done done active
}

# --- Configuration helpers ---

# Configure JSON-based agents using python3
# Args: config_file server_property [format]
# Formats: standard, http, claude_desktop, opencode, antigravity, gemini_cli, zed
configure_json_agent() {
  _cja_file="$1"
  _cja_prop="$2"
  _cja_fmt="${3:-standard}"

  SOURCED_CJA_FILE="$_cja_file" \
  SOURCED_CJA_PROP="$_cja_prop" \
  SOURCED_CJA_KEY="$api_key" \
  SOURCED_CJA_URL="$MCP_URL" \
  SOURCED_CJA_FMT="$_cja_fmt" \
  python3 << 'PYEOF'
import json, os, re, sys

config_file = os.environ['SOURCED_CJA_FILE']
prop = os.environ['SOURCED_CJA_PROP']
api_key = os.environ['SOURCED_CJA_KEY']
mcp_url = os.environ['SOURCED_CJA_URL']
fmt = os.environ['SOURCED_CJA_FMT']

if fmt == 'http':
    # Claude Code, VS Code, Copilot CLI
    server_config = {
        'type': 'http',
        'url': mcp_url,
        'headers': {'Authorization': f'Bearer {api_key}'}
    }
elif fmt == 'claude_desktop':
    # Claude Desktop — no native remote support, uses npx mcp-remote bridge
    server_config = {
        'command': 'npx',
        'args': ['mcp-remote', mcp_url, '--header', f'Authorization: Bearer {api_key}']
    }
elif fmt == 'opencode':
    server_config = {
        'type': 'remote',
        'url': mcp_url,
        'enabled': True,
        'oauth': False,
        'headers': {'Authorization': f'Bearer {api_key}'}
    }
elif fmt == 'antigravity':
    server_config = {
        'serverUrl': mcp_url,
        'headers': {'Authorization': f'Bearer {api_key}'}
    }
elif fmt == 'gemini_cli':
    server_config = {
        'httpUrl': mcp_url,
        'headers': {'Authorization': f'Bearer {api_key}'},
        'trust': True
    }
elif fmt == 'zed':
    server_config = {
        'enabled': True,
        'url': mcp_url,
        'headers': {'Authorization': f'Bearer {api_key}'}
    }
else:
    # standard — Cursor, Windsurf, Kiro
    server_config = {
        'url': mcp_url,
        'headers': {'Authorization': f'Bearer {api_key}'}
    }

def strip_jsonc(text):
    """Strip // and /* */ comments and trailing commas from JSONC, preserving strings."""
    result = []
    i = 0
    in_string = False
    while i < len(text):
        c = text[i]
        if in_string:
            result.append(c)
            if c == '\\' and i + 1 < len(text):
                i += 1
                result.append(text[i])
            elif c == '"':
                in_string = False
        elif c == '"':
            in_string = True
            result.append(c)
        elif c == '/' and i + 1 < len(text) and text[i+1] == '/':
            while i < len(text) and text[i] != '\n':
                i += 1
            continue
        elif c == '/' and i + 1 < len(text) and text[i+1] == '*':
            i += 2
            while i + 1 < len(text) and not (text[i] == '*' and text[i+1] == '/'):
                i += 1
            i += 2
            continue
        else:
            result.append(c)
        i += 1
    text = ''.join(result)
    text = re.sub(r',\s*([}\]])', r'\1', text)
    return text

config = {}
if os.path.exists(config_file):
    with open(config_file) as f:
        content = f.read().strip()
    if content:
        try:
            config = json.loads(content)
        except json.JSONDecodeError:
            try:
                config = json.loads(strip_jsonc(content))
            except json.JSONDecodeError:
                # Cannot parse existing file — refuse to overwrite
                sys.exit(1)

if not isinstance(config, dict):
    config = {}

# Navigate dotted property paths (e.g. "amp.mcpServers")
parts = prop.split('.')
target = config
for part in parts[:-1]:
    if part not in target or not isinstance(target[part], dict):
        target[part] = {}
    target = target[part]
if parts[-1] not in target:
    target[parts[-1]] = {}

target[parts[-1]]['sourced'] = server_config
target[parts[-1]].pop('sourced.dev', None)

config_dir = os.path.dirname(config_file)
if config_dir:
    os.makedirs(config_dir, exist_ok=True)

with open(config_file, 'w') as f:
    json.dump(config, f, indent=2)
    f.write('\n')
PYEOF
}

# Configure Codex (TOML)
configure_codex() {
  mkdir -p "$HOME/.codex"
  SOURCED_CODEX_FILE="$HOME/.codex/config.toml" \
  SOURCED_CODEX_KEY="$api_key" \
  SOURCED_CODEX_URL="$MCP_URL" \
  python3 << 'PYEOF'
import os, re, sys

config_file = os.environ['SOURCED_CODEX_FILE']
api_key = os.environ['SOURCED_CODEX_KEY']
mcp_url = os.environ['SOURCED_CODEX_URL']

content = ''
if os.path.exists(config_file):
    with open(config_file) as f:
        content = f.read()

    # Validate existing TOML if parser is available
    try:
        import tomllib
        tomllib.loads(content)
    except ImportError:
        pass
    except Exception:
        # Invalid TOML — refuse to overwrite
        sys.exit(1)

# Remove existing [mcp_servers."sourced.dev"] or [mcp_servers.sourced] section
content = re.sub(
    r'\n*\[mcp_servers\.(?:"sourced\.dev"|sourced)\]\n(?:(?!\[)[^\n]*\n?)*',
    '',
    content
)
content = content.rstrip()

# Build the new section
new_section = (
    '[mcp_servers.sourced]\n'
    'url = "' + mcp_url + '"\n'
    'http_headers = { Authorization = "Bearer ' + api_key + '" }\n'
)

content = (content + '\n\n' + new_section) if content else new_section

# Validate the result parses correctly
try:
    import tomllib
    tomllib.loads(content)
except ImportError:
    pass
except Exception:
    sys.exit(1)

os.makedirs(os.path.dirname(config_file), exist_ok=True)
with open(config_file, 'w') as f:
    f.write(content)
PYEOF
}

# Helper: run a configure function and count successes
try_configure() {
  if "$@"; then
    configured=$((configured + 1))
  fi
}

# --- Configure each detected agent ---

configured=0

for agent in $DETECTED; do
  case $agent in
    claude_code)
      try_configure configure_json_agent "$HOME/.claude.json" "mcpServers" "http" ;;
    claude_desktop)
      try_configure configure_json_agent \
        "$HOME/Library/Application Support/Claude/claude_desktop_config.json" "mcpServers" "claude_desktop" ;;
    cursor)
      try_configure configure_json_agent "$_cursor_dir/mcp.json" "mcpServers" ;;
    vscode)
      try_configure configure_json_agent "$_vscode_dir/mcp.json" "servers" "http" ;;
    windsurf)
      try_configure configure_json_agent "$_windsurf_dir/mcp_config.json" "mcpServers" ;;
    codex)
      try_configure configure_codex ;;
    gemini_cli)
      try_configure configure_json_agent "$HOME/.gemini/settings.json" "mcpServers" "gemini_cli" ;;
    kiro)
      try_configure configure_json_agent "$HOME/.kiro/settings/mcp.json" "mcpServers" ;;
    zed)
      try_configure configure_json_agent \
        "$HOME/.config/zed/settings.json" "context_servers" "zed" ;;
    opencode)
      try_configure configure_json_agent "$HOME/.config/opencode/opencode.json" "mcp" "opencode" ;;
    copilot_cli)
      try_configure configure_json_agent "$HOME/.copilot/mcp-config.json" "mcpServers" "http" ;;
    antigravity)
      try_configure configure_json_agent \
        "$HOME/.gemini/antigravity/mcp_config.json" "mcpServers" "antigravity" ;;
  esac
done

if [ "$configured" -gt 0 ]; then
  if [ "$configured" -eq 1 ]; then
    STEP3="Configure MCP (1 agent)"
  else
    STEP3="Configure MCP ($configured agents)"
  fi
  update_steps done done done
else
  STEP3="Configure MCP"
  update_steps done done fail
  printf "\n${RED}No coding agents could be configured.${RESET}\n\n"
  exit 1
fi

# --- Done ---

printf "\n"
printf "${BOLD_GREEN}Setup complete!${RESET}\n"
printf "Restart your coding agents to start using sourced.dev\n"
printf "\n"
