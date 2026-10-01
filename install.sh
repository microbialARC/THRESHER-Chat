#!/usr/bin/env bash
set -e
# Defaults
ENV_NAME="thresher-chat"
# Model default depends on local RAM
case "$(uname -s)" in
    Darwin)
        LOCAL_RAM_GB=$(( $(sysctl -n hw.memsize) / 1024 / 1024 / 1024 ))
        ;;
    Linux)
        LOCAL_RAM_GB=$(( $(grep MemTotal /proc/meminfo | awk '{print $2}') / 1024 / 1024 ))
        ;;
    MINGW*|MSYS*|CYGWIN*)
        LOCAL_RAM_GB=$(( $(wmic OS get TotalVisibleMemorySize /value | grep -o '[0-9]*') / 1024 / 1024 ))
        ;;
    *)
        LOCAL_RAM_GB=8
        ;;
esac

if [ "$LOCAL_RAM_GB" -ge 24 ]; then
    CHAT_MODEL="gemma4:12b"
elif [ "$LOCAL_RAM_GB" -le 24 ]; then
    CHAT_MODEL="gemma4:e4b"
fi
# Embedding model is fixed
EMBED_MODEL="embeddinggemma"
FORCE_REINSTALL=false
INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors generated from https://en.wikipedia.org/wiki/ANSI_escape_code#Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()  { echo -e "${CYAN}[THRESHER-Chat]${NC} $1"; }
ok()    { echo -e "${GREEN}[✓]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
fail()  { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --model|-m)
            CHAT_MODEL="$2"; shift 2 ;;
        --force|-f)
            FORCE_REINSTALL=true; shift ;;
        --help|-h)
            echo "Usage: bash install.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --model, -m NAME   Chat model (default: $CHAT_MODEL) "
            echo "                     based on your local RAM: ${LOCAL_RAM_GB}GB"
            echo "                     gemma4:e4b <=24GB RAM"
            echo "                     gemma4:12b >=24GB RAM"
            echo "  --force, -f        Force reinstall over existing environment"
            echo "  --help, -h         Show this help message"
            exit 0 ;;
        *)
            fail "Unknown option: $1. Use --help for usage." ;;
    esac
done

# Step 1: Check prerequisites
info "Checking prerequisites..."

# Check conda
if ! command -v conda &> /dev/null; then
    fail "conda not found. Install Miniconda: https://docs.conda.io/en/latest/miniconda.html"
fi
ok "conda found"

# Check Ollama / Install Ollama and pull chat model
# Ollama is independent of the conda environment since it runs as a separate server
# so we check it and/or install it before activating the environment
if ! command -v ollama &> /dev/null; then
    info "Ollama not found. Installing..."

    OS="$(uname -s)"
    case "$OS" in
        Darwin)
            if command -v brew &> /dev/null; then
                info "Installing Ollama via Homebrew..."
                brew install --cask ollama
            else
                fail "Ollama not found and Homebrew is not installed.
                Please install Ollama manually:
                Option A: Install Homebrew first (https://brew.sh), then run this script again
                Option B: Download Ollama from https://ollama.com/download"
            fi
            ;;
        Linux)
            info "Installing Ollama for Linux..."
            curl -fsSL https://ollama.com/install.sh | sh
            ;;
        *)
            fail "Unsupported OS: $OS. Install Ollama manually from https://ollama.com"
            ;;
    esac

    # Verify installation succeeded
    if ! command -v ollama &> /dev/null; then
        fail "Ollama installation failed. Install manually from https://ollama.com"
    fi
    ok "Ollama installed"
else
    ok "Ollama found"
fi

# Check Ollama server is reachable
if ! ollama list &> /dev/null; then
    warn "Ollama server not running. Attempting to start..."
    ollama serve &> /dev/null &
    sleep 3
    if ! ollama list &> /dev/null; then
        fail "Could not start Ollama server. Please start it manually: ollama serve"
    fi
    ok "Ollama server started"
else
    ok "Ollama server running"
fi

# Pull models (skip if already downloaded)
INSTALLED_MODELS=$(ollama list 2>/dev/null || echo "")

if echo "$INSTALLED_MODELS" | grep -q "$CHAT_MODEL"; then
    ok "Chat model already installed: ${CHAT_MODEL}"
