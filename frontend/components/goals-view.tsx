"use client";

import { FormEvent, useState } from "react";
import { CalendarDays, Flag, Plus, Trash2, WalletCards } from "lucide-react";
import { api } from "@/lib/api";
import type { Goal } from "@/types/finance";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const purposes = ["Emergency fund", "Travel", "Home", "Education", "Big purchase", "Debt payoff", "Custom"];

function money(value: string, currency: string) {
  return new Intl.NumberFormat("en-MY", { style: "currency", currency }).format(Number(value));
}

export function GoalsView({ goals, onRefresh }: { goals: Goal[]; onRefresh: () => Promise<void> }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [name, setName] = useState("");
  const [purpose, setPurpose] = useState("Emergency fund");
  const [target, setTarget] = useState("");
  const [saved, setSaved] = useState("0");
  const [date, setDate] = useState("");
  const [savedDrafts, setSavedDrafts] = useState<Record<number, string>>({});

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await api.createGoal({ name, purpose, target_amount: target, saved_amount: saved || "0", currency: "MYR", target_date: date || null });
      setOpen(false); setName(""); setTarget(""); setSaved("0"); setDate("");
      await onRefresh();
    } finally { setBusy(false); }
  }

  async function remove(id: number) { await api.deleteGoal(id); await onRefresh(); }

  async function updateSaved(goal: Goal) {
    await api.updateGoal(goal.id, { saved_amount: savedDrafts[goal.id] ?? goal.saved_amount });
    await onRefresh();
  }

  return <div className="space-y-5">
    <section className="goals-hero">
      <div><p className="eyebrow text-teal-900/60">Your next milestone</p><h2 className="mt-1 text-2xl">Save with a purpose</h2><p className="mt-2 max-w-xl text-sm leading-6 text-teal-950/70">Add only your real goals. Progress is calculated from the amounts you enter—Arus never invents savings data.</p></div>
      <Dialog open={open} onOpenChange={setOpen}><DialogTrigger asChild><Button className="bg-teal-800 text-white hover:bg-teal-900"><Plus/>Add goal</Button></DialogTrigger><DialogContent><DialogHeader><DialogTitle>Create a financial goal</DialogTitle><DialogDescription>Choose what you are saving for and enter your real amounts.</DialogDescription></DialogHeader><form onSubmit={submit} className="space-y-4"><div className="space-y-2"><Label htmlFor="goal-name">Goal name</Label><Input id="goal-name" value={name} onChange={(event)=>setName(event.target.value)} placeholder="e.g. Japan trip" required/></div><div className="space-y-2"><Label>Saving for</Label><Select value={purpose} onValueChange={setPurpose}><SelectTrigger><SelectValue/></SelectTrigger><SelectContent>{purposes.map((item)=><SelectItem value={item} key={item}>{item}</SelectItem>)}</SelectContent></Select></div><div className="grid gap-4 sm:grid-cols-2"><div className="space-y-2"><Label htmlFor="goal-target">Target amount (MYR)</Label><Input id="goal-target" type="number" min="0.01" step="0.01" value={target} onChange={(event)=>setTarget(event.target.value)} required/></div><div className="space-y-2"><Label htmlFor="goal-saved">Already saved (MYR)</Label><Input id="goal-saved" type="number" min="0" step="0.01" value={saved} onChange={(event)=>setSaved(event.target.value)} required/></div></div><div className="space-y-2"><Label htmlFor="goal-date">Target date (optional)</Label><Input id="goal-date" type="date" value={date} onChange={(event)=>setDate(event.target.value)}/></div><DialogFooter><Button type="submit" disabled={busy}>{busy?"Saving…":"Save goal"}</Button></DialogFooter></form></DialogContent></Dialog>
    </section>
    {goals.length === 0 ? <article className="empty-surface"><div className="icon-tile warm"><Flag/></div><h2>No goals yet</h2><p>Add the first thing you are genuinely saving for. Nothing is prefilled with fake data.</p><Button variant="outline" onClick={()=>setOpen(true)}><Plus/>Add your first goal</Button></article> : <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{goals.map((goal)=>{const current=Number(goal.saved_amount);const targetAmount=Number(goal.target_amount);const percent=Math.min(100,Math.max(0,targetAmount?current/targetAmount*100:0));return <article className="goal-card" key={goal.id}><div className="flex items-start justify-between gap-3"><div className="goal-icon"><WalletCards/></div><AlertDialog><AlertDialogTrigger asChild><Button variant="ghost" size="icon-sm" aria-label={`Delete ${goal.name}`}><Trash2/></Button></AlertDialogTrigger><AlertDialogContent><AlertDialogHeader><AlertDialogTitle>Delete “{goal.name}”?</AlertDialogTitle><AlertDialogDescription>This removes the goal and its saved progress from Arus.</AlertDialogDescription></AlertDialogHeader><AlertDialogFooter><AlertDialogCancel>Cancel</AlertDialogCancel><AlertDialogAction onClick={()=>void remove(goal.id)} className="bg-rose-700 text-white hover:bg-rose-800">Delete goal</AlertDialogAction></AlertDialogFooter></AlertDialogContent></AlertDialog></div><p className="eyebrow mt-5 text-amber-800">{goal.purpose}</p><h2 className="mt-1 text-xl">{goal.name}</h2><div className="mt-5 flex items-end justify-between gap-3"><div><p className="text-sm text-slate-500">Saved</p><p className="mt-1 text-lg font-bold tabular text-teal-800">{money(goal.saved_amount,goal.currency)}</p></div><p className="text-sm tabular text-slate-500">of {money(goal.target_amount,goal.currency)}</p></div><div className="mt-4 flex gap-2"><Input type="number" min="0" step="0.01" aria-label={"Saved amount for " + goal.name} value={savedDrafts[goal.id] ?? goal.saved_amount} onChange={(event)=>setSavedDrafts((current)=>({...current,[goal.id]:event.target.value}))}/><Button variant="outline" onClick={()=>void updateSaved(goal)}>Update saved</Button></div><div className="mt-4 h-2.5 overflow-hidden rounded-full bg-white/80"><div className="h-full rounded-full bg-teal-700" style={{width:`${percent}%`}}/></div><div className="mt-3 flex items-center justify-between text-sm"><span className="font-semibold text-teal-900">{Math.round(percent)}%</span><span className="flex items-center gap-1.5 text-slate-500"><CalendarDays className="size-4"/>{goal.target_date||"No deadline"}</span></div></article>})}</section>}
  </div>;
}
