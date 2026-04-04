"use client";

import { useEffect, useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  Eye,
  EyeOff,
  Fingerprint,
  Sparkles,
  Star,
  Wand2,
} from "lucide-react";

// ─── Types ───────────────────────────────────────────────────────────────────

export type XdmType =
  | "string"
  | "number"
  | "integer"
  | "boolean"
  | "object"
  | "array"
  | "date"
  | "date-time";

export type XdmFormat = "email" | "uri" | "date" | "date-time" | "uuid" | "phone" | "";

export type IdentityNamespace =
  | "Email"
  | "Phone"
  | "CRM_ID"
  | "ECID"
  | "Cookie_ID"
  | "Mobile_ID"
  | "";

export interface FieldMapping {
  sourceColumn: string;
  sampleValues: string[];
  xdmFieldName: string;
  type: XdmType;
  format: XdmFormat;
  isIdentity: boolean;
  identityNamespace: IdentityNamespace;
  isPrimary: boolean;
  include: boolean;
  autoDetected: boolean;
}

interface DataMappingStepProps {
  file: File;
  onMappingsChange: (mappings: FieldMapping[]) => void;
}

// ─── Constants ───────────────────────────────────────────────────────────────

const XDM_TYPES: XdmType[] = [
  "string", "number", "integer", "boolean", "object", "array", "date", "date-time",
];

const XDM_FORMATS: XdmFormat[] = ["", "email", "uri", "date", "date-time", "uuid", "phone"];

const IDENTITY_NAMESPACES: IdentityNamespace[] = [
  "", "Email", "Phone", "CRM_ID", "ECID", "Cookie_ID", "Mobile_ID",
];

const TYPE_COLORS: Record<XdmType, string> = {
  string: "bg-sky-50 text-sky-700 border-sky-200",
  number: "bg-emerald-50 text-emerald-700 border-emerald-200",
  integer: "bg-teal-50 text-teal-700 border-teal-200",
  boolean: "bg-amber-50 text-amber-700 border-amber-200",
  object: "bg-violet-50 text-violet-700 border-violet-200",
  array: "bg-indigo-50 text-indigo-700 border-indigo-200",
  date: "bg-rose-50 text-rose-700 border-rose-200",
  "date-time": "bg-pink-50 text-pink-700 border-pink-200",
};

// ─── File Parsing ─────────────────────────────────────────────────────────────

function parseCsv(text: string, maxRows = 5): Record<string, string[]> {
  const lines = text.trim().split(/\r?\n/);
  if (lines.length < 2) return {};
  const headers = lines[0].split(",").map((h) => h.trim().replace(/^"|"$/g, ""));
  const result: Record<string, string[]> = {};
  headers.forEach((h) => (result[h] = []));
  for (let i = 1; i <= Math.min(maxRows, lines.length - 1); i++) {
    const cells = lines[i].split(",").map((c) => c.trim().replace(/^"|"$/g, ""));
    headers.forEach((h, idx) => {
      if (cells[idx] !== undefined && cells[idx] !== "") result[h].push(cells[idx]);
    });
  }
  return result;
}

function parseJson(text: string, maxRows = 5): Record<string, string[]> {
  try {
    const parsed = JSON.parse(text);
    const rows: Record<string, unknown>[] = Array.isArray(parsed)
      ? parsed.slice(0, maxRows)
      : [parsed];
    const result: Record<string, string[]> = {};
    rows.forEach((row) => {
      Object.entries(row).forEach(([key, val]) => {
        if (!(key in result)) result[key] = [];
        if (val !== null && val !== undefined && val !== "") {
          result[key].push(String(val));
        }
      });
    });
    return result;
  } catch {
    return {};
  }
}

// ─── Auto-detection ───────────────────────────────────────────────────────────

function toXdmFieldName(col: string): string {
  return col
    .toLowerCase()
    .replace(/\s+/g, "_")
    .replace(/[^a-z0-9_]/g, "")
    .replace(/^(\d)/, "_$1");
}

