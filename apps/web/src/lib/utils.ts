import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: number | string | null | undefined, currency = 'USD') {
  if (value === null || value === undefined) return '—';
  const n = typeof value === 'string' ? parseFloat(value) : value;
  if (Number.isNaN(n)) return '—';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 0 }).format(n);
}

export function formatNumber(value: number | string | null | undefined) {
  if (value === null || value === undefined) return '—';
  const n = typeof value === 'string' ? parseFloat(value) : value;
  if (Number.isNaN(n)) return '—';
  return new Intl.NumberFormat('en-US').format(n);
}

export function formatPercent(value: number | string | null | undefined, decimals = 2) {
  if (value === null || value === undefined) return '—';
  const n = typeof value === 'string' ? parseFloat(value) : value;
  if (Number.isNaN(n)) return '—';
  return `${n.toFixed(decimals)}%`;
}

export const CAMPAIGN_STATUSES = [
  'BRIEF',
  'CONTACTANDO',
  'PLAN_DE_CUENTAS',
  'PULL',
  'CAMPAÑA INTERNA',
  'REPORTE',
  'TERMINADA',
  'CANCELADA',
  'PAUSADA',
] as const;

export const CAMPAIGN_OBJECTIVES = [
  'AWARENESS',
  'CONSIDERACION',
  'CONVERSION',
  'GESTION_DE_CRISIS',
  'BRANDING',
  'LANZAMIENTO',
  'RETENCION',
] as const;

export const INFLUENCER_TIERS = ['NANO', 'MICRO', 'MID', 'MACRO', 'MEGA', 'MIX'] as const;

export const STATUS_COLORS: Record<string, string> = {
  BRIEF: 'bg-slate-100 text-slate-700 border-slate-300',
  CONTACTANDO: 'bg-blue-100 text-blue-700 border-blue-300',
  PLAN_DE_CUENTAS: 'bg-purple-100 text-purple-700 border-purple-300',
  PULL: 'bg-amber-100 text-amber-700 border-amber-300',
  'CAMPAÑA INTERNA': 'bg-indigo-100 text-indigo-700 border-indigo-300',
  REPORTE: 'bg-cyan-100 text-cyan-700 border-cyan-300',
  TERMINADA: 'bg-emerald-100 text-emerald-700 border-emerald-300',
  CANCELADA: 'bg-rose-100 text-rose-700 border-rose-300',
  PAUSADA: 'bg-orange-100 text-orange-700 border-orange-300',
};

export const OBJECTIVE_COLORS: Record<string, string> = {
  AWARENESS: 'bg-blue-50 text-blue-700',
  CONSIDERACION: 'bg-purple-50 text-purple-700',
  CONVERSION: 'bg-emerald-50 text-emerald-700',
  GESTION_DE_CRISIS: 'bg-rose-50 text-rose-700',
  BRANDING: 'bg-indigo-50 text-indigo-700',
  LANZAMIENTO: 'bg-amber-50 text-amber-700',
  RETENCION: 'bg-cyan-50 text-cyan-700',
};