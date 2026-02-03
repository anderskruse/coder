#!/usr/bin/env bash
# Simple installer for KK-code CLI
# Usage: curl -sSL https://your-repo-url/install-kkcode.sh | bash

set -euo pipefail

# ============================================================================
# CONFIGURATION - Update these URLs for your Azure DevOps repo
# ============================================================================
WHEEL_URL="https://dev.azure.com/YOURORG/YOURPROJECT/_apis/git/repositories/YOURREPO/items?path=/dist/mistral_vibe-1.3.3-py3-none-any.whl&download=true"
PACKAGE_NAME="KK-code"

# ============================================================================
# Colors
# ============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NAVY='\033[38;2;0;12;46m'
RESET='\033[0m'

# ============================================================================
# Helper Functions
# ============================================================================
error() { echo -e "${RED}✗${RESET} $1" >&2; exit 1; }
info() { echo -e "${BLUE}→${RESET} $1"; }
success() { echo -e "${GREEN}✓${RESET} $1"; }

# ============================================================================
# Banner
# ============================================================================
show_banner() {
    echo -e "${NAVY}"
    echo "  ██   ██  ██   ██           ████   ████  ████   █████   "
    echo "  ██  ██   ██  ██           █      █    █ █   █  █       "
    echo "  █████    █████   ██████   █      █    █ █   █  ████    "
    echo "  ██  ██   ██  ██           █      █    █ █   █  █       "
    echo "  ██   ██  ██   ██           ████   ████  ████   █████   "
    echo -e "${RESET}"
    echo
}

# ============================================================================
# Install UV
# ============================================================================
install_uv() {
    if command -v uv &> /dev/null; then
        info "uv is already installed: $(uv --version)"
        return 0
    fi

    info "Installing uv..."
    if ! command -v curl &> /dev/null; then
        error "curl is required but not installed. Please install curl first."
    fi

    curl -LsSf https://astral.sh/uv/install.sh | sh || error "Failed to install uv"
    export PATH="$HOME/.local/bin:$PATH"
    success "uv installed successfully"
}

# ============================================================================
# Install KK-code
# ============================================================================
install_kkcode() {
    info "Downloading ${PACKAGE_NAME}..."

    local temp_dir=$(mktemp -d)

    # Download wheel with -J flag to preserve server filename, or use -O for output dir
    cd "$temp_dir"
    if ! curl -L -f -J -O "$WHEEL_URL" 2>/dev/null; then
        error "Failed to download from: ${WHEEL_URL}\nCheck that the URL is correct and accessible."
    fi

    # Find the downloaded wheel file
    local temp_wheel=$(find "$temp_dir" -name "*.whl" -type f | head -n 1)

    # Verify download
    if [[ ! -f "$temp_wheel" ]] || [[ ! -s "$temp_wheel" ]]; then
        error "Downloaded file is empty or missing"
    fi

    info "Installing ${PACKAGE_NAME}..."
    uv tool install "$temp_wheel" --force || error "Installation failed"

    # Cleanup
    rm -rf "$temp_dir"

    success "Installation completed!"
}

# ============================================================================
# Verify Installation
# ============================================================================
verify_installation() {
    # Add to PATH if needed
    if ! command -v kkcode &> /dev/null; then
        if [[ -f "$HOME/.local/bin/kkcode" ]]; then
            export PATH="$HOME/.local/bin:$PATH"
        fi
    fi

    if command -v kkcode &> /dev/null; then
        success "kkcode is ready to use!"
        echo
        echo "Run it with:"
        echo -e "  ${NAVY}kkcode${RESET}"
        echo
        echo "On first run, you'll configure your Scaleway AI credentials."
    else
        echo
        echo -e "${RED}⚠${RESET}  Installation completed but 'kkcode' not found in PATH"
        echo
        echo "Add to your PATH by running:"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
        echo
        echo "Then restart your terminal or run: source ~/.bashrc"
    fi
}

# ============================================================================
# Main
# ============================================================================
main() {
    show_banner

    # Check platform
    case "$(uname -s)" in
        Linux|Darwin) ;;
        *) error "Unsupported platform: $(uname -s). Only Linux and macOS are supported." ;;
    esac

    install_uv
    install_kkcode
    verify_installation

    echo
    success "Setup complete! 🎉"
}

main
