#!/bin/bash

# NyayaGPT Lite - Setup Script
echo "🏛️  NyayaGPT Lite - Setup Script"
echo "================================="
echo ""

# Check Docker
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo "✅ Docker found"
    echo ""
    echo "Choose: 1) Docker  2) Manual"
    read -p "Enter choice: " choice
    
    if [ "$choice" = "1" ]; then
        echo "🐳 Starting with Docker..."
        docker-compose up --build -d
        echo "✅ Running at http://localhost"
        exit 0
    fi
fi

# Manual Setup
echo "📦 Manual Setup"

# Backend
echo "🐍 Backend..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
[ ! -f ".env" ] && cp .env.example .env
cd ..

# Frontend
echo "⚛️  Frontend..."
cd frontend
npm install
[ ! -f ".env" ] && echo "VITE_API_URL=http://localhost:8000" > .env
cd ..

echo ""
echo "✅ Done! Run:"
echo "  Terminal 1: cd backend && source venv/bin/activate && python main.py"
echo "  Terminal 2: cd frontend && npm run dev"
