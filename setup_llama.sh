#!/bin/bash
# Automated Llama 2 Setup Script for GlassBox

set -e  # Exit on error

echo "🚀 GlassBox - Llama 2 Setup Script"
echo "===================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if already logged in
if huggingface-cli whoami > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Already logged in to HuggingFace${NC}"
    USERNAME=$(huggingface-cli whoami | grep username | awk '{print $2}')
    echo "   Username: $USERNAME"
else
    echo -e "${YELLOW}⚠️  Not logged in to HuggingFace${NC}"
    echo ""
    echo "To use Llama 2, you need to:"
    echo "1. Create account: https://huggingface.co/join"
    echo "2. Accept license: https://huggingface.co/meta-llama/Llama-2-7b-hf"
    echo "3. Get token: https://huggingface.co/settings/tokens"
    echo ""
    echo "Have you completed steps 1-3? (y/n)"
    read -r response

    if [[ "$response" != "y" ]]; then
        echo -e "${RED}❌ Please complete the setup steps first${NC}"
        exit 1
    fi

    echo ""
    echo "Please run: huggingface-cli login"
    echo "Then run this script again."
    exit 1
fi

echo ""
echo "📦 Checking dependencies..."

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "   Python: $PYTHON_VERSION"

# Check if in virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}   ⚠️  Not in a virtual environment${NC}"
    echo "   Recommended: source venv/bin/activate"
else
    echo -e "${GREEN}   ✅ Virtual environment active${NC}"
fi

# Install required packages
echo ""
echo "📥 Installing required packages..."
pip install -q transformers>=4.31.0
pip install -q accelerate>=0.20.0
pip install -q sentencepiece>=0.1.99
pip install -q protobuf>=3.20.0

echo -e "${GREEN}✅ Dependencies installed${NC}"

# Test loading Llama 2
echo ""
echo "🧪 Testing Llama 2 7B download/load..."
echo "   This will download ~13GB on first run (one-time only)"
echo "   Subsequent loads will be instant from cache"
echo ""

python3 -c "
import sys
sys.path.insert(0, '.')
from glassbox import ActivationTracer

print('Loading Llama 2 7B...')
try:
    tracer = ActivationTracer(model_name='meta-llama/Llama-2-7b-hf')
    print(f'\n✅ SUCCESS! Llama 2 loaded.')
    print(f'   Model: {tracer.model_name}')
    print(f'   Layers: {tracer.num_layers}')
    print(f'   Heads: {tracer.num_heads}')
except Exception as e:
    print(f'\n❌ ERROR: {e}')
    print('\nCommon issues:')
    print('1. License not accepted: https://huggingface.co/meta-llama/Llama-2-7b-hf')
    print('2. Not logged in: run huggingface-cli login')
    print('3. Not enough RAM: need 16GB+ system + 14GB for model')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    echo -e "${GREEN}✅ Llama 2 Setup Complete!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Test with Python:"
    echo "   python -c \"from glassbox import ActivationTracer; t = ActivationTracer('meta-llama/Llama-2-7b-hf')\""
    echo ""
    echo "2. Use in your code:"
    echo "   tracer = ActivationTracer(model_name='meta-llama/Llama-2-7b-hf')"
    echo ""
    echo "3. Configure for API/Dashboard:"
    echo "   export GLASSBOX_MODEL=meta-llama/Llama-2-7b-hf"
    echo "   uvicorn api.server:app --reload"
    echo ""
    echo "4. Read the guide:"
    echo "   cat LLAMA_SETUP_GUIDE.md"
    echo ""
else
    echo ""
    echo -e "${RED}❌ Setup failed - see errors above${NC}"
    exit 1
fi