function autoDetect(col: string, samples: string[]): Pick<FieldMapping, "type" | "format" | "isIdentity" | "identityNamespace" | "isPrimary" | "autoDetected"> {
  const colLower = col.toLowerCase();
  const nonEmpty = samples.filter(Boolean);

  // Email
  if (/email/i.test(col) || nonEmpty.some((s) => /@\w+\.\w+/.test(s))) {
    return { type: "string", format: "email", isIdentity: true, identityNamespace: "Email", isPrimary: false, autoDetected: true };
  }
  // UUID
  if (nonEmpty.some((s) => /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(s))) {
    return { type: "string", format: "uuid", isIdentity: false, identityNamespace: "", isPrimary: false, autoDetected: true };
  }
  // URI / URL
  if (/^url|uri$|link$/.test(colLower) || nonEmpty.some((s) => /^https?:\/\//.test(s))) {
    return { type: "string", format: "uri", isIdentity: false, identityNamespace: "", isPrimary: false, autoDetected: true };
  }
  // DateTime
  if (nonEmpty.some((s) => /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(s)) || /timestamp|datetime|created_at|updated_at/i.test(col)) {
    return { type: "string", format: "date-time", isIdentity: false, identityNamespace: "", isPrimary: false, autoDetected: true };
  }
  // Epoch ms / s
  if (nonEmpty.every((s) => /^\d{10,13}$/.test(s)) && /time|date|ts/i.test(col)) {
    return { type: "string", format: "date-time", isIdentity: false, identityNamespace: "", isPrimary: false, autoDetected: true };
  }
  // Date
  if (nonEmpty.some((s) => /^\d{4}-\d{2}-\d{2}$/.test(s)) || /^date$|birth_?date|expir/i.test(col)) {
    return { type: "string", format: "date", isIdentity: false, identityNamespace: "", isPrimary: false, autoDetected: true };
  }
  // Boolean
  if (nonEmpty.length > 0 && nonEmpty.every((s) => /^(true|false|0|1|yes|no)$/i.test(s))) {
    return { type: "boolean", format: "", isIdentity: false, identityNamespace: "", isPrimary: false, autoDetected: true };
  }
  // Phone
  if (/phone|tel|mobile|cell/i.test(col)) {
    return { type: "string", format: "phone", isIdentity: true, identityNamespace: "Phone", isPrimary: false, autoDetected: true };
  }
  // CRM ID
  if (/crm.?id|customer.?id|user.?id|member.?id|account.?id/i.test(col)) {
    return { type: "string", format: "", isIdentity: true, identityNamespace: "CRM_ID", isPrimary: false, autoDetected: true };
  }
  // Number (all numeric samples)
  if (nonEmpty.length > 0 && nonEmpty.every((s) => !isNaN(Number(s)))) {
    const hasDecimal = nonEmpty.some((s) => s.includes("."));
    return { type: hasDecimal ? "number" : "integer", format: "", isIdentity: false, identityNamespace: "", isPrimary: false, autoDetected: true };
  }
  // Default: string
  return { type: "string", format: "", isIdentity: false, identityNamespace: "", isPrimary: false, autoDetected: true };
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function TypeSelect({
  value,
  onChange,
}: {
  value: XdmType;
  onChange: (v: XdmType) => void;
}) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as XdmType)}
        className={`h-7 w-full appearance-none rounded-md border px-2 pr-6 text-xs font-mono font-medium focus:outline-none focus:ring-1 focus:ring-primary/60 ${TYPE_COLORS[value]}`}
      >
        {XDM_TYPES.map((t) => (
          <option key={t} value={t}>
            {t}
          </option>
        ))}
      </select>
      <ChevronDown className="pointer-events-none absolute right-1.5 top-1.5 h-3.5 w-3.5 opacity-50" />
    </div>
  );
}

function FormatSelect({ value, onChange }: { value: XdmFormat; onChange: (v: XdmFormat) => void }) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as XdmFormat)}
        className="h-7 w-full appearance-none rounded-md border border-gray-200 bg-gray-50 px-2 pr-6 text-xs font-mono text-gray-600 focus:outline-none focus:ring-1 focus:ring-primary/60"
      >
        {XDM_FORMATS.map((f) => (
          <option key={f} value={f}>
            {f || "—"}
          </option>
        ))}
      </select>
      <ChevronDown className="pointer-events-none absolute right-1.5 top-1.5 h-3.5 w-3.5 opacity-40" />
    </div>
  );
}

