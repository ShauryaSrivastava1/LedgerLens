export type PeriodType = "QUARTERLY" | "ANNUAL";

export interface Company {
  id: string;
  symbol: string;
  name: string;
  sector: string | null;
  industry: string | null;
  isin: string | null;
  created_at: string;
  updated_at: string;
}

export interface FinancialMetric {
  id: string;
  company_id: string;
  period_type: PeriodType;
  period_end_date: string;
  fiscal_year: string;
  revenue: string | null;
  pat: string | null;
  ebitda_margin: string | null;
  net_margin: string | null;
  roe: string | null;
  roce: string | null;
  debt_equity: string | null;
  free_cash_flow: string | null;
  receivable_days: string | null;
  [key: string]: string | null; // remaining metric fields
}

export interface ShareholdingPattern {
  id: string;
  company_id: string;
  period_end_date: string;
  promoter_holding_pct: string | null;
  institution_holding_pct: string | null;
  pledge_pct: string | null;
  [key: string]: string | null;
}

export interface CompanyDetail extends Company {
  financial_metrics: FinancialMetric[];
  shareholding_records: ShareholdingPattern[];
}

export type DocumentType =
  | "ANNUAL_REPORT"
  | "QUARTERLY_RESULT"
  | "INVESTOR_PRESENTATION"
  | "EARNINGS_CALL_TRANSCRIPT"
  | "CORPORATE_ANNOUNCEMENT"
  | "OTHER";

export type DocumentStatus = "PENDING" | "PROCESSING" | "PROCESSED" | "FAILED";

export interface EquityDocument {
  id: string;
  company_id: string;
  document_type: DocumentType;
  original_filename: string;
  period_end_date: string | null;
  status: DocumentStatus;
  error_message: string | null;
  page_count: number | null;
  char_count: number | null;
  uploaded_at: string;
  processed_at: string | null;
}

export type MetricCandidateStatus = "PENDING_REVIEW" | "ACCEPTED" | "REJECTED";

export interface MetricCandidate {
  id: string;
  document_id: string;
  metric_name: string;
  extracted_value: string | null;
  unit_note: string | null;
  raw_text_snippet: string;
  page_number: number | null;
  confidence: string;
  status: MetricCandidateStatus;
  promoted_financial_metric_id: string | null;
  created_at: string;
  reviewed_at: string | null;
}

export interface SearchResult {
  document_id: string;
  document_filename: string;
  document_type: DocumentType;
  page_number: number | null;
  text: string;
  relevance_score: number;
}

export interface FlagItem {
  statement: string;
  evidence: string;
  source_type: "document" | "financial_metric";
  document_id: string | null;
  page_number: number | null;
  period: string | null;
  confidence: number;
  citation_verified: boolean;
}

export interface AIReport {
  id: string;
  company_id: string;
  llm_provider: string;
  llm_model: string;
  overall_score: string | null;
  financial_health_score: string | null;
  growth_score: string | null;
  profitability_score: string | null;
  governance_score: string | null;
  moat_score: string | null;
  valuation_score: string | null;
  risk_score: string | null;
  confidence_score: string;
  summary: string;
  green_flags: FlagItem[];
  red_flags: FlagItem[];
  questions_investors_should_ask: string[];
  things_to_verify: string[];
  potential_risks: string[];
  context_snapshot: { document_ids: string[]; periods: string[]; topics_queried: string[] };
  generated_at: string;
}

export interface ComparisonRow {
  company_id: string;
  symbol: string;
  name: string;
  sector: string | null;
  latest_period_label: string | null;
  revenue: string | null;
  revenue_growth_pct: number | null;
  pat: string | null;
  pat_growth_pct: number | null;
  roce: string | null;
  roe: string | null;
  ebitda_margin: string | null;
  net_margin: string | null;
  debt_equity: string | null;
  free_cash_flow: string | null;
  promoter_holding_pct: string | null;
  pledge_pct: string | null;
  latest_report_id: string | null;
  overall_score: string | null;
  moat_score: string | null;
  governance_score: string | null;
  valuation_score: string | null;
  risk_score: string | null;
  report_confidence: string | null;
}

export interface ComparisonResponse {
  symbols: string[];
  rows: ComparisonRow[];
}

export interface Holding {
  id: string;
  user_id: string;
  company_id: string;
  quantity: string;
  average_buy_price: string;
  target_allocation_pct: string | null;
  created_at: string;
  updated_at: string;
}

export interface HoldingRow {
  holding_id: string;
  company_id: string;
  symbol: string;
  name: string;
  sector: string | null;
  quantity: string;
  average_buy_price: string;
  invested_amount: string;
  target_allocation_pct: string | null;
  actual_allocation_pct: string | null;
  current_price: string | null;
  price_as_of: string | null;
  price_staleness_days: number | null;
  current_value: string | null;
  unrealized_pnl: string | null;
  unrealized_pnl_pct: number | null;
  down_significantly_from_buy: boolean;
}

export interface SectorAllocation {
  sector: string;
  invested_amount: string;
  actual_allocation_pct: string;
}

export interface PortfolioSummary {
  total_invested: string;
  total_current_value: string | null;
  total_unrealized_pnl: string | null;
  total_unrealized_pnl_pct: number | null;
  all_holdings_priced: boolean;
  holdings: HoldingRow[];
  sector_allocation: SectorAllocation[];
  note: string;
  price_data_note: string;
}

export interface WatchlistItem {
  id: string;
  user_id: string;
  company_id: string;
  note: string | null;
  added_at: string;
}

export type RiskAlertType =
  | "PLEDGE_INCREASE"
  | "PROMOTER_HOLDING_DECREASE"
  | "GOVERNANCE_SCORE_DROP"
  | "OVERALL_SCORE_DROP";

export interface RiskAlert {
  id: string;
  company_id: string;
  alert_type: RiskAlertType;
  severity: "LOW" | "MEDIUM" | "HIGH";
  message: string;
  evidence: string;
  triggered_at: string;
  acknowledged: boolean;
}

export interface PriceHistoryPoint {
  id: string;
  company_id: string;
  price_date: string;
  close_price: string;
  source: string | null;
  created_at: string;
}

export interface PriceBulkUploadResult {
  rows_added: number;
  rows_skipped_duplicate: number;
  rows_with_errors: number;
  errors: string[];
}

export type TimelineEventType = "DOCUMENT_UPLOADED" | "AI_REPORT_GENERATED" | "RISK_ALERT";

export interface TimelineEvent {
  event_type: TimelineEventType;
  occurred_at: string;
  title: string;
  description: string;
  related_id: string;
}

// ============================================================
// Milestone 9: AI Assistant
// ============================================================

export interface AssistantCitation {
  source_type: "document" | "financial_metric";
  document_id: string | null;
  page_number: number | null;
  period: string | null;
  reference: string;
  confidence: number;
  citation_verified: boolean;
}

export interface AssistantContextSnapshot {
  document_ids: string[];
  periods: string[];
  chunks_retrieved: number;
}

export interface AssistantAnswer {
  company_id: string;
  question: string;
  answer: string;
  citations: AssistantCitation[];
  confidence: number;
  insufficient_evidence: boolean;
  context_snapshot: AssistantContextSnapshot;
}
