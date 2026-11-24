import type {
  AIReport,
  AssistantAnswer,
  Company,
  CompanyDetail,
  ComparisonResponse,
  EquityDocument,
  FinancialMetric,
  Holding,
  MetricCandidate,
  PortfolioSummary,
  PriceBulkUploadResult,
  PriceHistoryPoint,
  RiskAlert,
  SearchResult,
  ShareholdingPattern,
  TimelineEvent,
  WatchlistItem,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export { API_BASE_URL };

class APIError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit & { token?: string | null }): Promise<T> {
  const { token, ...rest } = options || {};
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...rest,
    headers: {
      ...(rest.body && !(rest.body instanceof FormData) && !(rest.body instanceof URLSearchParams)
        ? { "Content-Type": "application/json" }
        : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...rest.headers,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch {
      // response wasn't JSON; fall back to statusText
    }
    throw new APIError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}

export const api = {
  // Companies
  listCompanies: (): Promise<Company[]> => request("/companies"),
  getCompany: (id: string): Promise<CompanyDetail> => request(`/companies/${id}`),
  createCompany: (data: { symbol: string; name: string; sector?: string }): Promise<Company> =>
    request("/companies", { method: "POST", body: JSON.stringify(data) }),

  // Financial metrics
  addFinancialMetric: (companyId: string, data: Record<string, unknown>): Promise<FinancialMetric> =>
    request(`/companies/${companyId}/financial-metrics`, { method: "POST", body: JSON.stringify(data) }),
  addShareholding: (companyId: string, data: Record<string, unknown>): Promise<ShareholdingPattern> =>
    request(`/companies/${companyId}/shareholding`, { method: "POST", body: JSON.stringify(data) }),

  // Documents
  listDocuments: (companyId: string): Promise<EquityDocument[]> =>
    request(`/companies/${companyId}/documents`),
  getDocument: (companyId: string, documentId: string): Promise<EquityDocument> =>
    request(`/companies/${companyId}/documents/${documentId}`),
  uploadDocument: (companyId: string, file: File, documentType: string): Promise<EquityDocument> => {
    const form = new FormData();
    form.append("file", file);
    form.append("document_type", documentType);
    return request(`/companies/${companyId}/documents`, { method: "POST", body: form });
  },
  listMetricCandidates: (companyId: string, documentId: string): Promise<MetricCandidate[]> =>
    request(`/companies/${companyId}/documents/${documentId}/metric-candidates`),
  acceptMetricCandidate: (companyId: string, documentId: string, candidateId: string): Promise<MetricCandidate> =>
    request(`/companies/${companyId}/documents/${documentId}/metric-candidates/${candidateId}/accept`, {
      method: "POST",
    }),
  rejectMetricCandidate: (companyId: string, documentId: string, candidateId: string): Promise<MetricCandidate> =>
    request(`/companies/${companyId}/documents/${documentId}/metric-candidates/${candidateId}/reject`, {
      method: "POST",
    }),
  promoteMetricCandidate: (
    companyId: string,
    documentId: string,
    candidateId: string,
    data: { period_type: string; period_end_date: string; fiscal_year: string }
  ): Promise<FinancialMetric> =>
    request(`/companies/${companyId}/documents/${documentId}/metric-candidates/${candidateId}/promote`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Search
  searchDocuments: (companyId: string, query: string): Promise<{ query: string; results: SearchResult[] }> =>
    request(`/companies/${companyId}/search?q=${encodeURIComponent(query)}`),

  // AI reports
  listReports: (companyId: string): Promise<AIReport[]> => request(`/companies/${companyId}/ai-reports`),
  getReport: (companyId: string, reportId: string): Promise<AIReport> =>
    request(`/companies/${companyId}/ai-reports/${reportId}`),
  generateReport: (companyId: string): Promise<AIReport> =>
    request(`/companies/${companyId}/ai-reports`, { method: "POST" }),

  // Compare
  compareCompanies: (symbols: string[]): Promise<ComparisonResponse> =>
    request(`/compare?symbols=${symbols.map(encodeURIComponent).join(",")}`),

  // Portfolio (all require token)
  listHoldings: (token: string): Promise<Holding[]> => request("/portfolio/holdings", { token }),
  addHolding: (
    token: string,
    data: { company_id: string; quantity: string; average_buy_price: string; target_allocation_pct?: string }
  ): Promise<Holding> => request("/portfolio/holdings", { method: "POST", body: JSON.stringify(data), token }),
  updateHolding: (token: string, holdingId: string, data: Record<string, unknown>): Promise<Holding> =>
    request(`/portfolio/holdings/${holdingId}`, { method: "PATCH", body: JSON.stringify(data), token }),
  deleteHolding: (token: string, holdingId: string): Promise<void> =>
    request(`/portfolio/holdings/${holdingId}`, { method: "DELETE", token }),
  getPortfolioSummary: (token: string): Promise<PortfolioSummary> => request("/portfolio/summary", { token }),

  // Watchlist (all require token)
  listWatchlist: (token: string): Promise<WatchlistItem[]> => request("/watchlist", { token }),
  addToWatchlist: (token: string, companyId: string, note?: string): Promise<WatchlistItem> =>
    request("/watchlist", { method: "POST", body: JSON.stringify({ company_id: companyId, note }), token }),
  removeFromWatchlist: (token: string, itemId: string): Promise<void> =>
    request(`/watchlist/${itemId}`, { method: "DELETE", token }),

  // Risk alerts
  listCompanyAlerts: (companyId: string): Promise<RiskAlert[]> =>
    request(`/companies/${companyId}/risk-alerts`),
  listMyAlerts: (token: string): Promise<RiskAlert[]> => request("/me/alerts", { token }),
  acknowledgeAlert: (token: string, alertId: string): Promise<void> =>
    request(`/alerts/${alertId}/acknowledge`, { method: "POST", token }),

  // Prices
  addPrice: (companyId: string, priceDate: string, closePrice: string): Promise<PriceHistoryPoint> =>
    request(`/companies/${companyId}/prices`, {
      method: "POST",
      body: JSON.stringify({ price_date: priceDate, close_price: closePrice }),
    }),
  bulkUploadPrices: (companyId: string, file: File): Promise<PriceBulkUploadResult> => {
    const form = new FormData();
    form.append("file", file);
    return request(`/companies/${companyId}/prices/bulk`, { method: "POST", body: form });
  },
  listPrices: (companyId: string): Promise<PriceHistoryPoint[]> =>
    request(`/companies/${companyId}/prices`),
  getLatestPrice: (companyId: string): Promise<PriceHistoryPoint> =>
    request(`/companies/${companyId}/prices/latest`),

  // Timeline
  getCompanyTimeline: (companyId: string): Promise<TimelineEvent[]> =>
    request(`/companies/${companyId}/timeline`),

  // AI Assistant
  askAssistant: (companyId: string, question: string): Promise<AssistantAnswer> =>
    request(`/companies/${companyId}/assistant/ask`, {
      method: "POST",
      body: JSON.stringify({ question }),
    }),
};

/**
 * Downloads an authenticated file (CSV exports) by fetching with the
 * bearer token, then triggering a browser save via a throwaway anchor —
 * a plain <a href> can't carry an Authorization header, so this is the
 * only way to download an auth-gated file client-side.
 */
export async function downloadAuthenticatedFile(path: string, token: string, filename: string) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok) {
    throw new APIError(response.status, "Download failed");
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export { APIError };
