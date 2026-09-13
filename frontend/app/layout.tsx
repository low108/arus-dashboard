import type { Metadata } from "next";
import "@copilotkit/react-core/v2/styles.css";
import "./globals.css";
import { ArusCopilotProvider } from "@/components/copilot-provider";

export const metadata: Metadata = {
  title: "Arus · Financial agent",
  description: "A Gmail-native financial statement agent with deterministic ledger verification.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="antialiased"><ArusCopilotProvider>{children}</ArusCopilotProvider></body>
    </html>
  );
}
