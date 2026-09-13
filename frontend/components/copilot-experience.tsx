"use client";

import { CopilotKit, CopilotPopup } from "@copilotkit/react-core/v2";

export function ArusCopilotExperience() {
  return (
    <CopilotKit runtimeUrl="/api/copilotkit" agentId="arus" enableInspector={false}>
      <CopilotPopup defaultOpen={false} />
    </CopilotKit>
  );
}
