/**
 * 品牌战略洞察报告 API 类型定义
 * 
 * 与 OpenAPI 规范 (docs/api-spec.yaml) 保持一致
 * 用于前端 TypeScript 类型检查和代码提示
 * 
 * @author 系统架构组
 * @date 2026-03-01
 * @version 1.0.0
 */

// ==================== 枚举类型 ====================

/** 报告状态 */
export type ReportStatus = 'pending' | 'processing' | 'completed' | 'failed';

/** 报告阶段 */
export type ReportStage = 'init' | 'ai_fetching' | 'intelligence_analyzing' | 'completed' | 'failed';

/** 质量等级 */
export type QualityLevel = 'very_low' | 'low' | 'medium' | 'high' | 'very_high';

/** 情感标签 */
export type SentimentLabel = 'positive' | 'neutral' | 'negative';

/** 错误状态 */
export type ErrorStatus = 'not_found' | 'failed' | 'timeout' | 'no_results' | 'error';

/** 健康状态 */
export type HealthStatus = 'healthy' | 'degraded' | 'unhealthy';

// ==================== 基础数据类型 ====================

/** GEO 分析数据 */
export interface GeoData {
  brand_mentioned: boolean;
  rank: number;
  sentiment: number;
  cited_sources: string[];
  keywords: Keyword[];
}

/** AI 响应 */
export interface AIResponse {
  content: string;
  latency: number;
}

/** 关键词 */
export interface Keyword {
  word: string;
  count?: number;
  sentiment?: number;
  sentiment_label?: SentimentLabel;
}

/** 诊断结果 */
export interface DiagnosisResult {
  id?: number;
  brand: string;
  question: string;
  model: string;
  response?: AIResponse | null;
  geo_data?: GeoData | null;
  quality_score?: number;
  quality_level?: QualityLevel;
}

/** 分析数据 */
export interface AnalysisData {
  competitive_analysis?: Record<string, any>;
  brand_scores?: Record<string, any>;
  semantic_drift?: Record<string, any>;
  source_purity?: Record<string, any>;
  recommendations?: Record<string, any>;
}

/** 品牌分布 */
export interface BrandDistribution {
  data: Record<string, number>;
  total_count: number;
  warning?: string | null;
}

/** 情感分布 */
export interface SentimentDistribution {
  data: {
    positive: number;
    neutral: number;
    negative: number;
  };
  total_count: number;
  warning?: string | null;
}

/** 元数据 */
export interface Meta {
  data_schema_version: string;
  server_version: string;
  retrieved_at: string;
}

// ==================== 验证相关类型 ====================

/** 验证详情 */
export interface ValidationDetails {
  report_valid: boolean;
  results_valid: boolean;
  analysis_valid: boolean;
  aggregation_valid: boolean;
  checksum_valid: boolean;
}

/** 验证信息 */
export interface Validation {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  quality_issues?: string[];
  quality_score?: number;
  details?: ValidationDetails;
}

/** 质量提示 */
export interface QualityHints {
  has_low_quality_results: boolean;
  has_partial_analysis: boolean;
  warnings: string[];
}

// ==================== 报告主数据 ====================

/** 报告主数据 */
export interface Report {
  id?: number;
  execution_id: string;
  user_id?: string;
  brand_name: string;
  status: ReportStatus;
  progress: number;
  stage: ReportStage;
  is_completed: boolean;
  created_at: string;
  completed_at?: string | null;
  checksum?: string | null;
}

/** 错误信息 */
export interface ErrorInfo {
  status: ErrorStatus;
  message: string;
  suggestion?: string;
  stage?: string;
}

/** 部分结果信息 */
export interface PartialInfo {
  is_partial: boolean;
  progress: number;
  stage: string;
  message: string;
  suggestion: string;
}

// ==================== 完整报告响应 ====================

/** 完整报告响应 */
export interface FullReportResponse {
  report: Report;
  results: DiagnosisResult[];
  analysis: AnalysisData;
  brandDistribution: BrandDistribution;
  sentimentDistribution: SentimentDistribution;
  keywords: Keyword[];
  meta: Meta;
  validation: Validation;
  qualityHints: QualityHints;
  error?: ErrorInfo | null;
  partial?: PartialInfo | null;
  checksum_verified?: boolean;
  lowQualityWarning?: boolean;
}

