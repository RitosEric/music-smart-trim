# Quick Start Guide

## Fixed Issues
✅ Removed `NoFreshStrategiesError` import (not in main branch)
✅ API now imports successfully

## How to Run the Application

### Prerequisites
```bash
# Install backend dependencies
pip install -r requirements.txt
pip install -r api/requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### Option 1: Run from Project Root (Recommended)

**Terminal 1 - Flask API:**
```bash
cd /Users/ericli/Documents/Projects/music-smart-trim
python -m api.app
```

**Terminal 2 - WebSocket Server:**
```bash
cd /Users/ericli/Documents/Projects/music-smart-trim
python -m api.websocket
```

**Terminal 3 - React Frontend:**
```bash
cd /Users/ericli/Documents/Projects/music-smart-trim/frontend
npm start
```

### Option 2: Test with CLI Only
```bash
python -m src.cli --input "/Users/ericli/Downloads/ex/One Direction - What Makes You Beautiful.mp3" --target 120
```

## Accessing the Application

Once all three servers are running:
- Frontend: http://localhost:3000
- API: http://localhost:5002
- WebSocket: ws://localhost:8765

## Troubleshooting

### Import Errors
Always run from project root (`/Users/ericli/Documents/Projects/music-smart-trim`), not from subdirectories.

### Port Already in Use
```bash
# Kill processes on specific ports
lsof -ti:5002 | xargs kill  # Flask API
lsof -ti:8765 | xargs kill  # WebSocket
lsof -ti:3000 | xargs kill  # React dev server
```

### Module Not Found
Make sure you're in the correct directory and have installed all dependencies.

## What's Working Now

✅ API imports work correctly
✅ Compatible with main branch engine
✅ No experimental changes to core engine
✅ Ready to process audio files

## Next Steps

1. Start all three servers
2. Upload audio file through web UI
3. Test processing with main branch engine
4. Begin iterative improvements if needed
