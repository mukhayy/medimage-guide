# MedGemma User Guide

AI-powered MRI analysis with interactive diagnosis highlighting.

## Quick Start

```bash
npm install
npm run dev
```

Open http://localhost:3000

## Demo Mode

Click **"Load Demo"** → Instant ankle MRI analysis  
Hover diagnosis text → MRI regions highlight

## Upload Your Own MRI

1. Start backend: `cd pipeline && python api.py`
2. Upload image in UI
3. Analysis runs locally

## How It Works

1. **MedSAM2** segments anatomical regions
2. **MedGemma** generates diagnosis
3. **Interactive UI** links text ↔ regions

## Stack

- Next.js 14 + TypeScript
- MedSAM2 (segmentation)
- MedGemma (diagnosis)
- Tailwind CSS

## File Structure

```
/app
  page.tsx              # Main UI
  components/
    MRIViewer.tsx       # Region visualization
    DiagnosisPanel.tsx  # Interactive text
    UploadArea.tsx      # File upload
/pipeline
  complete_pipeline.py  # MedSAM2 + MedGemma
  api.py               # Flask API (local)
/public/demo
  ankle/               # Pre-generated demo
```

## Local Backend (Optional)

```bash
cd pipeline
pip install -r requirements.txt
python api.py
```

Runs on http://localhost:8000

## Features

✅ Real-time region highlighting  
✅ Hover anatomical terms → see regions  
✅ Click regions → scroll to text  
✅ Dark/light theme  
✅ Demo mode (instant)  
✅ Custom upload (local backend)

## Requirements

- Node.js 18+
- Python 3.10+ (for local inference)
- 16GB RAM (for MedGemma)
