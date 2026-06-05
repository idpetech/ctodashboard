CTO Dashboard — Sample CSV Import Files
=========================================

Location on disk:
  samples/import/

Files:
  1. assignments_clean.csv   — Standard headers (best starting point)
  2. assignments_messy.csv   — Alternate column names, commas in numbers, $ signs
  3. assignments_minimal.csv — No IDs (auto-generated from name), 2 rows only

How to import in the app:
  1. Open http://127.0.0.1:8520/dashboard and log in
  2. Click "Import" in the top toolbar (or sidebar Import button)
  3. Drag a CSV onto the drop zone, or click to browse
  4. Import Mode: "Create New" (default) — safe for first run
  5. Click "Import Assignments"
  6. Watch browser DevTools Console (Network + Console tabs)

Expected API call:
  POST /api/workspaces/<your-workspace>/import/file?mode=create_new

Requires env flags (local):
  ENABLE_CSV_IMPORT=true
  ENABLE_ATTENTION_ENGINE=true  (optional, for CTO Briefing after import)

Re-importing the same file is skipped (idempotent) unless you use force=true
or change Import Mode to Overwrite/Merge.
