/**
 * jobAdapter.ts — backend → OotoCV reference shape.
 *
 * The OotoCV reference (`references/ootocv_src 2/src/data/jobs.ts`) carries
 * a flat `Job` shape with `role`, `verdict` (uppercase 4-way), `verdictReason`,
 * `redFlags[]`, `strengths[]`, `gaps[]` (with severity + strategy), and
 * `matchScore` (0–4). Our backend keeps these split across `Job`,
 * `Evaluation`, and `ParseResult` rows and uses lowercase `recommended_action`
 * values. This module collapses the three into the reference shape so the
 * ported pages don't need to know about the split.
 *
 * Field mapping
 *
 *   reference          ← backend source
 *   ─────────────────────────────────────────────────────────────
 *   id                 ← Job.id
 *   role               ← Job.title
 *   company            ← Job.company_name
 *   location           ← Job.location
 *   postedAt           ← formatTimeAgo(Job.posted_at)
 *   verdict            ← Evaluation.recommended_action (uppercased
 *                          and mapped: tailor → TAILOR, apply/apply_direct
 *                          → APPLY DIRECT, borderline → BORDERLINE, skip → SKIP)
 *   verdictReason      ← Evaluation.wit_line || Evaluation.summary
 *   redFlags           ← Evaluation.red_flags (em-dash format preserved;
 *                          backend normalizes hyphens on write — R6)
 *   strengths          ← derived from Evaluation.matched_keywords +
 *                          interview_tips.your_strengths_to_highlight
 *                          (typed as 'req met' / 'signal' for keyword vs
 *                          narrative entries)
 *   gaps               ← Evaluation.gaps.technical + .domain + .soft_skills
 *                          with severity bucketed from match_score band and
 *                          strategy derived from improvement_suggestions when
 *                          available; falls back to a single-word fallback
 *                          when the evaluator hasn't been redeployed yet
 *   summary            ← Evaluation.summary
 *   matchScore         ← Math.round(Evaluation.job_match_score / 25), clamp 0..4
 *   originalUrl        ← Job.job_url || Job.apply_url
 *
 * Note: `top_strength`, `deciding_factor`, `kill_shot` are NOT consumed by
 * the reference (it composes its own one-liners from strengths/gaps). They
 * remain in the API client for future use.
 */
import type { Evaluation, Job as BackendJob } from './apiClient';
import type { JobWithEvaluation } from './jobService';
import { formatTimeAgo } from '../utils/format';

// ─── Reference shape, mirrors references/ootocv_src 2/src/data/jobs.ts ────────

export type ReferenceVerdict = 'TAILOR' | 'SKIP' | 'BORDERLINE' | 'APPLY DIRECT';
export type ReferenceStrengthType = 'req met' | 'evidence' | 'signal';
export type ReferenceGapSeverity = 'minor' | 'notable' | 'significant';

export interface ReferenceStrength {
    text: string;
    type: ReferenceStrengthType;
}

export interface ReferenceGap {
    text: string;
    severity: ReferenceGapSeverity;
    /** One-line OotoCV-voice instruction. */
    strategy: string;
}

export interface ReferenceJob {
    id: string;
    role: string;
    company: string;
    location: string;
    postedAt: string;
    verdict: ReferenceVerdict;
    verdictReason: string;
    redFlags: string[];
    strengths?: ReferenceStrength[];
    gaps?: ReferenceGap[];
    summary?: string;
    /** Integer 0–4 — maps to the four signal dots in MatchBrief. */
    matchScore?: number;
    originalUrl?: string;
}

// ─── Mapping helpers ─────────────────────────────────────────────────────────

function mapVerdict(action: Evaluation['recommended_action'] | undefined): ReferenceVerdict {
    if (action === 'apply' || action === 'apply_direct') return 'APPLY DIRECT';
    if (action === 'borderline') return 'BORDERLINE';
    if (action === 'skip') return 'SKIP';
    // Default for null / 'tailor' / anything unexpected. Defaulting to
    // TAILOR keeps the feed showing the job as actionable rather than
    // dropping it; the user can still skip it.
    return 'TAILOR';
}

