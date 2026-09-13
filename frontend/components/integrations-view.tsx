"use client";

import { useState } from "react";
import { BadgeCheck, CircleAlert, ExternalLink, FileLock2, Mail, RefreshCw, Sheet, Sparkles } from "lucide-react";
import { api, API_URL } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { IntegrationStatus } from "@/types/finance";

function StatusBadge({label}:{label:string}) { const positive=label==="Connected — real"; const warning=label==="Configured but unverified"; return <Badge variant="outline" className={positive?"border-teal-200 bg-teal-50 text-teal-800":warning?"border-amber-200 bg-amber-50 text-amber-900":"border-slate-200 bg-slate-50 text-slate-600"}>{positive?<BadgeCheck/>:<CircleAlert/>}{label}</Badge>; }

export function IntegrationsView({status, onRefresh}:{status:IntegrationStatus|null;onRefresh:()=>Promise<void>}) {
  const [busy,setBusy]=useState(""); const [message,setMessage]=useState("");
  async function verify(){setBusy("openrouter");setMessage("");try{const result=await api.verifyOpenRouter();setMessage(result.status==="ok"?`OpenRouter verified in ${result.latency_ms} ms${result.request_id?` · Request ${result.request_id}`:""}.`:`Verification failed safely: ${result.error_type||result.status}.`);await onRefresh();}catch{setMessage("OpenRouter verification could not run.");}finally{setBusy("");}}
  async function disconnect(){setBusy("gmail");await api.disconnectGmail();await onRefresh();setBusy("");}
  const cards=[
    {key:"gmail",icon:Mail,title:"Gmail",copy:"Read-only attachment discovery. Email bodies are not retained.",state:status?.gmail.status||"Error",detail:status?.gmail.account||"Connect Google to discover allowed statement attachments."},
    {key:"openrouter",icon:Sparkles,title:"OpenRouter",copy:"Strict structured extraction from minimum necessary local text.",state:status?.openrouter.status||"Error",detail:`Model: ${status?.openrouter.model||"Unavailable"}`},
    {key:"pdf",icon:FileLock2,title:"Local PDF processor",copy:"Encrypted PDF decryption and page-aware text extraction.",state:status?.pdf.status||"Error",detail:"pikepdf + pdfplumber · local"},
    {key:"sheets",icon:Sheet,title:"Google Sheets",copy:"Separate, user-approved export permission.",state:status?.google_sheets.status||"Not configured",detail:"Coming next · CSV export is available now"},
    {key:"exa",icon:ExternalLink,title:"Exa",copy:"Public research for user-confirmed holdings only.",state:status?.exa.status||"Not configured",detail:"Not implemented"},
  ];
  return <div className="space-y-5"><div className="surface p-5 sm:p-6"><div className="flex flex-wrap items-start justify-between gap-4"><div><p className="eyebrow">Integration truth</p><h2 className="mt-1">What is genuinely connected</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">These states come directly from the backend; unverified integrations are never labelled as connected.</p></div><Button variant="outline" onClick={onRefresh}><RefreshCw/>Refresh status</Button></div></div><div className="grid gap-4 lg:grid-cols-2">{cards.map((card)=><article className="surface p-5" key={card.key}><div className="flex items-start gap-4"><div className="icon-tile"><card.icon/></div><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center justify-between gap-2"><h2>{card.title}</h2><StatusBadge label={card.state}/></div><p className="mt-2 text-sm leading-5 text-slate-600">{card.copy}</p><p className="mt-3 text-xs font-medium text-slate-500">{card.detail}</p><div className="mt-5">{card.key==="gmail"&&(status?.gmail.connected?<Button variant="outline" onClick={disconnect} disabled={busy==="gmail"}>Disconnect Gmail</Button>:<Button asChild className="bg-teal-700 text-white hover:bg-teal-800"><a href={`${API_URL}/api/auth/google/start`}>Connect Gmail <ExternalLink/></a></Button>)}{card.key==="openrouter"&&<Button variant="outline" onClick={verify} disabled={busy==="openrouter"}>{busy==="openrouter"?"Verifying…":"Verify real request"}</Button>}</div></div></div></article>)}</div>{message&&<div className="notice" role="status"><CircleAlert className="mt-0.5 size-5 shrink-0 text-amber-700"/><p className="text-sm text-slate-700">{message}</p></div>}</div>;
}
