export type NavView = "overview" | "goals" | "transactions" | "statements" | "activity" | "settings";

export type StatementState = "discovered" | "processing" | "needs_password" | "needs_review" | "imported" | "unsupported" | "failed";

export type Statement = {
  id: string; institution: string; account: string; accountType: string; period: string;
  source: string; state: StatementState; reconciliation: "Matched" | "Review needed";
  transactions: number; pages: string;
};

export type AgentStage = {
  id: string; stage: string; detail: string; provider: string; model?: string;
  status: "Completed" | "Needs review"; duration: string; records: number;
  retries: number; timestamp: string;
};

export type IntegrationStatus = {
  gmail: { implemented: boolean; connected: boolean; mode: "real"; account: string | null; status: string };
  openrouter: { implemented: boolean; configured: boolean; verified: boolean; mode: "real"; model: string; status: string };
  pdf: { implemented: boolean; encrypted_pdf_supported: boolean; status: string };
  exa: { implemented: boolean; configured: boolean; status: string };
  google_sheets: { implemented: boolean; connected: boolean; status: string };
};

export type Goal = {
  id: number;
  name: string;
  purpose: string;
  target_amount: string;
  saved_amount: string;
  currency: string;
  target_date: string | null;
  created_at: string;
  updated_at: string;
};

export type OverviewData = {
  latest_reported_cash: string;
  reported_card_debt: string;
  income: string;
  spending: string;
  verified_statement_count: number;
  total_statement_count: number;
  balance_dates: string[];
  mixed_dates: boolean;
  data_mode: "real" | "empty";
};

export type Transaction = {
  source_identifier: string; date: string; description: string; direction: "debit" | "credit";
  amount: string; currency: string; page_reference: number; suggested_merchant: string | null;
  suggested_category: string | null; category_confidence: string | null; statement_id: string | number;
  institution: string; masked_account_identifier: string;
};