function clampScore(raw: number | null | undefined): number {
    if (typeof raw !== 'number' || !Number.isFinite(raw)) return 0;
    // Backend stores 0–100 in steps of 10. Reference uses 0–4 dots.
    return Math.max(0, Math.min(4, Math.round(raw / 25)));
}

function severityFromScore(score: number | null | undefined): ReferenceGapSeverity {
    const n = score ?? 0;
    if (n >= 70) return 'minor';
    if (n >= 40) return 'notable';
    return 'significant';
}

function buildStrengths(eval_: Evaluation): ReferenceStrength[] {
    const out: ReferenceStrength[] = [];
    // Matched keywords are concrete requirement evidence (req met).
    for (const kw of (eval_.matched_keywords ?? []).slice(0, 4)) {
        if (kw && typeof kw === 'string') {
            out.push({ text: kw, type: 'req met' });
        }
    }
    // Narrative strengths from interview prep.
    const narrative = eval_.interview_tips?.your_strengths_to_highlight ?? [];
    for (const s of narrative.slice(0, 3)) {
        if (s && typeof s === 'string') {
            out.push({ text: s, type: 'evidence' });
        }
    }
    return out;
}

function buildGaps(eval_: Evaluation): ReferenceGap[] {
    const out: ReferenceGap[] = [];
    const severity = severityFromScore(eval_.job_match_score);
    const sources: Array<{ items: string[] | undefined; sev?: ReferenceGapSeverity }> = [
        { items: eval_.gaps?.technical,    sev: severity },
        // Domain gaps tend to be more situational; default to one band softer.
        { items: eval_.gaps?.domain,       sev: severity === 'significant' ? 'notable' : 'minor' },
        { items: eval_.gaps?.soft_skills,  sev: 'minor' },
    ];

    // Strategy lookup from improvement_suggestions.resume_edits: match by
    // substring so a gap like "No Kubernetes" can pick up an edit suggestion
    // that mentions "kubernetes". Falls back to a generic imperative.
    const edits = eval_.improvement_suggestions?.resume_edits ?? [];
    const findStrategy = (text: string): string => {
        const lower = text.toLowerCase();
        for (const edit of edits) {
            const target = `${edit.area ?? ''} ${edit.suggestion ?? ''}`.toLowerCase();
            const keywords = lower.split(/\s+/).filter(w => w.length > 4);
            if (keywords.some(k => target.includes(k))) {
                return edit.suggestion ?? `Address it head-on in your tailoring.`;
            }
        }
        return `Address it head-on in your tailoring.`;
    };

    for (const { items, sev } of sources) {
        for (const text of (items ?? []).slice(0, 3)) {
            if (text && typeof text === 'string') {
                out.push({
                    text,
                    severity: sev ?? severity,
                    strategy: findStrategy(text),
                });
            }
        }
    }
    // Cap at 6 so the brief doesn't get too long.
    return out.slice(0, 6);
}

/** Backend job + evaluation → reference Job shape. */
export function toReferenceJob(
    job: BackendJob | JobWithEvaluation,
    overrideEvaluation?: Evaluation | null,
): ReferenceJob {
    const eval_ =
        overrideEvaluation
        ?? ('evaluation' in job ? job.evaluation : null)
        ?? null;

    const verdict = mapVerdict(eval_?.recommended_action ?? null);
    const verdictReason =
        eval_?.wit_line
        || eval_?.summary
        || 'No evaluation yet.';

    return {
        id: job.id,
        role: job.title ?? 'Untitled role',
        company: job.company_name ?? 'Unknown company',
        location: job.location ?? '',
        postedAt: formatTimeAgo(job.posted_at) || 'recently',
        verdict,
        verdictReason,
        redFlags: Array.isArray(eval_?.red_flags) ? eval_!.red_flags as string[] : [],
        strengths: eval_ ? buildStrengths(eval_) : undefined,
        gaps: eval_ ? buildGaps(eval_) : undefined,
        summary: eval_?.summary ?? undefined,
        matchScore: clampScore(eval_?.job_match_score),
        originalUrl: job.job_url ?? undefined,
    };
}
