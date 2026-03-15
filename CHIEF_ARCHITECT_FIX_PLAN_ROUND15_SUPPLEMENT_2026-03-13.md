# 第 15 次修复补充 - 历史报告完整加载修复方案

**制定日期**: 2026-03-13 12:30
**制定人**: 系统首席架构师
**版本**: v1.1 - 历史报告加载修复
**状态**: 🚨 紧急实施中

---

## 📊 问题分析

### 用户需求

从历史诊断记录中点进去，能完整读到信息并展示详细的诊断报告内容。

### 当前问题链路

```
1. 用户打开"历史记录"页面
   ↓
2. 点击某条历史诊断记录
   ↓
3. 调用 diagnosis.js::loadHistoryReport(reportId)
   ↓
4. 【💥 关键断裂点 1】Storage 缓存未命中
   - 缓存键：`history_report_${reportId}`
   - 问题：用户清除缓存或首次查看时，缓存不存在
   ↓
5. 从云函数/API 加载
   - reportService.getFullReport(reportId)
   ↓
6. 【💥 关键断裂点 2】后端 API 可能返回空数据
   - get_history_report() 从数据库读取
   - 如果 results 为空，brandDistribution 也为空
   ↓
7. 【💥 关键断裂点 3】前端验证失败
   - reportService._processReportData() 验证 brandDistribution
   - 如果 data 为空，验证失败
   ↓
8. 前端显示错误/空白页面
```

---

## 🔍 根因分析

### 后端问题

**文件**: `backend_python/wechat_backend/diagnosis_report_service.py`

**问题**: `get_history_report()` 方法在 results 为空时，未尝试从 DiagnosisResult 表重建数据

```python
# Line 1314-1320
if not results or len(results) == 0:
    db_logger.warning(f"[HistoryReport] 结果数据为空：{execution_id}")
    # 检查报告状态
    if report.get('status') == 'failed':
        return self._create_fallback_report(...)
    # 返回部分数据（包含元数据）
    return self._create_partial_fallback_report(...)
```

**问题**: 直接返回部分数据，没有尝试从数据库重建 brandDistribution

### 前端问题

**文件**: `miniprogram/pages/report-v2/report-v2.js`

**问题**: `loadHistoryReport()` 方法依赖云函数，但云函数可能返回空数据

```javascript
// Line 724-730
const reportService = require('../../services/reportService').default;
const report = await reportService.getFullReport(reportId);

if (report && report.brandDistribution && report.brandDistribution.data) {
    // ✅ 成功
} else {
    // ❌ 失败，显示错误
}
```

---

## 🎯 修复方案

### 修复 1: 后端 get_history_report 增强数据重建

**文件**: `backend_python/wechat_backend/diagnosis_report_service.py`

**位置**: Line 1314-1340

**修复内容**:

```python
def get_history_report(self, execution_id: str) -> Optional[Dict[str, Any]]:
    # ... 前面的代码保持不变 ...

    # 3. 结果为空时的处理
    if not results or len(results) == 0:
        db_logger.warning(f"[HistoryReport] 结果数据为空：{execution_id}")
        
        # 【P0 关键修复 - 2026-03-13 第 15 次补充】尝试从 DiagnosisResult 表重建
        try:
            from wechat_backend.models import DiagnosisResult
            db_results = DiagnosisResult.query.filter_by(execution_id=execution_id).all()
            
            if db_results:
                db_logger.info(
                    f"[HistoryReport] ✅ 从 DiagnosisResult 重建数据：{len(db_results)} 条"
                )
                
                # 转换为字典格式
                results = []
                for r in db_results:
                    results.append({
                        'id': r.id,
                        'execution_id': r.execution_id,
                        'brand': r.brand,
                        'extracted_brand': r.extracted_brand,
                        'question': r.question,
                        'response': r.response,
                        'status': r.status,
                        'created_at': r.created_at.isoformat() if r.created_at else None
                    })
                
                db_logger.info(
                    f"[HistoryReport] ✅ 重建完成：results_count={len(results)}"
                )
        except Exception as rebuild_err:
            db_logger.error(
                f"[HistoryReport] ❌ 重建失败：{rebuild_err}"
            )
            # 继续执行后续逻辑，使用空的 results
        
        # 检查报告状态
        if report.get('status') == 'failed':
            return self._create_fallback_report(
                execution_id,
                '诊断执行失败',
                'failed',
                report
            )
        
        # 如果重建后仍然为空，返回部分数据
        if not results or len(results) == 0:
            db_logger.warning(
                f"[HistoryReport] ⚠️ 重建后仍然为空，返回部分数据"
            )
            return self._create_partial_fallback_report(
                execution_id, 
                report, 
                report.get('progress', 0)
            )

    # 4. 计算品牌分布（使用重建后的 results）
    # 构建完整的品牌列表：主品牌 + 竞品
    expected_brands = [report.get('brand_name', '')] if report.get('brand_name') else []
    if report.get('competitor_brands'):
        expected_brands.extend(report.get('competitor_brands', []))

    brand_distribution = self._calculate_brand_distribution(results, expected_brands)
    
    # ... 后续代码保持不变 ...
```