// ==================== 其他响应类型 ====================

/** 报告摘要 */
export interface ReportSummary {
  id: number;
  execution_id: string;
  brand_name: string;
  status: string;
  progress: number;
  created_at: string;
}

/** 分页信息 */
export interface Pagination {
  page: number;
  limit: number;
  total: number;
  has_more: boolean;
}

/** 历史报告响应 */
export interface HistoryResponse {
  reports: ReportSummary[];
  pagination: Pagination;
}

/** 任务状态响应 */
export interface TaskStatusResponse {
  execution_id: string;
  status: string;
  progress: number;
  stage: string;
  results_count: number;
  total_tasks: number;
  should_stop_polling: boolean;
  detailed_results?: DiagnosisResult[];
}

/** 验证响应 */
export interface ValidationResponse {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  quality_score?: number;
  checksum_verified?: boolean;
}

/** 健康检查响应 */
export interface HealthResponse {
  status: HealthStatus;
  timestamp: string;
  services: Record<string, string>;
}

// ==================== 错误响应类型 ====================

/** 基础错误响应 */
export interface BaseError {
  error: string;
}

/** 404 错误 */
export interface NotFoundError extends BaseError {
  execution_id?: string;
  suggestion?: string;
}

/** 500 错误 */
export interface ServerError extends BaseError {
  message?: string;
  execution_id?: string;
  suggestion?: string;
}

/** 401 错误 */
export interface AuthError extends BaseError {
  message?: string;
}

/** 429 错误 */
export interface RateLimitError extends BaseError {
  retry_after?: number;
}

/** API 错误联合类型 */
export type ApiError = NotFoundError | ServerError | AuthError | RateLimitError;

// ==================== 请求参数类型 ====================

/** 获取报告参数 */
export interface GetReportParams {
  execution_id: string;
}

/** 获取历史参数 */
export interface GetHistoryParams {
  user_id?: string;
  page?: number;
  limit?: number;
}

/** 获取任务状态参数 */
export interface GetTaskStatusParams {
  execution_id: string;
  since?: string;
}

// ==================== 工具类型 ====================

/** 部分类型（所有字段可选） */
export type Partial<T> = {
  [P in keyof T]?: T[P];
};

/** 只读类型 */
export type Readonly<T> = {
  readonly [P in keyof T]: T[P];
};

/** 报告响应联合类型 */
export type ReportApiResponse = FullReportResponse | NotFoundError | ServerError;

/** 任意 API 响应类型 */
export type ApiResponse<T = any> = T | ApiError;

// ==================== 组件 Props 类型 ====================

/** 报告展示组件 Props */
export interface ReportDisplayProps {
  report: FullReportResponse;
  loading?: boolean;
  onError?: (error: ApiError) => void;
}

/** 结果列表组件 Props */
export interface ResultsListProps {
  results: DiagnosisResult[];
  selectedBrand?: string;
  onResultClick?: (result: DiagnosisResult) => void;
}

/** 品牌分布图表组件 Props */
export interface BrandDistributionChartProps {
  data: BrandDistribution;
  loading?: boolean;
}

/** 情感分布图表组件 Props */
export interface SentimentDistributionChartProps {
  data: SentimentDistribution;
  loading?: boolean;
}

/** 关键词云组件 Props */
export interface WordCloudProps {
  keywords: Keyword[];
  loading?: boolean;
}

/** 验证信息组件 Props */
export interface ValidationInfoProps {
  validation: Validation;
  qualityHints: QualityHints;
}

/** 空状态组件 Props */
export interface EmptyStateProps {
  type: 'not_found' | 'failed' | 'timeout' | 'no_results' | 'partial';
  message?: string;
  suggestion?: string;
  onRetry?: () => void;
  onBack?: () => void;
}

/** 降级提示横幅 Props */
export interface FallbackBannerProps {
  error?: ErrorInfo | null;
  partial?: PartialInfo | null;
  qualityHints?: QualityHints | null;
  onRetry?: () => void;
}

// ==================== 服务类型 ====================

/** API 服务配置 */
export interface ApiConfig {
  baseUrl: string;
  timeout?: number;
  headers?: Record<string, string>;
}

