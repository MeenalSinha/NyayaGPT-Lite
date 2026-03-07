# 🚀 NyayaGPT Lite - Quick Start Guide

**Get running in 5 minutes!**

---

## ⚡ Fastest Way to Run

### Option 1: Docker (Recommended)

```bash
# Clone repository
git clone https://github.com/yourusername/nyayagpt-lite.git
cd nyayagpt-lite

# Start everything
docker-compose up --build

# Access:
# - Frontend: http://localhost
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

**That's it!** 🎉

---

## 💻 Option 2: Manual Setup

### Frontend (Terminal 1)

```bash
cd frontend
npm install
npm run dev

# Opens at http://localhost:3000
```

### Backend (Terminal 2)

```bash
cd backend
pip install -r requirements.txt
python main.py

# Runs at http://localhost:8000
```

---

## 🎯 First Steps After Setup

1. **Try the Demo** - Click "Try Sample FIR"
2. **Switch Language** - Toggle English/Hindi
3. **See Explanation** - Notice structured output
4. **Check Features** - All 15 features work!

---

## 🔧 Quick Configuration

### Frontend `.env`:
```
VITE_API_URL=http://localhost:8000
```

### Backend `.env`:
```
API_HOST=0.0.0.0
API_PORT=8000
ENVIRONMENT=development
```

---

## 🐛 Common Issues

**Port in use?** Change port in `vite.config.js` or backend command

**Module not found?** Run `npm install` or `pip install -r requirements.txt`

**Docker issues?** Run `docker-compose down` then rebuild

---

**Full documentation:** See `README.md` and `docs/` folder

**For hackathon presentation:** Read `docs/30_SECOND_NARRATIVE.md`
