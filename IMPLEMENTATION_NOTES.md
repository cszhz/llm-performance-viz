# Project-Based Architecture Implementation Notes

## Overview
This document describes the implementation of project-based data organization in the LLM Performance Visualization tool.

## Architecture Changes

### Directory Structure
**Before:**
```
archive_results/
├── vllm-v0.9.2--g6e.4xlarge--Qwen3-30B-A3B-FP8/
│   ├── sysinfo.json
│   └── test_*.json
└── sglang-v0.4.9--p5en.48xlarge--Qwen3-235B-A22B-FP8/
    └── test_*.json
```

**After:**
```
archive_results/
├── default/                    # Default project
│   ├── vllm-v0.9.2--g6e.4xlarge--Qwen3-30B-A3B-FP8/
│   │   └── test_*.json
│   └── sglang-v0.4.9--p5en.48xlarge--Qwen3-235B-A22B-FP8/
│       └── test_*.json
├── project-a/                  # Custom project
│   └── ...
└── project-b/
    └── ...
```

## Backend Changes (Python)

### 1. `ResultsDataProvider` Class (`viz_server.py`)
**New methods:**
- `_ensure_default_project()` - Auto-migrate old structure to project-based
- `get_available_projects()` - List all projects
- `load_all_results(project_name)` - Load data for specific project

**Modified methods:**
- `__init__()` - Initialize with project support
- `load_all_results()` - Changed signature to accept `project_name` parameter

**New attributes:**
- `current_project` - Track currently loaded project

### 2. New API Endpoints (`viz_server.py`)
```
GET /api/projects
  - Returns list of available projects
  - Response: {"projects": ["default", "project-a", ...]}

Modified:
GET /api/tree-structure?project=<name>&reload=<bool>
GET /api/combinations?project=<name>
GET /api/parameters?project=<name>&...
GET /api/performance-data?project=<name>&...
POST /api/comparison-data (body includes project field)
POST /api/export-csv (body includes project field)
```

### 3. Data Model Changes
```python
class ComparisonRequest(BaseModel):
    combinations: List[Dict]
    project: Optional[str] = "default"  # NEW
```

### 4. Migration Support
- Automatic detection of old structure
- Auto-migration to `default` project on first run
- `migrate_to_project_structure.py` - Manual migration tool

## Frontend Changes (JavaScript/HTML)

### 1. UI Components (`index.html`)
**New Project Selector:**
```html
<div class="tree-container">
    <div class="tree-title">Project Selection</div>
    <div class="slider-group">
        <label for="project-dropdown">Project:</label>
        <select id="project-dropdown" class="select-input"
                onchange="switchProject(this.value)">
            <option value="">Loading projects...</option>
        </select>
    </div>
</div>
```

### 2. State Management (`config.js`)
```javascript
export const STATE = {
    // ... existing state ...
    currentProject: 'default',
    availableProjects: ['default']
};
```

### 3. Project Loading (`main.js`)
**New functions:**
- `loadProjectList()` - Fetch available projects from backend
- `setupProjectSelector()` - Setup change event listener
- `switchProject(projectName)` - Switch to different project

**Modifications:**
- `init()` - Now loads projects before tree structure
- Added localStorage for project persistence

### 4. API Calls
**Modified in multiple files:**
- `tree.js` - Added `project` query parameter
- `charts.js` - Added `project` to POST body
- `tokens.js` - Added `project` query parameter
- `main.js` - Added `project` to export CSV

## Backward Compatibility

### Auto-Migration
When the server starts:
1. Checks if old structure exists at root of `archive_results/`
2. If found, creates `default` project automatically
3. No data is lost in the process

### Fallbacks
- Default project is always `default`
- If no projects exist, system creates an empty `default`
- UI gracefully handles empty project list

## Testing

### Unit Tests
Run `test_project_api.py` to verify:
```bash
python3 test_project_api.py
```

Tests verify:
1. Project detection
2. Data loading per project
3. Data isolation between projects
4. Combination retrieval

### Manual Testing
1. Start server: `uv run start_viz_server.py`
2. Access UI: `http://localhost:8000`
3. Check project dropdown in sidebar
4. Switch projects and verify data changes

## Migration Path for Existing Users

### Option 1: Automatic (Recommended)
- Just start the server as normal
- Old data is automatically migrated to `default` project

### Option 2: Manual
```bash
python3 migrate_to_project_structure.py
```

The migration script:
- Detects old structure
- Creates backup before migration
- Moves directories to appropriate projects
- Provides interactive confirmation

## Configuration

### Start with Custom Default Project
```bash
uv run start_viz_server.py --project production
```

### Use Custom Results Directory
```bash
uv run start_viz_server.py --results-dir /path/to/archive_results
```

## Database Schema (Logical)

All data remains JSON-based, with logical project-based organization:

```
Project
├── Runtime
│   ├── Instance Type
│   │   └── Model
│   │       └── Test Results
│   │           ├── Test Case 1
│   │           ├── Test Case 2
│   │           └── ...
│   └── ...
├── ...
└── Default
    └── ...
```

## File Modifications Summary

| File | Type | Changes |
|------|------|---------|
| `src/llm_test_tool/viz_server.py` | Backend | 300+ lines modified |
| `src/llm_test_tool/static/js/main.js` | Frontend | 80+ lines added |
| `src/llm_test_tool/static/js/config.js` | Frontend | 2 lines added |
| `src/llm_test_tool/static/js/tree.js` | Frontend | 5 lines modified |
| `src/llm_test_tool/static/js/charts.js` | Frontend | 20 lines modified |
| `src/llm_test_tool/static/js/tokens.js` | Frontend | 5 lines modified |
| `src/llm_test_tool/index.html` | Frontend | 10 lines added |
| `start_viz_server.py` | Config | 10 lines added |
| `migrate_to_project_structure.py` | NEW | Migration utility |

## Performance Considerations

- Project loading is on-demand (lazy loading)
- DataFrame is cleared when switching projects
- No performance degradation with multiple projects
- Memory usage scales with active project size, not total size

## Future Enhancements

1. **Project Management UI:**
   - Create/delete projects from web UI
   - Rename projects
   - Share projects

2. **Project Metadata:**
   - Project description
   - Creation date
   - Owner information
   - Tags/categories

3. **Access Control:**
   - Project-level permissions
   - User-specific projects
   - Project collaboration

4. **Data Operations:**
   - Export/import projects
   - Merge projects
   - Archive old projects

## Known Limitations

1. Project names must be valid filesystem directory names
2. No spaces or special characters in project names recommended
3. Project switching clears all chart selections
4. Analytics data is not project-separated (global)

## Troubleshooting

### Old data not appearing
- Run migration: `python3 migrate_to_project_structure.py`
- Check file permissions in `archive_results/`

### Projects not showing in dropdown
- Verify `archive_results/` directory exists
- Check server console for loading errors
- Try server restart

### Data switching not working
- Clear browser cache/localStorage
- Check browser console for API errors
- Verify all modified files are deployed

## Deployment Checklist

- [ ] All Python files syntax-checked
- [ ] All JavaScript files syntax-checked
- [ ] Test data created for verification
- [ ] Migration script tested
- [ ] Backward compatibility verified
- [ ] HTML templates updated
- [ ] CSS (if needed) updated
- [ ] API documentation updated
- [ ] User documentation updated