/** API 服务接口 */
export interface ApiService {
  getFullReport(executionId: string): Promise<FullReportResponse>;
  getHistory(params?: GetHistoryParams): Promise<HistoryResponse>;
  getTaskStatus(executionId: string, since?: string): Promise<TaskStatusResponse>;
  validateReport(executionId: string): Promise<ValidationResponse>;
  healthCheck(): Promise<HealthResponse>;
}

/** 缓存服务接口 */
export interface CacheService {
  get<T>(key: string): T | null;
  set<T>(key: string, value: T, ttl?: number): void;
  remove(key: string): void;
  clear(): void;
}

// ==================== 事件类型 ====================

/** 报告加载完成事件 */
export interface ReportLoadedEvent {
  type: 'report:loaded';
  payload: FullReportResponse;
}

/** 报告加载失败事件 */
export interface ReportLoadFailedEvent {
  type: 'report:failed';
  payload: ApiError;
}

/** 报告验证事件 */
export interface ReportValidatedEvent {
  type: 'report:validated';
  payload: Validation;
}

/** 诊断事件联合类型 */
export type DiagnosisEvent = ReportLoadedEvent | ReportLoadFailedEvent | ReportValidatedEvent;

/** 事件处理器类型 */
export type EventHandler<T extends DiagnosisEvent> = (event: T) => void;

// ==================== 状态管理类型 ====================

/** 报告状态 */
export interface ReportState {
  loading: boolean;
  report: FullReportResponse | null;
  error: ApiError | null;
  validation: Validation | null;
}

/** 报告操作 */
export interface ReportActions {
  loadReport: (executionId: string) => Promise<void>;
  refreshReport: () => Promise<void>;
  clearReport: () => void;
  setValidation: (validation: Validation) => void;
}

/** 报告存储接口 */
export interface ReportStore extends ReportState, ReportActions {}

// ==================== 工具函数类型 ====================

/** 类型守卫：判断是否为错误响应 */
export function isError(response: any): response is ApiError {
  return response && typeof response === 'object' && 'error' in response;
}

/** 类型守卫：判断是否为 404 错误 */
export function isNotFoundError(response: any): response is NotFoundError {
  return isError(response) && response.error === '报告不存在';
}

/** 类型守卫：判断是否为完整报告 */
export function isFullReport(response: any): response is FullReportResponse {
  return response && 'report' in response && 'results' in response;
}

/** 类型守卫：判断是否为降级报告 */
export function isFallbackReport(response: any): boolean {
  return response && ('error' in response || 'partial' in response);
}

// ==================== 导出 ====================

export type {
  // 基础类型
  GeoData,
  AIResponse,
  Keyword,
  DiagnosisResult,
  AnalysisData,
  BrandDistribution,
  SentimentDistribution,
  Meta,
  
  // 验证类型
  ValidationDetails,
  Validation,
  QualityHints,
  
  // 报告类型
  Report,
  ErrorInfo,
  PartialInfo,
  FullReportResponse,
  
  // 其他响应
  ReportSummary,
  Pagination,
  HistoryResponse,
  TaskStatusResponse,
  ValidationResponse,
  HealthResponse,
  
  // 错误类型
  BaseError,
  NotFoundError,
  ServerError,
  AuthError,
  RateLimitError,
  ApiError,
  
  // 请求参数
  GetReportParams,
  GetHistoryParams,
  GetTaskStatusParams,
  
  // 组件 Props
  ReportDisplayProps,
  ResultsListProps,
  BrandDistributionChartProps,
  SentimentDistributionChartProps,
  WordCloudProps,
  ValidationInfoProps,
  EmptyStateProps,
  FallbackBannerProps,
  
  // 服务类型
  ApiConfig,
  ApiService,
  CacheService,
  
  // 事件类型
  ReportLoadedEvent,
  ReportLoadFailedEvent,
  ReportValidatedEvent,
  DiagnosisEvent,
  EventHandler,
  
  // 状态类型
  ReportState,
  ReportActions,
  ReportStore
};

export {
  // 枚举类型
  type ReportStatus,
  type ReportStage,
  type QualityLevel,
  type SentimentLabel,
  type ErrorStatus,
  type HealthStatus,
  
  // 工具函数
  isError,
  isNotFoundError,
  isFullReport,
  isFallbackReport
};
