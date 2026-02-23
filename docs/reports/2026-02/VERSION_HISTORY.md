# Project Version History

## Version 1.1.0 - February 21, 2026

### 🎯 Major Features

#### Frontend Page System Completion
- ✅ Created favorites list page (`pages/favorites/`) with full CRUD functionality
- ✅ Implemented report history page (`pages/report/history/`) with sorting and filtering
- ✅ Added ROI detail page (`pages/report/roi-detail/`) with industry benchmark comparison
- ✅ Created source graph detail page (`pages/report/source-graph/`) with network visualization
- ✅ Implemented raw data page (`pages/report/raw-data/`) with data table and export

#### User Preference System
- ✅ AI platform preference memory - remembers user's last selection
- ✅ Smart default configuration for new users (DeepSeek, 豆包，通义千问，智谱 AI)
- ✅ Auto-save on platform selection change
- ✅ 7-day draft recovery for brand/competitor input

#### Data Management & Security
- ✅ Data backup/restore functionality with local + cloud storage
- ✅ Data encryption toggle with secure storage
- ✅ Auto-backup scheduling support
- ✅ Permission management with role assignment API integration

### 🐛 Bug Fixes

#### Critical Fixes (P0)
- ✅ Fixed WXML compilation error in dashboard (line 206 structure issue)
- ✅ Fixed `ModuleNotFoundError` in NxM execution engine - AI response logging restored
- ✅ Fixed `reportRealtimeAction` compatibility error with safe reporting wrapper
- ✅ Fixed `onLoad` null reference error with defensive programming
- ✅ Fixed ROI detail page WXML method calls - replaced with preprocessed data

#### Important Fixes (P1)
- ✅ Fixed public history detail view navigation
- ✅ Fixed personal history score filter functionality
- ✅ Fixed permission manager role assignment
- ✅ Fixed home page input preservation across sessions
- ✅ Fixed AI platform selection default state

#### Optimization Fixes (P2)
- ✅ Added influence visualization pie chart in ROI detail page
- ✅ Enhanced industry benchmark comparison visualization
- ✅ Integrated WorkflowFindings component into Dashboard
- ✅ Optimized WXML conditional rendering chains

### 🔧 Technical Improvements

#### Backend
- **NxM Engine**: Fixed import paths, restored AI response logging to `ai_responses.jsonl`
- **Monitoring**: Fixed AlertCondition initialization parameter mismatch
- **Security**: Implemented data encryption, input validation, SQL injection protection
- **Performance**: Thread-safe JSONL writing with file locks

#### Frontend
- **Components**: Added ROICard, ImpactGauge, WorkflowFindings reusable components
- **State Management**: Enhanced data persistence with wx.Storage
- **Performance**: Debounced input saving, optimized rendering
- **UX**: Smooth transitions, loading states, error handling

### 📊 Metrics

| Category | Before | After | Improvement |
|----------|--------|-------|-------------|
| Missing Pages | 6 | 0 | ✅ 100% |
| Broken Links | 3 | 0 | ✅ 100% |
| Incomplete Features | 5 | 0 | ✅ 100% |
| Unused Components | 4 | 0 | ✅ 100% |
| Data Flow Bugs | 4 | 0 | ✅ 100% |
| Visualization Gaps | 7 | 0 | ✅ 100% |
| **Total Issues** | **29** | **0** | ✅ **100%** |

### 📁 Files Modified

- **Frontend Pages**: 15+ new/modified pages
- **Components**: 3 new reusable components
- **Utils**: 10+ new utility modules
- **Backend**: 20+ files fixed/optimized
- **Documentation**: 30+ technical reports

### 🚀 Breaking Changes

None - All changes are backward compatible

---

## Version 1.0.0 - February 12, 2026
### Issues Fixed
- Fixed database primary key ID issue where all records had ID=0 instead of auto-incrementing
- Fixed Doubao API 404 errors by correcting endpoint configuration
- Fixed circuit breaker not triggering for timeout failures
- Implemented health check and warm-up mechanism for API adapters
- Optimized frontend polling with dynamic intervals and exponential backoff

### Files Modified
- `wechat_backend/database.py` - Fixed auto-increment ID issue
- `wechat_backend/ai_adapters/doubao_adapter.py` - Fixed API endpoint and circuit breaker integration
- `wechat_backend/circuit_breaker.py` - Enhanced circuit breaker functionality
- `wechat_backend/app.py` - Added warm-up functionality
- `ai_judge_module.py` - Fixed default platform selection
- Multiple test files created for verification

### Key Improvements
- Database now properly generates auto-incrementing IDs
- Circuit breaker properly trips after timeout failures
- Connection pooling implemented for better performance
- Health checks performed on startup
- Dynamic polling intervals reduce unnecessary requests
- All existing functionality preserved with no breaking changes