#!/bin/sh
set -e

# sourced.dev MCP server installer
# Usage: curl -sL sourced.dev/install | sh

GITHUB_CLIENT_ID="Ov23licLaZ5SAKAW8vZO"
API_BASE="${API_BASE:-https://api.sourced.dev}"
PORT=8123
REDIRECT_URI="http://localhost:${PORT}/callback"

# --- Colors (only when outputting to a terminal) ---

BOLD=''
DIM=''
GREEN=''
BOLD_GREEN=''
RED=''
RESET=''

if [ -t 1 ]; then
  BOLD='\033[1m'
  DIM='\033[2m'
  GREEN='\033[0;32m'
  BOLD_GREEN='\033[1;32m'
  RED='\033[0;31m'
  RESET='\033[0m'
fi

# --- Check dependencies ---

if ! command -v curl > /dev/null 2>&1; then
  printf "${RED}error${RESET}: curl is required. Install it and try again.\n"
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
printf "${DIM}Give your coding agent access to dependency source code.${RESET}\n"
printf "\n"
printf "${DIM}This will:${RESET}\n"
printf "  Authorise sourced.dev to read public GitHub repos\n"
printf "  Create your sourced.dev API key\n"
printf "  Configure MCP\n"
printf "\n"
printf "${DIM}Continue?${RESET} [Y/n] "
read -r confirm
if [ "$confirm" = "n" ] || [ "$confirm" = "N" ]; then
  printf "Cancelled.\n"
  exit 0
fi

# --- Execute steps (update lines in-place) ---

# Move cursor up to "This will:" and clear it, then down to step 1
# Continue(-1), blank(-2), MCP(-3), API key(-4), GitHub(-5), This will:(-6)
printf '\033[6A\033[2K\033[B'

# --- Step 1: Authorise sourced.dev to read public GitHub repos ---

printf "\033[2K\r  ${DIM}Authorizing with GitHub...${RESET}"

auth_url="https://github.com/login/oauth/authorize?client_id=${GITHUB_CLIENT_ID}&redirect_uri=${REDIRECT_URI}&scope=read:user+user:email"

if command -v open > /dev/null 2>&1; then
  open "$auth_url"
elif command -v xdg-open > /dev/null 2>&1; then
  xdg-open "$auth_url"
else
  printf '\033[4B\r\033[2K  Open: %s\033[4A' "$auth_url"
fi

code=$(python3 -c "
import http.server, urllib.parse

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(b'<html><body style=\"font-family:system-ui;display:flex;justify-content:center;align-items:center;height:100vh;margin:0\"><div style=\"text-align:center\"><h1>Authenticated!</h1><p>You can close this tab.</p></div></body></html>')
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        if 'code' in params:
            print(params['code'][0], flush=True)
            raise KeyboardInterrupt

    def log_message(self, *args):
        pass

try:
    http.server.HTTPServer(('', ${PORT}), Handler).serve_forever()
except KeyboardInterrupt:
    pass
")

if [ -z "$code" ]; then
  printf "\033[2K\r  ${RED}✗${RESET} Authorise sourced.dev to read public GitHub repos\n"
  printf '\033[J'
  printf "${RED}Failed to get authorization code from GitHub.${RESET}\n\n"
  exit 1
fi

printf "\033[2K\r  ${GREEN}✓${RESET} Authorise sourced.dev to read public GitHub repos\n"

# --- Step 2: Create API key ---

printf "\033[2K\r  ${DIM}Creating your API key...${RESET}"

auth_response=$(curl -s -X POST "${API_BASE}/api/v1/auth/token" \
  -H "Content-Type: application/json" \
  -d "{\"code\": \"${code}\", \"redirect_uri\": \"${REDIRECT_URI}\"}")

api_key=$(echo "$auth_response" | grep -o '"api_key":"[^"]*"' | cut -d'"' -f4)

if [ -z "$api_key" ]; then
  printf "\033[2K\r  ${RED}✗${RESET} Create your sourced.dev API key\n"
  printf '\033[J'
  printf "${RED}Failed to create API key.${RESET}\n"
  printf "${DIM}%s${RESET}\n\n" "$auth_response"
  exit 1
fi

printf "\033[2K\r  ${GREEN}✓${RESET} Create your sourced.dev API key\n"

# --- Step 3: Configure MCP server ---

printf "\033[2K\r  ${DIM}Configuring MCP tool...${RESET}"

claude_config_dir="$HOME/.claude"
claude_config_file="$claude_config_dir/claude_desktop_config.json"

mkdir -p "$claude_config_dir"

if [ -f "$claude_config_file" ]; then
  if echo "$(cat "$claude_config_file")" | grep -q '"sourced"'; then
    tmp_file=$(mktemp)
    sed "s|\"SOURCED_API_KEY\": *\"[^\"]*\"|\"SOURCED_API_KEY\": \"${api_key}\"|" "$claude_config_file" > "$tmp_file"
    mv "$tmp_file" "$claude_config_file"
  else
    tmp_file=$(mktemp)
    sed "s|\"mcpServers\": *{|\"mcpServers\": { \"sourced\": { \"command\": \"npx\", \"args\": [\"-y\", \"@anthropic/sourced-mcp\"], \"env\": { \"SOURCED_API_KEY\": \"${api_key}\" } },|" "$claude_config_file" > "$tmp_file"
    mv "$tmp_file" "$claude_config_file"
  fi
else
  cat > "$claude_config_file" << EOF
{
  "mcpServers": {
    "sourced": {
      "command": "npx",
      "args": ["-y", "@anthropic/sourced-mcp"],
      "env": {
        "SOURCED_API_KEY": "${api_key}"
      }
    }
  }
}
EOF
fi

printf "\033[2K\r  ${GREEN}✓${RESET} Configure MCP\n"

# --- Done ---

printf '\033[J'
printf "\n"
printf "${BOLD_GREEN}Setup complete!${RESET}\n"
printf "Restart your coding agent to start using sourced.\n"
printf "\n"
