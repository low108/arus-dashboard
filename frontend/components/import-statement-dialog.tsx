"use client";

import { FormEvent, useState } from "react";
import { BadgeCheck, CircleAlert, FileLock2, LoaderCircle, Upload } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type Props = { onImported: (jobId?: string) => void };

export function ImportStatementDialog({ onImported }: Props) {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<"idle" | "uploading" | "success" | "needs_password" | "error">("idle");
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!file || !password) return;
    setStatus("uploading"); setMessage("");
    const body = new FormData();
    body.append("pdf", file); body.append("pdf_password", password); body.append("user_id", "local-demo"); body.append("bank_layout", "auto");
    try {
      const result = await api.importStatement(body);
      const state = String(result.state);
      if (state === "needs_password") { setStatus("needs_password"); setMessage("The password was not accepted. Nothing was retained."); }
      else { setStatus("success"); setMessage(state === "imported" ? "Statement imported and reconciled." : "Processing completed, but this statement needs review."); onImported(result.job_id as string | undefined); }
    } catch (error) {
      setStatus("error"); setMessage(error instanceof Error && error.message.includes("provider_failed") ? "PDF processing succeeded, but OpenRouter is not configured or could not be verified." : "The statement could not be processed. Check the backend and file format.");
    } finally { setPassword(""); }
  }

  return <Dialog open={open} onOpenChange={setOpen}><DialogTrigger asChild><Button variant="outline"><Upload />Import statement</Button></DialogTrigger><DialogContent className="sm:max-w-xl"><DialogHeader><DialogTitle>Import encrypted statement</DialogTitle><DialogDescription>Select your encrypted PDF and enter its password. The password is sent only in the local POST body, is never stored, and is never sent to OpenRouter.</DialogDescription></DialogHeader><form onSubmit={submit} className="space-y-5"><div className="rounded-xl border border-teal-100 bg-teal-50/60 p-4"><div className="flex gap-3"><FileLock2 className="mt-0.5 size-5 text-teal-700"/><div><p className="text-sm font-semibold text-slate-900">Local processing boundary</p><p className="mt-1 text-sm leading-5 text-slate-600">Decrypt → extract text → validate model JSON → reconcile exact amounts → delete temporary files.</p></div></div></div><div className="space-y-2"><Label htmlFor="statement-file">Encrypted PDF</Label><Input id="statement-file" type="file" accept="application/pdf,.pdf" required onChange={(event)=>setFile(event.target.files?.[0] || null)} /></div><div className="space-y-2"><Label htmlFor="statement-password">PDF password</Label><Input id="statement-password" type="password" autoComplete="off" required value={password} onChange={(event)=>setPassword(event.target.value)} /></div>{status !== "idle" && <div className={`flex gap-3 rounded-xl border p-3 text-sm ${status === "success" ? "border-teal-200 bg-teal-50 text-teal-900" : status === "uploading" ? "border-slate-200 bg-slate-50 text-slate-700" : "border-amber-200 bg-amber-50 text-amber-900"}`}>{status === "uploading" ? <LoaderCircle className="size-4 animate-spin"/> : status === "success" ? <BadgeCheck className="size-4"/> : <CircleAlert className="size-4"/>}<span>{status === "uploading" ? "Processing locally and waiting for verified extraction…" : message}</span></div>}<DialogFooter><Button type="submit" disabled={!file || !password || status === "uploading"} className="bg-teal-700 text-white hover:bg-teal-800">{status === "uploading" ? "Processing…" : "Import securely"}</Button></DialogFooter></form></DialogContent></Dialog>;
}