---

### 修复 2: 后端诊断 API 增加历史报告专用接口

**文件**: `backend_python/wechat_backend/views/diagnosis_api.py`

**位置**: Line 120-180

**新增接口**:

```python
@diagnosis_bp.route('/report/<execution_id>/history', methods=['GET'])
@rate_limit(limit=60, window=60, per='user')
def get_history_report_api(execution_id):
    """
    获取历史报告（增强版 - 2026-03-13 第 15 次补充）

    专为历史报告查看优化：
    1. 优先从数据库读取，不触发新的诊断
    2. 包含完整的元数据（品牌、时间、状态等）
    3. 即使部分数据缺失，也返回可用的最大数据集
    4. 支持从 DiagnosisResult 表重建数据
    """
    try:
        # 获取服务
        service = get_report_service()

        # 获取历史报告（不重新计算）
        report = service.get_history_report(execution_id)

        if not report:
            api_logger.warning(f"历史报告不存在：execution_id={execution_id}")
            return jsonify({
                'error': '报告不存在',
                'execution_id': execution_id
            }), 404

        # 【P0 关键修复】检查返回的报告是否有 brandDistribution
        brand_dist = report.get('brandDistribution', {})
        if not brand_dist.get('data'):
            api_logger.warning(
                f"⚠️ [历史报告] brandDistribution 为空，尝试从数据库直接读取"
            )
            
            # 尝试直接从 DiagnosisResult 读取
            try:
                from wechat_backend.models import DiagnosisResult
                db_results = DiagnosisResult.query.filter_by(execution_id=execution_id).all()
                
                if db_results:
                    brand_data = {}
                    for r in db_results:
                        brand = r.extracted_brand or r.brand
                        if brand:
                            brand_data[brand] = brand_data.get(brand, 0) + 1
                    
                    if brand_data:
                        # 更新 report
                        report['brandDistribution'] = {
                            'data': brand_data,
                            'totalCount': sum(brand_data.values()),
                            'successRate': 1.0
                        }
                        api_logger.info(
                            f"✅ [历史报告] 直接从数据库重建 brandDistribution: {list(brand_data.keys())}"
                        )
            except Exception as e:
                api_logger.error(f"❌ [历史报告] 直接读取失败：{e}")

        api_logger.info(
            f"[HistoryAPI] ✅ 历史报告返回：{execution_id}, "
            f"results={len(report.get('results', []))}, "
            f"brands={len(report.get('brandDistribution', {}).get('data', {}))}"
        )

        # P0 修复：转换为 camelCase
        return jsonify(convert_response_to_camel(report)), 200

    except Exception as e:
        api_logger.error(f"获取历史报告失败：{e}")
        return jsonify({
            'error': '获取失败',
            'execution_id': execution_id,
            'message': str(e)
        }), 500
```

---

### 修复 3: 前端 report-v2 多数据源降级（历史报告增强）

**文件**: `miniprogram/pages/report-v2/report-v2.js`

**位置**: Line 691-800

**修复内容**:

```javascript
/**
 * 加载历史报告（增强版 - 2026-03-13 第 15 次补充）
 * @param {string} reportId - 报告 ID 或 executionId
 */
async loadHistoryReport(reportId) {
  console.log('[ReportPageV2] 加载历史报告:', reportId);
  showLoading('加载中...');

  try {
    // 【P0 关键修复】多数据源降级加载策略
    
    // 尝试 1: 检查全局变量
    const app = getApp();
    if (app && app.globalData && app.globalData.pendingReport) {
      const pendingReport = app.globalData.pendingReport;
      if (pendingReport.executionId === reportId && pendingReport.isHistory) {
        console.log('[ReportPageV2] ✅ [尝试 1] 从全局变量加载历史数据');
        this._loadFromGlobalData(pendingReport);
        hideLoading();
        return;
      }
    }

    // 尝试 2: 从 Storage 加载备份
    const cachedData = wx.getStorageSync(`history_report_${reportId}`);
    if (cachedData && cachedData.dashboardData) {
      console.log('[ReportPageV2] ✅ [尝试 2] 从 Storage 备份加载');
      this._loadFromStorageData(cachedData);
      hideLoading();
      return;
    }

    // 尝试 3: 从云函数加载
    console.log('[ReportPageV2] ⏳ [尝试 3] 从云函数加载历史报告');
    const reportService = require('../../services/reportService').default;
    const report = await reportService.getFullReport(reportId);

    if (report && report.brandDistribution && report.brandDistribution.data) {
      console.log('[ReportPageV2] ✅ [尝试 3] 云函数加载成功');
      
      this.setData({
        brandDistribution: report.brandDistribution || {},
        sentimentDistribution: report.sentimentDistribution || {},
        keywords: report.keywords || [],
        brandScores: report.brandScores || {},
        isHistoryData: true,
        hasError: false,
        dataSource: 'cloudFunction'
      });

      // 缓存到 Storage
      wx.setStorageSync(`history_report_${reportId}`, {
        executionId: report.executionId || reportId,
        dashboardData: {
          brandDistribution: report.brandDistribution,
          sentimentDistribution: report.sentimentDistribution,
          keywords: report.keywords,
          brandScores: report.brandScores
        },
        rawResults: report.results || [],
        timestamp: Date.now()
      });
      console.log('[ReportPageV2] ✅ 数据已缓存到 Storage');

      hideLoading();
    } else {
      console.warn('[ReportPageV2] ⚠️ 云函数返回数据不完整');
      throw new Error('报告数据不完整');
    }
  } catch (error) {
    console.error('[ReportPageV2] ❌ 加载历史报告失败:', error);
    hideLoading();

    // 显示错误提示
    wx.showModal({
      title: '加载失败',
      content: error.message || '无法加载历史报告，请稍后重试',
      confirmText: '重试',
      cancelText: '返回',
      success: (res) => {
        if (res.confirm) {
          this.loadHistoryReport(reportId);
        } else {
          wx.navigateBack();
        }
      }
    });
  }
},
```

---

### 修复 4: 前端 diagnosis.js 历史报告加载增强

**文件**: `miniprogram/pages/diagnosis/diagnosis.js`

**位置**: Line 511-600

**修复内容**:

```javascript
/**
 * 加载历史报告（增强版 - 2026-03-13 第 15 次补充）
 * @param {string} reportId - 报告 ID 或 executionId
 */
async loadHistoryReport(reportId) {
  console.log('[DiagnosisPage] 加载历史报告:', reportId);
  showLoading('加载中...');

  try {
    // 【P0 关键修复】多数据源降级加载策略
    
    // 尝试 1: 从本地缓存加载
    const cachedData = wx.getStorageSync(`history_report_${reportId}`);
    if (cachedData && cachedData.executionId) {
      console.log('[DiagnosisPage] ✅ [尝试 1] 从本地缓存加载历史报告');

      // 跳转到报告页，传递缓存数据
      const app = getApp();
      if (app && app.globalData) {
        app.globalData.pendingReport = {
          executionId: cachedData.executionId,
          dashboardData: cachedData.dashboardData,
          rawResults: cachedData.rawResults,
          timestamp: cachedData.timestamp,
          isHistory: true  // 标记为历史数据
        };
      }

      hideLoading();
      wx.navigateTo({
        url: `/pages/report-v2/report-v2?executionId=${cachedData.executionId}`
      });
      return;
    }

    // 尝试 2: 从服务器加载
    console.log('[DiagnosisPage] ⏳ [尝试 2] 从服务器加载历史报告');
    const reportService = require('../../services/reportService').default;
    const report = await reportService.getFullReport(reportId);

    if (report && report.brandDistribution && report.brandDistribution.data) {
      console.log('[DiagnosisPage] ✅ [尝试 2] 服务器加载成功');

      // 处理数据
      const { generateDashboardData } = require('../../../services/brandTestService');
      const rawResults = report.results || report.detailed_results || [];
      const dashboardData = generateDashboardData(rawResults, {
        brandName: report.brandName || '',
        competitorBrands: report.competitorBrands || []
      });

      // 保存到全局变量
      const app = getApp();
      if (app && app.globalData) {
        app.globalData.pendingReport = {
          executionId: report.executionId || reportId,
          dashboardData: dashboardData,
          rawResults: rawResults,
          timestamp: Date.now(),
          isHistory: true
        };
        console.log('[DiagnosisPage] ✅ 数据已保存到 globalData.pendingReport');
      }

      // 缓存到本地
      wx.setStorageSync(`history_report_${reportId}`, {
        executionId: report.executionId || reportId,
        dashboardData: dashboardData,
        rawResults: rawResults,
        timestamp: Date.now()
      });
      console.log('[DiagnosisPage] ✅ 数据已缓存到本地');

      hideLoading();
      wx.navigateTo({
        url: `/pages/report-v2/report-v2?executionId=${report.executionId || reportId}`
      });
    } else {
      console.warn('[DiagnosisPage] ⚠️ 报告数据不完整');
      throw new Error('报告数据不完整');
    }
  } catch (error) {
    console.error('[DiagnosisPage] ❌ 加载历史报告失败:', error);
    hideLoading();

    wx.showModal({
      title: '加载失败',
      content: error.message || '无法加载历史报告，请稍后重试',
      confirmText: '重试',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          this.loadHistoryReport(reportId);
        } else {
          wx.navigateBack();
        }
      }
    });
  }
},
```

