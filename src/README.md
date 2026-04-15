# src/ - Core Scripts

## 4 Essential Scripts Only

This folder contains **only the necessary Python scripts** for the analysis pipeline.

---

## 📝 Scripts

### 1. **data_loader.py**
- **Purpose:** Load raw CMS data files (.dta format)
- **Input:** Raw files from `data/raw/`
- **Output:** Pandas DataFrames
- **When to use:** First step in pipeline

### 2. **data_cleaner.py**
- **Purpose:** Clean and validate data
- **Input:** Loaded DataFrames
- **Output:** Cleaned parquet files
- **When to use:** After loading raw data

### 3. **dea.py** ⭐
- **Purpose:** Calculate hospital efficiency scores (DEA-CCR model)
- **Input:** Cleaned data from `data/processed/`
- **Output:** Efficiency scores + hospital stratification
- **Time:** ~5 seconds
- **When to use:** Main analysis - generates key metrics

### 4. **visualizations.py** ⭐
- **Purpose:** Create 10 interactive dashboards
- **Input:** Data with efficiency scores
- **Output:** 10 HTML files in `outputs/figures/dashboards/`
- **Time:** ~5 seconds
- **When to use:** Final step - generates all visualizations

---

## 🚀 Quick Usage

### Run Complete Pipeline
```bash
# Step 1: Load data
python data_loader.py

# Step 2: Clean data
python data_cleaner.py

# Step 3: Generate efficiency scores
python dea.py

# Step 4: Create dashboards
python visualizations.py
```

### Run Only Key Steps
```bash
# Generate efficiency (if data already clean)
python dea.py

# 3. Create Dashboards
python visualizations.py
```

---

## 📊 Data Flow

```
data/raw/
  ↓
data_loader.py
  ↓
Loaded DataFrames
  ↓
data_cleaner.py
  ↓
data/processed/
  ↓
dea.py
  ↓
Efficiency Scores
  ↓
visualizations.py
  ↓
outputs/figures/dashboards/
  (10 HTML dashboards ready to view!)
```

---

## 🗂️ What Was Removed

14 old/redundant scripts were moved to `_archived_code/`:
- Slow DEA versions
- Old visualization scripts
- Rural vs urban analysis
- Individual analysis scripts
- Experimental code

**Only kept:** The 4 essential, fast, production-ready scripts

---

## ⚡ Performance

| Script | Time |
|--------|------|
| data_loader.py | ~30 sec (first time) |
| data_cleaner.py | ~60 sec |
| dea.py | ~5 sec |
| visualizations.py | ~5 sec |
| **Total** | **~2 min** |

---

## 📝 Code Quality

All 4 scripts:
- ✅ Well-documented with docstrings
- ✅ Error handling included
- ✅ Progress indicators
- ✅ Configuration-driven
- ✅ Production-ready

---

## 💡 Tips

1. **First time?** Run all 4 scripts in order
2. **Regenerate dashboards?** Just run `visualizations.py`
3. **New data?** Run `data_loader.py` → `data_cleaner.py` → rest
4. **Stuck?** Check console output for detailed progress messages

---

**Status:** ✅ Minimal, essential, production-ready
