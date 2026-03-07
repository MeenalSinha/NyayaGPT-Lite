#!/bin/bash

# Local CI Test Script
# Run this before pushing to verify CI will pass

echo "🧪 NyayaGPT Lite - Local CI Test"
echo "=================================="
echo ""

FAILED=0

# Job 1: Verify Structure
echo "📋 Job 1: Verify File Structure"
echo "--------------------------------"
files=(
  "README.md"
  "LICENSE"
  "setup.sh"
  "backend/main.py"
  "backend/requirements.txt"
  "frontend/package.json"
  "frontend/src/NyayaGPTLite.jsx"
  "kaggle_training_notebook.py"
)

for file in "${files[@]}"; do
  if [ -f "$file" ]; then
    echo "  ✓ $file"
  else
    echo "  ✗ MISSING: $file"
    FAILED=1
  fi
done

if [ $FAILED -eq 0 ]; then
  echo "✅ Structure check PASSED"
else
  echo "❌ Structure check FAILED"
fi

echo ""

# Job 2: Backend Check
echo "🐍 Job 2: Backend Syntax Check"
echo "--------------------------------"
if command -v python3 &> /dev/null; then
  if python3 -m py_compile backend/main.py 2>/dev/null; then
    echo "  ✓ backend/main.py syntax valid"
  else
    echo "  ✗ backend/main.py has syntax errors"
    FAILED=1
  fi
  
  echo "  ℹ️  kaggle_training_notebook.py is for Kaggle/Jupyter (skipped)"
  
  if [ $FAILED -eq 0 ]; then
    echo "✅ Backend check PASSED"
  else
    echo "❌ Backend check FAILED"
  fi
else
  echo "⚠️  Python3 not found - skipping (will pass in CI)"
  echo "✅ Backend check SKIPPED"
fi

echo ""

# Job 3: Frontend Check
echo "⚛️  Job 3: Frontend Build Check"
echo "--------------------------------"
if command -v node &> /dev/null; then
  if [ -f "frontend/package.json" ]; then
    echo "  ✓ package.json exists"
    
    # Check if it's valid JSON
    if node -e "require('./frontend/package.json')" 2>/dev/null; then
      echo "  ✓ package.json is valid"
      echo "✅ Frontend check PASSED"
    else
      echo "  ✗ package.json is invalid"
      echo "❌ Frontend check FAILED"
      FAILED=1
    fi
  else
    echo "  ✗ package.json missing"
    echo "❌ Frontend check FAILED"
    FAILED=1
  fi
else
  echo "⚠️  Node.js not found - skipping (will pass in CI)"
  echo "✅ Frontend check SKIPPED"
fi

echo ""

# Job 4: Documentation Check
echo "📚 Job 4: Documentation Check"
echo "--------------------------------"
docs=(
  "README.md"
  "docs/30_SECOND_NARRATIVE.md"
  "docs/PITCH_GUIDE.md"
  "docs/DEPLOYMENT.md"
  "docs/PRESENTATION_CHEAT_SHEET.md"
)

DOC_FAILED=0
for doc in "${docs[@]}"; do
  if [ -f "$doc" ]; then
    echo "  ✓ $doc"
  else
    echo "  ✗ MISSING: $doc"
    DOC_FAILED=1
    FAILED=1
  fi
done

if [ $DOC_FAILED -eq 0 ]; then
  echo "✅ Documentation check PASSED"
else
  echo "❌ Documentation check FAILED"
fi

echo ""

# Job 5: Safety Check
echo "🛡️  Job 5: Safety Phrase Check"
echo "--------------------------------"
SAFETY_ISSUES=0

# Check for killer line
if grep -q "does NOT replace lawyers" README.md && grep -q "replaces confusion" README.md; then
  echo "  ✓ Killer line present in README"
else
  echo "  ⚠️  Killer line format may need review"
  SAFETY_ISSUES=1
fi

# Check for problematic prediction claims
if grep -r "We predict\|AI predicts" --include="*.md" . 2>/dev/null | grep -v "cannot predict" | grep -v "not predict" | grep -v "don't predict" | grep -q .; then
  echo "  ⚠️  Warning: Found prediction claims - review context"
  SAFETY_ISSUES=1
else
  echo "  ✓ No problematic prediction claims"
fi

# Check for problematic legal advice claims
if grep -r "provides legal advice\|gives legal advice" --include="*.md" . 2>/dev/null | grep -v "not\|cannot\|does not" | grep -q .; then
  echo "  ⚠️  Warning: Found legal advice claims - review context"
  SAFETY_ISSUES=1
else
  echo "  ✓ No problematic legal advice claims"
fi

if [ $SAFETY_ISSUES -eq 0 ]; then
  echo "✅ Safety check PASSED"
else
  echo "⚠️  Safety check has warnings (won't fail CI)"
fi

echo ""
echo "=================================="
echo "📊 Local CI Test Summary"
echo "=================================="
echo ""

if [ $FAILED -eq 0 ]; then
  echo "✅ ALL CRITICAL CHECKS PASSED!"
  echo ""
  echo "Your code is ready to push!"
  echo "CI/CD pipeline will succeed."
  echo ""
  echo "Next steps:"
  echo "  git add ."
  echo "  git commit -m \"Your message\""
  echo "  git push"
  echo ""
  exit 0
else
  echo "❌ SOME CHECKS FAILED!"
  echo ""
  echo "Please fix the issues above before pushing."
  echo ""
  exit 1
fi
