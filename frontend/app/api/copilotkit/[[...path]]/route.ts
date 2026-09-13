import { createOpenAI } from "@ai-sdk/openai";
import { BuiltInAgent, CopilotRuntime, createCopilotRuntimeHandler, defineTool } from "@copilotkit/runtime/v2";
import { z } from "zod";

const apiUrl = process.env.ARUS_API_URL || "http://127.0.0.1:8000";
const openrouter = createOpenAI({
  apiKey: process.env.OPENROUTER_API_KEY,
  baseURL: process.env.OPENROUTER_BASE_URL || "https://openrouter.ai/api/v1",
});

async function backend(path: string, init?: RequestInit) {
  const response = await fetch(`${apiUrl}${path}`, init);
  if (!response.ok) throw new Error(`Arus backend returned ${response.status}`);
  return response.json();
}

const runtime = new CopilotRuntime({
  agents: {
    arus: new BuiltInAgent({
      model: openrouter(process.env.OPENROUTER_MODEL || "openai/gpt-4.1-mini"),
      maxSteps: 3,
      prompt: "You are Arus, a concise personal finance copilot. Use only the real data returned by tools. Never invent balances, transactions, Gmail state, or goals. Explain when setup or user authorization is required.",
      tools: [
        defineTool({
          name: "get_financial_summary",
          description: "Read the user's real imported statement summary and real financial goals from Arus.",
          parameters: z.object({}),
          execute: async () => {
            const [overview, goals] = await Promise.all([backend("/api/overview"), backend("/api/goals")]);
            return { overview, goals };
          },
        }),
        defineTool({
          name: "sync_gmail_statements",
          description: "Use the user's authorized read-only Gmail connection to discover and process real PDF statement attachments.",
          parameters: z.object({ confirmed: z.boolean().describe("True only after the user explicitly asks to sync Gmail") }),
          execute: async ({ confirmed }) => confirmed ? backend("/api/sync", { method: "POST" }) : { status: "confirmation_required" },
        }),
      ],
    }),
  },
});

const handler = createCopilotRuntimeHandler({ runtime, basePath: "/api/copilotkit", cors: true });

export const GET = handler;
export const POST = handler;
export const OPTIONS = handler;
