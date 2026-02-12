# Project Version History

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