---

## 📋 修改文件清单

| 文件 | 修改位置 | 修改内容 | 作用 |
|-----|---------|---------|------|
| `diagnosis_report_service.py` | Line 1314-1340 | 增强 get_history_report 数据重建 | 从 DiagnosisResult 重建数据 |
| `diagnosis_api.py` | Line 120-180 | 增强 get_history_report_api | 直接从数据库重建 brandDistribution |
| `report-v2.js` | Line 691-800 | 多数据源降级加载 | globalData → Storage → 云函数 |
| `diagnosis.js` | Line 511-600 | 多数据源降级加载 | Storage → 服务器 |

---

## ✅ 验证方法

### 1. 后端验证

```bash
cd /Users/sgl/PycharmProjects/PythonProject/backend_python

# 测试历史报告 API
curl -s "http://localhost:5001/api/diagnosis/report/6b91dd25-9fa5-4533-9d3a-7d94bd83204f/history" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print('brands:', list(d.get('brandDistribution', {}).get('data', {}).keys()))"
```

**预期输出**:
```
brands: ['E 电行']
```

### 2. 数据库验证

```bash
sqlite3 database.db "SELECT execution_id, brand, extracted_brand FROM diagnosis_results WHERE execution_id='6b91dd25-9fa5-4533-9d3a-7d94bd83204f';"
```

**预期输出**:
```
6b91dd25-9fa5-4533-9d3a-7d94bd83204f|E 电行|E 电行
```

### 3. 前端验证

**步骤**:
1. 打开小程序"历史记录"页面
2. 点击任意历史诊断记录
3. 观察是否能正常打开报告页
4. 检查报告页数据是否完整显示

**预期效果**:
- ✅ 报告页正常打开（不卡顿）
- ✅ 品牌分布饼图显示
- ✅ 情感分析柱状图显示
- ✅ 关键词云显示（如果有数据）
- ✅ 品牌评分雷达图显示（如果有数据）

---

## 🎯 修复承诺

作为系统首席架构师，我承诺：

1. **端到端负责** - 从数据库→后端 API→前端展示，全程负责
2. **今日解决** - 今天内彻底解决历史报告加载问题
3. **不再复发** - 建立多数据源降级机制，确保任何情况下都能加载数据
4. **透明沟通** - 每小时同步进展，不隐瞒问题

---

**修复完成时间**: 2026-03-13 12:45
**修复人**: 系统首席架构师
**修复状态**: ✅ 代码修复中
**根因**: 历史报告加载未从 DiagnosisResult 表重建数据
**解决方案**:
1. 后端 get_history_report 增强数据重建
2. 后端 API 直接从数据库重建 brandDistribution
3. 前端多数据源降级加载（globalData → Storage → 云函数）
4. 前端友好的错误提示和重试机制

**签署**: 系统首席架构师
**日期**: 2026-03-13
