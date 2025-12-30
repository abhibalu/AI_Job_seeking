import React, { useState } from 'react';
import { Evaluation, ParseResult } from '../services/apiClient';
import { parseJobDescription, getParsedJD } from '../services/jobService';
import {
  X, CheckCircle, AlertTriangle, XCircle, User, FileText,
  Lightbulb, Target, MessageSquare, Sparkles, ChevronDown, ChevronUp,
  BookOpen, Zap, HelpCircle, ExternalLink
} from 'lucide-react';
import { GlassCard } from './GlassCard';

interface JobModalProps {
  evaluation: Evaluation | null;
  onClose: () => void;
  onEvaluate?: () => void;
  isEvaluating?: boolean;
}

export const JobModal: React.FC<JobModalProps> = ({ evaluation, onClose, onEvaluate, isEvaluating }) => {
  const [parsedJD, setParsedJD] = useState<ParseResult | null>(null);
  const [isParsing, setIsParsing] = useState(false);
  const [showInterviewTips, setShowInterviewTips] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);

  if (!evaluation) return null;

  const handleParseJD = async () => {
    setIsParsing(true);
    try {
      await parseJobDescription(evaluation.job_id, false);
      const result = await getParsedJD(evaluation.job_id);
      setParsedJD(result);
    } catch (error) {
      console.error('Failed to parse JD:', error);
    } finally {
      setIsParsing(false);
    }
  };

  const getScoreColor = (score: number | null) => {
    if (!score) return 'text-slate-400';
    if (score >= 80) return 'text-emerald-600';
    if (score >= 50) return 'text-amber-600';
    return 'text-rose-600';
  };

  const getActionColor = (action: string | null) => {
    switch (action) {
      case 'apply': return 'bg-emerald-500 text-white';
      case 'tailor': return 'bg-amber-500 text-white';
      case 'skip': return 'bg-rose-500 text-white';
      default: return 'bg-slate-200 text-slate-600';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-slate-900/20 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      <GlassCard className="w-full max-w-5xl max-h-[90vh] overflow-y-auto z-20 animate-in fade-in zoom-in duration-200 bg-white/90 shadow-2xl">

        {/* Header */}
        <div className="sticky top-0 z-30 flex justify-between items-center p-6 border-b border-slate-200/60 bg-white/80 backdrop-blur-xl">
          <div className="flex items-center space-x-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-slate-800 to-slate-900 flex items-center justify-center text-white font-bold text-2xl shadow-lg">
              {(evaluation.company_name || 'U').substring(0, 1)}
            </div>
            <div>
              <h2 className="text-2xl font-bold text-slate-900">{evaluation.title_role || 'Untitled Position'}</h2>
              <p className="text-slate-500 font-medium">{evaluation.company_name || 'Unknown Company'}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-full hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Left Column: Stats & Actions */}
          <div className="space-y-6">

            {/* Score Card */}
            <div className="bg-slate-50 rounded-xl p-5 border border-slate-200">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Match Score</h3>
              <div className="flex items-end space-x-2">
                <span className={`text-5xl font-bold ${getScoreColor(evaluation.job_match_score)}`}>
                  {evaluation.job_match_score || '—'}
                </span>
                <span className="text-xl text-slate-400 mb-1">/100</span>
              </div>
              <div className="mt-2 flex items-center space-x-2">
                <span className={`text-sm font-medium px-2 py-1 rounded ${evaluation.verdict === 'Strong Match' ? 'bg-emerald-100 text-emerald-700' :
                  evaluation.verdict === 'Moderate Match' ? 'bg-amber-100 text-amber-700' :
                    'bg-rose-100 text-rose-700'
                  }`}>
                  {evaluation.verdict || 'Unknown'}
                </span>
              </div>
            </div>

            {/* Recommended Action */}
            <div className="bg-slate-50 rounded-xl p-5 border border-slate-200">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">Recommended Action</h3>
              <div className={`text-center py-3 rounded-xl font-bold text-lg uppercase tracking-wide ${getActionColor(evaluation.recommended_action)}`}>
                {evaluation.recommended_action || 'Unknown'}
              </div>
            </div>

            {/* Details Card */}
            <div className="bg-slate-50 rounded-xl p-5 border border-slate-200 space-y-4">
              <div>
                <h4 className="text-xs font-bold text-slate-400 uppercase mb-1">Experience Required</h4>
                <p className="text-slate-800 font-medium">{evaluation.required_exp || 'Not specified'}</p>
              </div>
              {evaluation.evaluated_at && (
                <div>
                  <h4 className="text-xs font-bold text-slate-400 uppercase mb-1">Evaluated</h4>
                  <p className="text-slate-600 text-sm">
                    {new Date(evaluation.evaluated_at).toLocaleDateString()}
                  </p>
                </div>
              )}
            </div>

            {/* Job URL/Link */}
            {evaluation.job_url && (
              <div className="bg-slate-50 rounded-xl p-5 border border-slate-200">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Job Link</h3>
                <a
                  href={evaluation.job_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center text-blue-600 hover:text-blue-800 font-medium transition-colors"
                >
                  View Posting <ExternalLink className="w-4 h-4 ml-2" />
                </a>
              </div>
            )}

            {/* Parse JD Button */}
            <button
              onClick={handleParseJD}
              disabled={isParsing}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-medium transition-all shadow-lg hover:shadow-xl disabled:opacity-50 flex items-center justify-center"
            >
              {isParsing ? (
                <>
                  <div className="w-4 h-4 mr-2 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Parsing JD...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-2" />
                  Parse Job Description
                </>
              )}
            </button>

          </div>

          {/* Right Column: Analysis */}
          <div className="lg:col-span-2 space-y-6">

            {/* Summary */}
            <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm">
              <h3 className="text-lg font-semibold text-slate-900 mb-3 flex items-center">
                <FileText className="w-5 h-5 mr-2 text-blue-600" />
                Executive Summary
              </h3>
              <p className="text-slate-600 leading-relaxed">
                {evaluation.summary || 'No summary available'}
              </p>
            </div>

            {/* Keywords Section */}
            <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm">
              <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center">
                <Target className="w-5 h-5 mr-2 text-purple-600" />
                ATS Keywords
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Matched Keywords */}
                <div className="bg-emerald-50 rounded-lg p-4 border border-emerald-100">
                  <h4 className="text-sm font-semibold text-emerald-700 mb-2 flex items-center">
                    <CheckCircle className="w-4 h-4 mr-1" />
                    Matched ({evaluation.matched_keywords?.length || 0})
                  </h4>
                  <div className="flex flex-wrap gap-1.5">
                    {evaluation.matched_keywords?.map((kw, i) => (
                      <span key={i} className="text-xs bg-emerald-100 text-emerald-700 px-2 py-1 rounded-md">
                        {kw}
                      </span>
                    )) || <span className="text-sm text-slate-400">None</span>}
                  </div>
                </div>

                {/* Missing Keywords */}
                <div className="bg-rose-50 rounded-lg p-4 border border-rose-100">
                  <h4 className="text-sm font-semibold text-rose-700 mb-2 flex items-center">
                    <XCircle className="w-4 h-4 mr-1" />
                    Missing ({evaluation.missing_keywords?.length || 0})
                  </h4>
                  <div className="flex flex-wrap gap-1.5">
                    {evaluation.missing_keywords?.map((kw, i) => (
                      <span key={i} className="text-xs bg-rose-100 text-rose-700 px-2 py-1 rounded-md">
                        {kw}
                      </span>
                    )) || <span className="text-sm text-slate-400">None</span>}
                  </div>
                </div>
              </div>
            </div>

            {/* Gaps Analysis */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

              {/* Technical Gaps */}
              <div className="bg-rose-50/80 rounded-xl p-5 border border-rose-100">
                <h4 className="text-rose-700 font-medium mb-3 flex items-center">
                  <XCircle className="w-4 h-4 mr-2" />
                  Technical Gaps
                </h4>
                {evaluation.gaps?.technical && evaluation.gaps.technical.length > 0 ? (
                  <ul className="space-y-2">
                    {evaluation.gaps.technical.map((gap, i) => (
                      <li key={i} className="text-sm text-rose-800/80 flex items-start">
                        <span className="mr-2">•</span> {gap}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-400">No technical gaps</p>
                )}
              </div>

              {/* Domain Gaps */}
              <div className="bg-blue-50/80 rounded-xl p-5 border border-blue-100">
                <h4 className="text-blue-700 font-medium mb-3 flex items-center">
                  <BookOpen className="w-4 h-4 mr-2" />
                  Domain Gaps
                </h4>
                {evaluation.gaps?.domain && evaluation.gaps.domain.length > 0 ? (
                  <ul className="space-y-2">
                    {evaluation.gaps.domain.map((gap, i) => (
                      <li key={i} className="text-sm text-blue-800/80 flex items-start">
                        <span className="mr-2">•</span> {gap}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-400">No domain gaps</p>
                )}
              </div>

              {/* Soft Skill Gaps */}
              <div className="bg-amber-50/80 rounded-xl p-5 border border-amber-100">
                <h4 className="text-amber-700 font-medium mb-3 flex items-center">
                  <AlertTriangle className="w-4 h-4 mr-2" />
                  Soft Skill Gaps
                </h4>
                {evaluation.gaps?.soft_skills && evaluation.gaps.soft_skills.length > 0 ? (
                  <ul className="space-y-2">
                    {evaluation.gaps.soft_skills.map((gap, i) => (
                      <li key={i} className="text-sm text-amber-800/80 flex items-start">
                        <span className="mr-2">•</span> {gap}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-400">No soft skill gaps</p>
                )}
              </div>
            </div>

            {/* Interview Tips (Collapsible) */}
            {evaluation.interview_tips && (
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                <button
                  onClick={() => setShowInterviewTips(!showInterviewTips)}
                  className="w-full p-5 flex items-center justify-between hover:bg-slate-50 transition-colors"
                >
                  <h3 className="text-lg font-semibold text-slate-900 flex items-center">
                    <Lightbulb className="w-5 h-5 mr-2 text-yellow-500" />
                    Interview Tips
                  </h3>
                  {showInterviewTips ? <ChevronUp className="w-5 h-5 text-slate-400" /> : <ChevronDown className="w-5 h-5 text-slate-400" />}
                </button>

                {showInterviewTips && (
                  <div className="p-5 pt-0 space-y-4">
                    {/* High Priority Topics */}
                    {evaluation.interview_tips.high_priority_topics && evaluation.interview_tips.high_priority_topics.length > 0 && (
                      <div>
                        <h4 className="text-sm font-bold text-slate-700 mb-2 flex items-center">
                          <Zap className="w-4 h-4 mr-1 text-orange-500" />
                          High Priority Topics
                        </h4>
                        <div className="space-y-3">
                          {evaluation.interview_tips.high_priority_topics.map((topic, i) => (
                            <div key={i} className="bg-slate-50 rounded-lg p-3 border border-slate-100">
                              <p className="font-medium text-slate-800">{topic.topic}</p>
                              <p className="text-sm text-slate-500 mt-1">{topic.why}</p>
                              <p className="text-sm text-blue-600 mt-1">📚 {topic.prep}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Strengths to Highlight */}
                    {evaluation.interview_tips.your_strengths_to_highlight && evaluation.interview_tips.your_strengths_to_highlight.length > 0 && (
                      <div>
                        <h4 className="text-sm font-bold text-slate-700 mb-2">✨ Your Strengths to Highlight</h4>
                        <ul className="space-y-1">
                          {evaluation.interview_tips.your_strengths_to_highlight.map((s, i) => (
                            <li key={i} className="text-sm text-slate-600">• {s}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Questions to Ask */}
                    {evaluation.interview_tips.questions_to_ask && evaluation.interview_tips.questions_to_ask.length > 0 && (
                      <div>
                        <h4 className="text-sm font-bold text-slate-700 mb-2 flex items-center">
                          <HelpCircle className="w-4 h-4 mr-1 text-purple-500" />
                          Questions to Ask
                        </h4>
                        <ul className="space-y-1">
                          {evaluation.interview_tips.questions_to_ask.map((q, i) => (
                            <li key={i} className="text-sm text-slate-600">• {q}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Resume Suggestions (Collapsible) */}
            {evaluation.improvement_suggestions && (
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                <button
                  onClick={() => setShowSuggestions(!showSuggestions)}
                  className="w-full p-5 flex items-center justify-between hover:bg-slate-50 transition-colors"
                >
                  <h3 className="text-lg font-semibold text-slate-900 flex items-center">
                    <MessageSquare className="w-5 h-5 mr-2 text-green-500" />
                    Resume Improvement Suggestions
                  </h3>
                  {showSuggestions ? <ChevronUp className="w-5 h-5 text-slate-400" /> : <ChevronDown className="w-5 h-5 text-slate-400" />}
                </button>

                {showSuggestions && (
                  <div className="p-5 pt-0 space-y-4">
                    {evaluation.improvement_suggestions.resume_edits && evaluation.improvement_suggestions.resume_edits.length > 0 && (
                      <div className="space-y-3">
                        {evaluation.improvement_suggestions.resume_edits.map((edit, i) => (
                          <div key={i} className="bg-green-50 rounded-lg p-3 border border-green-100">
                            <p className="text-xs font-mono text-green-600 mb-1">{edit.area}</p>
                            <p className="text-sm text-slate-700">{edit.suggestion}</p>
                            {edit.approved_reference && (
                              <p className="text-xs text-slate-500 mt-1">Ref: {edit.approved_reference}</p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    {evaluation.improvement_suggestions.interview_prep && evaluation.improvement_suggestions.interview_prep.length > 0 && (
                      <div>
                        <h4 className="text-sm font-bold text-slate-700 mb-2">📖 Interview Prep</h4>
                        <ul className="space-y-1">
                          {evaluation.improvement_suggestions.interview_prep.map((prep, i) => (
                            <li key={i} className="text-sm text-slate-600">• {prep}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Parsed JD Results */}
            {parsedJD && (
              <div className="bg-gradient-to-br from-purple-50 to-blue-50 rounded-xl p-6 border border-purple-100">
                <h3 className="text-lg font-semibold text-slate-900 mb-4 flex items-center">
                  <Sparkles className="w-5 h-5 mr-2 text-purple-600" />
                  Parsed JD Signals
                </h3>

                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <span className="text-xs font-bold text-slate-400 uppercase">Domain</span>
                    <p className="text-slate-700 font-medium">{parsedJD.domain || 'Unspecified'}</p>
                  </div>
                  <div>
                    <span className="text-xs font-bold text-slate-400 uppercase">Seniority</span>
                    <p className="text-slate-700 font-medium capitalize">{parsedJD.seniority || 'Unspecified'}</p>
                  </div>
                </div>

                {parsedJD.must_haves && parsedJD.must_haves.length > 0 && (
                  <div className="mb-3">
                    <span className="text-xs font-bold text-rose-600 uppercase">Must-Haves</span>
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      {parsedJD.must_haves.map((req, i) => (
                        <span key={i} className="text-xs bg-rose-100 text-rose-700 px-2 py-1 rounded-md">
                          {req}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {parsedJD.ats_keywords && parsedJD.ats_keywords.length > 0 && (
                  <div>
                    <span className="text-xs font-bold text-blue-600 uppercase">ATS Keywords</span>
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      {parsedJD.ats_keywords.map((kw, i) => (
                        <span key={i} className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-md">
                          {kw}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

          </div>
        </div>
      </GlassCard>
    </div>
  );
};