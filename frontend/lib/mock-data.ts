import type { AgentStage, Statement } from "@/types/finance";

export const statements: Statement[] = [
  { id: "stmt_0931", institution: "Meridian Bank", account: "•••• 4821", accountType: "Current account", period: "1–31 Aug 2026", source: "Gmail · statements@meridian.example", state: "imported", reconciliation: "Matched", transactions: 38, pages: "Statement p. 1–4" },
  { id: "stmt_0932", institution: "Northstar Card", account: "•••• 7314", accountType: "Credit card", period: "6 Aug–5 Sep 2026", source: "Gmail · estatement@northstar.example", state: "imported", reconciliation: "Matched", transactions: 21, pages: "Statement p. 1–3" },
  { id: "stmt_0933", institution: "Harbour Savings", account: "•••• 1098", accountType: "Savings account", period: "1–31 Aug 2026", source: "Gmail · alerts@harbour.example", state: "needs_password", reconciliation: "Review needed", transactions: 0, pages: "Encrypted attachment" },
];

export const stages: AgentStage[] = [
  { id: "run-1", stage: "Gmail", detail: "3 supported attachments discovered", provider: "Synthetic Gmail adapter", status: "Completed", duration: "0.8s", records: 3, retries: 0, timestamp: "13 Sep · 10:42:08" },
  { id: "run-2", stage: "Local PDF Processor", detail: "Decrypted and extracted text locally", provider: "pikepdf + pdfplumber", status: "Completed", duration: "1.3s", records: 2, retries: 0, timestamp: "13 Sep · 10:42:10" },
  { id: "run-3", stage: "OpenRouter", detail: "No real request recorded for this workspace", provider: "OpenRouter · MOCKED DISPLAY", model: "Configured at runtime", status: "Needs review", duration: "—", records: 0, retries: 0, timestamp: "Not run" },
  { id: "run-4", stage: "Ledger Guard", detail: "Balances reconciled with exact decimals", provider: "Deterministic code", status: "Completed", duration: "0.02s", records: 2, retries: 0, timestamp: "13 Sep · 10:42:15" },
  { id: "run-5", stage: "Local PDF Processor", detail: "Password required; document not retained", provider: "pikepdf", status: "Needs review", duration: "0.1s", records: 1, retries: 0, timestamp: "13 Sep · 10:42:16" },
];

export const transactions = [
  { source_identifier: "p1-r1", date: "2026-08-28", description: "SALARY CREDIT ARUS DEMO", direction: "credit" as const, amount: "6800.00", currency: "MYR", page_reference: 1, suggested_merchant: "Salary", suggested_category: "Income", category_confidence: "0.99", statement_id: "stmt_0931", institution: "Meridian Bank", masked_account_identifier: "•••• 4821" },
  { source_identifier: "p1-r2", date: "2026-08-27", description: "JAYA GROCER 0826", direction: "debit" as const, amount: "186.40", currency: "MYR", page_reference: 1, suggested_merchant: "Jaya Grocer", suggested_category: "Groceries", category_confidence: "0.96", statement_id: "stmt_0931", institution: "Meridian Bank", masked_account_identifier: "•••• 4821" },
  { source_identifier: "p2-r1", date: "2026-08-25", description: "TNB BILLPAY 2408", direction: "debit" as const, amount: "142.80", currency: "MYR", page_reference: 2, suggested_merchant: "TNB", suggested_category: "Utilities", category_confidence: "0.98", statement_id: "stmt_0931", institution: "Meridian Bank", masked_account_identifier: "•••• 4821" },
  { source_identifier: "p2-r2", date: "2026-08-22", description: "GRAB* TRIP 821", direction: "debit" as const, amount: "23.50", currency: "MYR", page_reference: 2, suggested_merchant: "Grab", suggested_category: "Transport", category_confidence: "0.94", statement_id: "stmt_0931", institution: "Meridian Bank", masked_account_identifier: "•••• 4821" },
  { source_identifier: "p1-r3", date: "2026-08-20", description: "MERCHANT* KLG 8371", direction: "debit" as const, amount: "68.20", currency: "MYR", page_reference: 1, suggested_merchant: "KLG Merchant", suggested_category: "Dining", category_confidence: "0.62", statement_id: "stmt_0932", institution: "Northstar Card", masked_account_identifier: "•••• 7314" },
  { source_identifier: "p2-r3", date: "2026-08-18", description: "NETFLIX.COM", direction: "debit" as const, amount: "55.00", currency: "MYR", page_reference: 2, suggested_merchant: "Netflix", suggested_category: "Subscriptions", category_confidence: "0.99", statement_id: "stmt_0932", institution: "Northstar Card", masked_account_identifier: "•••• 7314" },
  { source_identifier: "p3-r1", date: "2026-08-15", description: "PETRONAS 1043", direction: "debit" as const, amount: "90.00", currency: "MYR", page_reference: 3, suggested_merchant: "Petronas", suggested_category: "Transport", category_confidence: "0.95", statement_id: "stmt_0932", institution: "Northstar Card", masked_account_identifier: "•••• 7314" },
];