else
    info "Pulling chat model: ${CHAT_MODEL}"
    ollama pull "$CHAT_MODEL"
    ok "Chat model successfully installed: ${CHAT_MODEL}"
fi

if echo "$INSTALLED_MODELS" | grep -q "$EMBED_MODEL"; then
    ok "Embedding model already installed: ${EMBED_MODEL}"
else
    info "Pulling embedding model: ${EMBED_MODEL}"
    ollama pull "$EMBED_MODEL"
    ok "Embedding model successfully installed: ${EMBED_MODEL}"
fi

# Step 2: Conda environment
info "Setting up conda environment..."

# Initialize conda for this shell
eval "$(conda shell.bash hook)" 2>/dev/null || . "$(conda info --base)/etc/profile.d/conda.sh"
# Check if environment already exists
ENV_EXISTS=false
if conda env list | grep -q "^${ENV_NAME} "; then
    ENV_EXISTS=true
fi

if [ "$ENV_EXISTS" = true ] && [ "$FORCE_REINSTALL" = false ]; then
    fail "Conda environment '${ENV_NAME}' already exists but --force flag not set. Use --force to reinstall."
    fail "Quitting installation to avoid overwriting existing environment."
elif [ "$ENV_EXISTS" = true ] && [ "$FORCE_REINSTALL" = true ]; then
    warn "Force reinstalling in existing conda environment ${ENV_NAME}..."
elif [ "$ENV_EXISTS" = false ] && [ "$FORCE_REINSTALL" = false ]; then
    # normal first install
    info "Creating conda environment '${ENV_NAME}'..."
    conda env create -f "$INSTALL_DIR/thresher-chat.yml"
    ok "Conda environment ${ENV_NAME} created"
elif [ "$ENV_EXISTS" = false ] && [ "$FORCE_REINSTALL" = true ]; then
    # this case is unlikely since if the env doesn't exist, there's nothing to force reinstall over
    warn "Environment ${ENV_NAME} does not exist. Creating new environment..."
    conda env create -f "$INSTALL_DIR/thresher-chat.yml"
    ok "Conda environment ${ENV_NAME} created"
fi

# Activate
conda activate "$ENV_NAME"
CURRENT_ENV=$(basename "$CONDA_PREFIX")
if [ "$CURRENT_ENV" != "$ENV_NAME" ]; then
    fail "Failed to activate environment. Run: conda activate ${ENV_NAME}"
fi
ok "Environment activated"

# Step 3: Install Python package
info "Installing thresher-chat package..."
pip install "$INSTALL_DIR" -q
ok "Python package installed"

# Step 4: Show success message and usage instructions
cols=$(tput cols 2>/dev/null || echo 60)
echo ""
printf '%*s\n' "$cols" '' | tr ' ' '='
echo -e "${GREEN}  THRESHER-Chat installed successfully!${NC}"
printf '%*s\n' "$cols" '' | tr ' ' '='
echo ""
echo -e "  ${CYAN}Quick Start${NC}"
echo ""
echo -e "  ${BOLD}1. Activate the environment${NC}"
echo -e "     conda activate ${ENV_NAME}"
echo ""
echo -e "  ${BOLD}2. Get the THRESHER source code that the assistant will learn from${NC}"
echo -e "     git clone https://github.com/microbialARC/THRESHER.git"
echo ""
echo -e "  ${BOLD}3. Build the local knowledge base${NC}"
echo -e "     thresher-chat ingest --repo THRESHER --db-dir thresher_chat_db"
echo ""
echo -e "  ${BOLD}4. Start the web interface (with the chat model downloaded above)${NC}"
echo -e "     thresher-chat server --db-dir thresher_chat_db --model ${CHAT_MODEL}"
echo ""
echo -e "  Then open ${CYAN}http://127.0.0.1:5000${NC} in your browser."
echo ""
echo -e "  Full guide: ${INSTALL_DIR}/docs/quick_start.md"
echo ""
printf '%*s\n' "$cols" '' | tr ' ' '-'
echo -e "  ${CYAN}Need help?${NC}  thresher-chat --help   |   thresher-chat <command> --help"
printf '%*s\n' "$cols" '' | tr ' ' '='
echo ""