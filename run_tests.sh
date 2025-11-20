#!/bin/bash
# Test runner script for GlassBox
# Ensures tests run in the correct virtual environment

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🧪 GlassBox Test Runner${NC}\n"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Virtual environment not found${NC}"
    echo "Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}📦 Activating virtual environment...${NC}"
source venv/bin/activate

# Install package in editable mode
echo -e "${YELLOW}📦 Installing GlassBox in editable mode...${NC}"
pip install -e . --quiet

# Run tests
echo -e "\n${YELLOW}🚀 Running tests...${NC}\n"

if [ "$1" == "--coverage" ]; then
    # Run with coverage
    pytest tests/ -v --cov=glassbox --cov-report=html --cov-report=term-missing
elif [ "$1" == "--fast" ]; then
    # Run without collecting slow tests
    pytest tests/ -v -m "not slow"
else
    # Run all tests
    pytest tests/ -v
fi

# Check exit code
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ All tests passed!${NC}"
else
    echo -e "\n${RED}❌ Some tests failed${NC}"
    exit 1
fi
