#!/bin/bash

# NyayaGPT Lite - File Structure & Compatibility Verification Script
# Run this to verify all files are present and compatible

echo "🔍 NyayaGPT Lite - Verification Script"
echo "======================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TOTAL=0
PASSED=0
FAILED=0

# Check function
check_file() {
    TOTAL=$((TOTAL + 1))
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗${NC} $1 ${RED}[MISSING]${NC}"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Check directory
check_dir() {
    TOTAL=$((TOTAL + 1))
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $1/"
        PASSED=$((PASSED + 1))
        return 0
    else
        echo -e "${RED}✗${NC} $1/ ${RED}[MISSING]${NC}"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

echo "📋 Checking Root Files..."
check_file "README.md"
check_file "LICENSE"
check_file ".gitignore"
check_file "QUICKSTART.md"
check_file "GITHUB_STRUCTURE.md"
check_file "MASTER_CHECKLIST.md"
check_file "setup.sh"
check_file "setup.bat"
check_file "docker-compose.yml"

echo ""
echo "📚 Checking Documentation..."
check_dir "docs"
check_file "docs/30_SECOND_NARRATIVE.md"
check_file "docs/PITCH_GUIDE.md"
check_file "docs/ENHANCED_PITCH.md"
check_file "docs/DEPLOYMENT.md"
check_file "docs/DATASET_PREPARATION.md"
check_file "docs/FINAL_3_IMPROVEMENTS.md"
check_file "docs/99_POINT_IMPROVEMENTS.md"
check_file "docs/PROJECT_SUMMARY.md"

echo ""
echo "🎨 Checking Frontend Files..."
check_dir "frontend"
check_dir "frontend/src"
check_file "frontend/package.json"
check_file "frontend/vite.config.js"
check_file "frontend/tailwind.config.js"
check_file "frontend/postcss.config.js"
check_file "frontend/index.html"
check_file "frontend/Dockerfile"
check_file "frontend/nginx.conf"
check_file "frontend/src/NyayaGPTLite.jsx"
check_file "frontend/src/main.jsx"
check_file "frontend/src/index.css"

echo ""
echo "⚙️  Checking Backend Files..."
check_dir "backend"
check_dir "backend/tests"
check_file "backend/main.py"
check_file "backend/requirements.txt"
check_file "backend/__init__.py"
check_file "backend/.env.example"
check_file "backend/Dockerfile"
check_file "backend/tests/__init__.py"
check_file "backend/tests/test_api.py"

echo ""
echo "🤖 Checking Training Files..."
check_dir "training"
check_file "training/kaggle_training_notebook.py"

echo ""
echo "📊 Checking Dataset Files..."
check_dir "dataset"
check_file "dataset/sample.json"
check_file "dataset/sample_training_data.json"
check_file "dataset/README.md"

echo ""
echo "📦 Checking Model Directory..."
check_dir "models"
check_file "models/.gitkeep"
check_file "models/README.md"

echo ""
echo "📝 Checking Logs Directory..."
check_dir "logs"
check_file "logs/.gitkeep"

echo ""
echo "🔄 Checking CI/CD..."
check_dir ".github"
check_dir ".github/workflows"
check_file ".github/workflows/ci.yml"

echo ""
echo "======================================"
echo -e "${BLUE}Verification Summary${NC}"
echo "======================================"
echo -e "Total checks: ${BLUE}$TOTAL${NC}"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All files present!${NC}"
    echo ""
    echo "🔍 Checking File Compatibility..."
    echo ""
    
    # Check package.json dependencies
    if [ -f "frontend/package.json" ]; then
        echo -e "${BLUE}Frontend Dependencies:${NC}"
        if grep -q "react" frontend/package.json && grep -q "lucide-react" frontend/package.json; then
            echo -e "${GREEN}✓${NC} React and lucide-react present"
        else
            echo -e "${YELLOW}⚠${NC} Check frontend dependencies"
        fi
    fi
    
    # Check requirements.txt
    if [ -f "backend/requirements.txt" ]; then
        echo -e "${BLUE}Backend Dependencies:${NC}"
        if grep -q "fastapi" backend/requirements.txt && grep -q "pdfplumber" backend/requirements.txt; then
            echo -e "${GREEN}✓${NC} FastAPI and pdfplumber present"
        else
            echo -e "${YELLOW}⚠${NC} Check backend dependencies"
        fi
    fi
    
    # Check main imports
    if [ -f "frontend/src/NyayaGPTLite.jsx" ]; then
        echo -e "${BLUE}Frontend Imports:${NC}"
        if grep -q "from 'lucide-react'" frontend/src/NyayaGPTLite.jsx; then
            echo -e "${GREEN}✓${NC} lucide-react imports correct"
        fi
    fi
    
    if [ -f "backend/main.py" ]; then
        echo -e "${BLUE}Backend Imports:${NC}"
        if grep -q "from fastapi import FastAPI" backend/main.py; then
            echo -e "${GREEN}✓${NC} FastAPI imports correct"
        fi
        if grep -q "import pdfplumber" backend/main.py; then
            echo -e "${GREEN}✓${NC} pdfplumber imports correct"
        fi
    fi
    
    echo ""
    echo -e "${GREEN}🎉 Structure verified! Ready to push to GitHub!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Run: ./setup.sh"
    echo "2. Test the application"
    echo "3. git add . && git commit -m 'Initial commit'"
    echo "4. git push"
    
else
    echo -e "${RED}❌ Some files are missing!${NC}"
    echo ""
    echo "Please ensure all files are present before proceeding."
    exit 1
fi

echo ""
echo "📊 Quick Stats:"
echo "- Documentation: 8 files"
echo "- Frontend: 10 files"
echo "- Backend: 7 files"
echo "- Training: 1 file"
echo "- Dataset: 3 files"
echo "- Config: 5+ files"
echo ""
echo "Total: 40+ files ✅"