function NamespaceSelect({
  value,
  onChange,
}: {
  value: IdentityNamespace;
  onChange: (v: IdentityNamespace) => void;
}) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as IdentityNamespace)}
        className="h-7 w-full appearance-none rounded-md border border-violet-200 bg-violet-50 px-2 pr-6 text-xs font-mono text-violet-700 focus:outline-none focus:ring-1 focus:ring-primary/60"
      >
        {IDENTITY_NAMESPACES.map((ns) => (
          <option key={ns} value={ns}>
            {ns || "namespace…"}
          </option>
        ))}
      </select>
      <ChevronDown className="pointer-events-none absolute right-1.5 top-1.5 h-3.5 w-3.5 opacity-40" />
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function DataMappingStep({ file, onMappingsChange }: DataMappingStepProps) {
  const [mappings, setMappings] = useState<FieldMapping[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingField, setEditingField] = useState<string | null>(null);

  // Parse file on mount
  useEffect(() => {
    setLoading(true);
    setError(null);
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const text = e.target?.result as string;
        const raw = file.name.endsWith(".csv") ? parseCsv(text) : parseJson(text);
        const cols = Object.keys(raw);
        if (cols.length === 0) {
          setError("No columns detected. Ensure your file has headers.");
          setLoading(false);
          return;
        }
        const initial: FieldMapping[] = cols.map((col) => ({
          sourceColumn: col,
          sampleValues: raw[col].slice(0, 3),
          xdmFieldName: toXdmFieldName(col),
          include: true,
          ...autoDetect(col, raw[col]),
        }));
        // Set first CRM_ID or Email as primary
        const firstIdentity = initial.find((m) => m.isIdentity && m.identityNamespace === "Email")
          ?? initial.find((m) => m.isIdentity && m.identityNamespace === "CRM_ID")
          ?? initial.find((m) => m.isIdentity);
        if (firstIdentity) firstIdentity.isPrimary = true;

        setMappings(initial);
        onMappingsChange(initial);
      } catch {
        setError("Failed to parse file.");
      }
      setLoading(false);
    };
    reader.onerror = () => {
      setError("Could not read file.");
      setLoading(false);
    };
    reader.readAsText(file);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [file]);

  const update = (sourceColumn: string, patch: Partial<FieldMapping>) => {
    setMappings((prev) => {
      let next = prev.map((m) =>
        m.sourceColumn === sourceColumn ? { ...m, ...patch, autoDetected: false } : m
      );
      // enforce single primary
      if (patch.isPrimary) {
        next = next.map((m) =>
          m.sourceColumn !== sourceColumn ? { ...m, isPrimary: false } : m
        );
      }
      onMappingsChange(next);
      return next;
    });
  };

  const redetectAll = () => {
    setMappings((prev) => {
      const next = prev.map((m) => ({
        ...m,
        ...autoDetect(m.sourceColumn, m.sampleValues),
      }));
      // re-assign primary
      const firstId = next.find((m) => m.isIdentity && m.identityNamespace === "Email")
        ?? next.find((m) => m.isIdentity);
      if (firstId) {
        next.forEach((m) => (m.isPrimary = m.sourceColumn === firstId.sourceColumn));
      }
      onMappingsChange(next);
      return next;
    });
  };

  const stats = useMemo(() => ({
    total: mappings.length,
    included: mappings.filter((m) => m.include).length,
    identities: mappings.filter((m) => m.include && m.isIdentity).length,
    primary: mappings.find((m) => m.isPrimary)?.sourceColumn ?? "—",
  }), [mappings]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="flex flex-col items-center gap-3 text-muted-foreground">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <span className="text-sm font-mono">Parsing {file.name}…</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
        <AlertCircle className="h-4 w-4 shrink-0" />
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-gray-200 bg-gray-50/70 px-4 py-2.5">
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <span className="font-mono font-semibold text-foreground">{stats.included}</span>
            <span>/ {stats.total} fields included</span>
          </span>
          <span className="h-3 w-px bg-gray-300" />
          <span className="flex items-center gap-1.5">
            <Fingerprint className="h-3.5 w-3.5 text-violet-500" />
            <span className="font-mono font-semibold text-foreground">{stats.identities}</span>
            <span>identit{stats.identities === 1 ? "y" : "ies"}</span>
          </span>
          <span className="h-3 w-px bg-gray-300" />
          <span className="flex items-center gap-1.5">
            <Star className="h-3.5 w-3.5 text-amber-500" />
            <span>Primary:</span>
            <span className="font-mono font-medium text-foreground">{stats.primary}</span>
          </span>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={redetectAll}
          className="h-7 gap-1.5 border-primary/30 text-xs text-primary hover:bg-primary/5"
        >
          <Wand2 className="h-3.5 w-3.5" />
          Re-detect all
        </Button>
      </div>

      {/* Mapping table */}
      <div className="rounded-lg border border-gray-200 overflow-hidden">
        {/* Table header */}
        <div className="grid grid-cols-[1fr_1fr_1fr_1fr_auto_auto] gap-x-3 border-b border-gray-200 bg-gray-50 px-4 py-2 text-[10px] font-semibold uppercase tracking-widest text-gray-400">
          <span>Source column</span>
          <span>XDM field name</span>
          <span>Type / Format</span>
          <span>Identity</span>
          <span className="text-center">Primary</span>
          <span className="text-center">Include</span>
        </div>

        {/* Rows */}
        <div className="divide-y divide-gray-100">
          {mappings.map((m) => {
            const isEditing = editingField === m.sourceColumn;
            const rowMuted = !m.include;

            return (
              <div
                key={m.sourceColumn}
                className={`grid grid-cols-[1fr_1fr_1fr_1fr_auto_auto] items-center gap-x-3 px-4 py-2.5 transition-colors ${
                  rowMuted ? "bg-gray-50/50 opacity-50" : isEditing ? "bg-primary/[0.03]" : "hover:bg-gray-50/60"
                }`}
                onClick={() => !rowMuted && setEditingField(isEditing ? null : m.sourceColumn)}
              >
                {/* Source column */}
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="truncate font-mono text-xs font-medium text-gray-800">
                      {m.sourceColumn}
                    </span>
                    {m.autoDetected && (
                      <span title="Auto-detected">
                        <Sparkles className="h-3 w-3 shrink-0 text-amber-400" />
                      </span>
                    )}
                  </div>
                  {m.sampleValues.length > 0 && (
                    <div className="mt-0.5 truncate font-mono text-[10px] text-gray-400">
                      {m.sampleValues.map((v, i) => (
                        <span key={i}>
                          {i > 0 && <span className="mx-0.5 text-gray-300">·</span>}
                          {v}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* XDM field name */}
                <div onClick={(e) => e.stopPropagation()}>
                  <Input
                    value={m.xdmFieldName}
                    onChange={(e) => update(m.sourceColumn, { xdmFieldName: e.target.value })}
                    disabled={rowMuted}
                    className="h-7 border-gray-200 font-mono text-xs focus-visible:ring-primary/50"
                    placeholder="field_name"
                  />
                </div>

                {/* Type / Format */}
                <div className="flex flex-col gap-1.5" onClick={(e) => e.stopPropagation()}>
                  <TypeSelect
                    value={m.type}
                    onChange={(v) => update(m.sourceColumn, { type: v })}
                  />
                  <FormatSelect
                    value={m.format}
                    onChange={(v) => update(m.sourceColumn, { format: v })}
                  />
                </div>

                {/* Identity */}
                <div className="flex flex-col gap-1.5" onClick={(e) => e.stopPropagation()}>
                  <button
                    type="button"
                    disabled={rowMuted}
                    onClick={() =>
                      update(m.sourceColumn, {
                        isIdentity: !m.isIdentity,
                        identityNamespace: !m.isIdentity ? "Email" : "",
                        isPrimary: false,
                      })
                    }
                    className={`flex h-7 items-center gap-1.5 rounded-md border px-2 text-xs transition-colors ${
                      m.isIdentity
                        ? "border-violet-300 bg-violet-50 text-violet-700"
                        : "border-gray-200 bg-white text-gray-400 hover:border-gray-300"
                    }`}
                  >
                    <Fingerprint className="h-3.5 w-3.5" />
                    {m.isIdentity ? "Identity" : "Not identity"}
                  </button>
                  {m.isIdentity && (
                    <NamespaceSelect
                      value={m.identityNamespace}
                      onChange={(v) => update(m.sourceColumn, { identityNamespace: v })}
                    />
                  )}
                </div>

                {/* Primary star */}
                <div className="flex justify-center" onClick={(e) => e.stopPropagation()}>
                  <button
                    type="button"
                    disabled={rowMuted || !m.isIdentity}
                    onClick={() => update(m.sourceColumn, { isPrimary: !m.isPrimary })}
                    title={m.isIdentity ? "Set as primary identity" : "Must be identity first"}
                    className={`rounded p-1 transition-colors ${
                      m.isPrimary
                        ? "text-amber-500"
                        : m.isIdentity
                        ? "text-gray-300 hover:text-amber-400"
                        : "cursor-not-allowed text-gray-200"
                    }`}
                  >
                    <Star className={`h-4 w-4 ${m.isPrimary ? "fill-amber-500" : ""}`} />
                  </button>
                </div>

                {/* Include toggle */}
                <div className="flex justify-center" onClick={(e) => e.stopPropagation()}>
                  <button
                    type="button"
                    onClick={() => update(m.sourceColumn, { include: !m.include })}
                    className={`rounded p-1 transition-colors ${
                      m.include
                        ? "text-gray-400 hover:text-gray-600"
                        : "text-gray-300 hover:text-gray-500"
                    }`}
                    title={m.include ? "Exclude this field" : "Include this field"}
                  >
                    {m.include ? (
                      <Eye className="h-4 w-4" />
                    ) : (
                      <EyeOff className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Validation hints */}
      {stats.identities > 0 && !mappings.find((m) => m.include && m.isPrimary) && (
        <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2.5 text-xs text-amber-800">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
          <span>
            You have identity fields but no <strong>primary identity</strong> set. Click the{" "}
            <Star className="inline h-3 w-3 fill-amber-500 text-amber-500" /> star on an identity
            field to mark it as primary (required for Profile schemas).
          </span>
        </div>
      )}
      {stats.identities === 0 && (
        <div className="flex items-start gap-2 rounded-md border border-sky-200 bg-sky-50 px-3 py-2.5 text-xs text-sky-800">
          <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-sky-500" />
          <span>
            No identity fields detected. Toggle the <strong>Identity</strong> button on fields like
            email or customer ID to enable Profile stitching.
          </span>
        </div>
      )}
      {mappings.find((m) => m.include && m.isPrimary) && (
        <div className="flex items-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
          <span>
            Mapping looks good — primary identity is{" "}
            <strong className="font-mono">{mappings.find((m) => m.isPrimary)?.xdmFieldName}</strong>{" "}
            ({mappings.find((m) => m.isPrimary)?.identityNamespace}).
          </span>
        </div>
      )}
    </div>
  );
}

// ─── Compact summary badge (for review step) ─────────────────────────────────

export function MappingSummaryBadges({ mappings }: { mappings: FieldMapping[] }) {
  const included = mappings.filter((m) => m.include);
  return (
    <div className="flex flex-wrap gap-1.5">
      {included.map((m) => (
        <Badge
          key={m.sourceColumn}
          variant="outline"
          className={`gap-1 font-mono text-[10px] ${TYPE_COLORS[m.type]}`}
        >
          {m.isPrimary && <Star className="h-2.5 w-2.5 fill-current" />}
          {m.isIdentity && !m.isPrimary && <Fingerprint className="h-2.5 w-2.5" />}
          {m.xdmFieldName}
          <span className="opacity-60">:{m.type}</span>
        </Badge>
      ))}
    </div>
  );
}
