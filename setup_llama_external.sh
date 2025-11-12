#!/bin/bash
# Setup Llama 2 with External Storage
# For users who want to store models on external drives

set -e

echo "🚀 GlassBox - Llama 2 External Storage Setup"
echo "============================================="
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check RAM
echo "💾 Checking your system..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    TOTAL_RAM_GB=$(sysctl hw.memsize | awk '{print int($2/1024/1024/1024)}')
else
    TOTAL_RAM_GB=$(free -g | grep Mem | awk '{print $2}')
fi

echo "   RAM: ${TOTAL_RAM_GB}GB"

if [ "$TOTAL_RAM_GB" -lt 30 ]; then
    echo -e "${RED}⚠️  Warning: You have ${TOTAL_RAM_GB}GB RAM${NC}"
    echo "   Llama 2 7B needs ~30GB (14GB model + 16GB system)"
    echo "   Consider using GPT-2 instead"
    echo ""
    echo "Continue anyway? (y/n)"
    read -r response
    if [[ "$response" != "y" ]]; then
        echo "Setup cancelled. Try: tracer = ActivationTracer('gpt2-medium')"
        exit 1
    fi
else
    echo -e "${GREEN}   ✅ RAM is sufficient (need 30GB, you have ${TOTAL_RAM_GB}GB)${NC}"
fi

echo ""
echo "📂 Setting up external storage..."
echo ""
echo "Where do you want to store the models?"
echo "Examples:"
echo "  /Volumes/ExternalSSD/ai-models"
echo "  /mnt/storage/ai-models"
echo "  /media/user/ExternalDrive/ai-models"
echo ""
echo -n "Enter path (or press Enter for default ~/.cache/huggingface): "
read -r CUSTOM_PATH

if [ -z "$CUSTOM_PATH" ]; then
    echo "Using default location: ~/.cache/huggingface"
    HF_HOME="$HOME/.cache/huggingface"
    TRANSFORMERS_CACHE="$HOME/.cache/huggingface"
else
    # Expand ~ if used
    CUSTOM_PATH="${CUSTOM_PATH/#\~/$HOME}"

    # Check if path exists
    if [ ! -d "$CUSTOM_PATH" ]; then
        echo ""
        echo "Directory doesn't exist. Create it? (y/n)"
        read -r create_response
        if [[ "$create_response" == "y" ]]; then
            mkdir -p "$CUSTOM_PATH"
            echo -e "${GREEN}✅ Created $CUSTOM_PATH${NC}"
        else
            echo "Setup cancelled."
            exit 1
        fi
    fi

    # Check if writable
    if [ ! -w "$CUSTOM_PATH" ]; then
        echo -e "${RED}❌ Error: Cannot write to $CUSTOM_PATH${NC}"
        echo "Try: sudo chown -R $USER:$USER $CUSTOM_PATH"
        exit 1
    fi

    HF_HOME="$CUSTOM_PATH/huggingface"
    TRANSFORMERS_CACHE="$CUSTOM_PATH/cache"

    mkdir -p "$HF_HOME"
    mkdir -p "$TRANSFORMERS_CACHE"

    echo -e "${GREEN}✅ Will store models at: $HF_HOME${NC}"
fi

echo ""
echo "💾 Checking disk space..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    AVAILABLE_GB=$(df -g "$CUSTOM_PATH" 2>/dev/null | tail -1 | awk '{print $4}' || df -g ~ | tail -1 | awk '{print $4}')
else
    AVAILABLE_GB=$(df -BG "$CUSTOM_PATH" 2>/dev/null | tail -1 | awk '{print int($4)}' || df -BG ~ | tail -1 | awk '{print int($4)}')
fi

echo "   Available space: ${AVAILABLE_GB}GB"

if [ "$AVAILABLE_GB" -lt 15 ]; then
    echo -e "${YELLOW}⚠️  Low disk space. Llama 2 needs ~13GB${NC}"
    echo "Continue? (y/n)"
    read -r space_response
    if [[ "$space_response" != "y" ]]; then
        echo "Setup cancelled."
        exit 1
    fi
else
    echo -e "${GREEN}   ✅ Enough disk space${NC}"
fi

echo ""
echo "🔐 Checking HuggingFace login..."

if huggingface-cli whoami > /dev/null 2>&1; then
    USERNAME=$(huggingface-cli whoami | grep username | awk '{print $2}')
    echo -e "${GREEN}✅ Logged in as: $USERNAME${NC}"
else
    echo -e "${YELLOW}⚠️  Not logged in to HuggingFace${NC}"
    echo ""
    echo "You need to:"
    echo "1. Create account: https://huggingface.co/join"
    echo "2. Accept Llama license: https://huggingface.co/meta-llama/Llama-2-7b-hf"
    echo "3. Get token: https://huggingface.co/settings/tokens"
    echo "4. Run: huggingface-cli login"
    echo ""
    echo "Have you completed steps 1-3? (y/n)"
    read -r login_response

    if [[ "$login_response" == "y" ]]; then
        echo "Please run: huggingface-cli login"
        echo "Then run this script again."
        exit 1
    else
        echo "Setup cancelled."
        exit 1
    fi
fi

echo ""
echo "📥 Installing dependencies..."
pip install -q transformers>=4.31.0
pip install -q accelerate>=0.20.0
pip install -q sentencepiece>=0.1.99
pip install -q protobuf>=3.20.0
echo -e "${GREEN}✅ Dependencies installed${NC}"

echo ""
echo "🧪 Testing Llama 2 download/load..."
echo "   Cache location: $HF_HOME"
echo "   This will download ~13GB (one-time only)"
echo ""

# Export environment variables
export HF_HOME="$HF_HOME"
export TRANSFORMERS_CACHE="$TRANSFORMERS_CACHE"

python3 -c "
import sys
import os
sys.path.insert(0, '.')

# Set cache location
os.environ['HF_HOME'] = '$HF_HOME'
os.environ['TRANSFORMERS_CACHE'] = '$TRANSFORMERS_CACHE'

from glassbox import ActivationTracer

print('Loading Llama 2 7B...')
print(f'Cache location: $HF_HOME')
try:
    tracer = ActivationTracer(model_name='meta-llama/Llama-2-7b-hf')
    print(f'\n✅ SUCCESS!')
    print(f'   Model: {tracer.model_name}')
    print(f'   Layers: {tracer.num_layers}')
    print(f'   Heads: {tracer.num_heads}')
    print(f'   Stored at: $HF_HOME')
except Exception as e:
    print(f'\n❌ ERROR: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ Setup Complete!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    echo ""
    echo "Model stored at: $HF_HOME"
    echo ""
    echo "To use this location permanently, add to your ~/.zshrc or ~/.bashrc:"
    echo ""
    echo "  export HF_HOME=\"$HF_HOME\""
    echo "  export TRANSFORMERS_CACHE=\"$TRANSFORMERS_CACHE\""
    echo ""
    echo "Or add to your .env file:"
    echo ""
    echo "  HF_HOME=$HF_HOME"
    echo "  TRANSFORMERS_CACHE=$TRANSFORMERS_CACHE"
    echo ""
    echo "To use now:"
    echo ""
    echo "  export HF_HOME=\"$HF_HOME\""
    echo "  export TRANSFORMERS_CACHE=\"$TRANSFORMERS_CACHE\""
    echo "  python -c \"from glassbox import ActivationTracer; t = ActivationTracer('meta-llama/Llama-2-7b-hf')\""
    echo ""
else
    echo ""
    echo -e "${RED}❌ Setup failed${NC}"
    exit 1
fi
