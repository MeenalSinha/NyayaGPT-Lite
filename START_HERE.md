# 🚀 START HERE - NyayaGPT Lite

## Quick Setup Guide (5 Minutes)

Welcome! This package contains everything you need to run NyayaGPT Lite locally.

---

## ✅ Prerequisites

Before starting, make sure you have:

- **Node.js 18+** - [Download](https://nodejs.org/)
- **Python 3.9+** - [Download](https://www.python.org/downloads/)
- **Git** (optional) - [Download](https://git-scm.com/)

Check versions:
```bash
node --version    # Should be v18 or higher
python --version  # Should be 3.9 or higher
npm --version     # Comes with Node.js
```

---

## 🎯 Three Steps to Run

### Step 1: Extract This ZIP
```bash
# You've already done this if you're reading this file!
cd nyagagpt-lite
```

### Step 2: Run Setup (Automatic!)
```bash
# Mac/Linux
bash setup.sh

# Windows
setup.bat
```

**This will automatically:**
- ✅ Install all Node.js dependencies (~200 MB)
- ✅ Create Python virtual environment (~150 MB)
- ✅ Install all Python packages
- ✅ Set up configuration files
- ✅ Verify everything works

**Takes:** 3-5 minutes

### Step 3: Start the Application

**Terminal 1 - Backend:**
```bash
cd backend
source venv/bin/activate   # Mac/Linux
# OR
venv\Scripts\activate      # Windows

python main.py
```
**Backend runs on:** http://localhost:8000

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```
**Frontend runs on:** http://localhost:5173

**Open browser:** http://localhost:5173

---

## 🎉 That's It!

You're now running NyayaGPT Lite locally!

---

## 📚 Next Steps

### Read These Files:
1. **README.md** - Project overview
2. **QUICKSTART.md** - Detailed setup guide
3. **docs/30_SECOND_NARRATIVE.md** - Pitch script for presentation
4. **LOCAL_DEVELOPMENT_STRUCTURE.md** - Understanding the folders

### For Presentation:
1. **docs/PRESENTATION_CHEAT_SHEET.md** - Print and keep!
2. **docs/SAFETY_AUDIT.md** - Forbidden phrases
3. **docs/VERBAL_PHRASING_GUIDE.md** - Live Q&A

---

## 🆘 Troubleshooting

### Issue: "node_modules not found"
```bash
cd frontend
npm install --legacy-peer-deps
```

### Issue: "venv not found"
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt --break-system-packages
```

### Issue: Setup script fails
Run commands manually:
```bash
# Frontend
cd frontend
npm install --legacy-peer-deps

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt --break-system-packages
cp .env.example .env
```

---

## 📊 What's Included

- ✅ Complete React frontend
- ✅ FastAPI backend
- ✅ Training notebook (Kaggle)
- ✅ Sample data
- ✅ Docker configs
- ✅ CI/CD pipeline
- ✅ Comprehensive documentation
- ✅ Presentation materials

**Total:** 54 source files (~2 MB compressed)

---

## 🎯 Quick Commands

### Verify Structure
```bash
bash verify.sh
```

### Test CI Locally
```bash
bash test-ci.sh
```

### Build for Production
```bash
docker-compose up --build
```

---

## 🏆 Ready to Present?

Check these before demo:
- [ ] Both servers running (ports 8000 & 5173)
- [ ] Read `docs/30_SECOND_NARRATIVE.md`
- [ ] Print `docs/PRESENTATION_CHEAT_SHEET.md`
- [ ] Review `docs/SAFETY_AUDIT.md`

---

## 📞 Need Help?

1. Check **QUICKSTART.md** for detailed instructions
2. Check **LOCAL_DEVELOPMENT_STRUCTURE.md** for folder help
3. Check **docs/CI_TROUBLESHOOTING.md** for CI issues

---

## 🎉 You're All Set!

**Open:** http://localhost:5173
**Upload a legal document** and see the magic happen!

**Good luck with your hackathon!** 🏆
