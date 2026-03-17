import React, { useState, useRef, useEffect, useCallback } from 'react';
import { JobWithEvaluation, evaluateJob, importJob } from './services/jobService';
import { apiClient } from './services/apiClient';
import { useJobs } from './hooks/useJobs';
import { useResumeState } from './hooks/useResumeState';
import { useJobSelection } from './hooks/useJobSelection';
import { ViewMode, FilterOptions, TemplateType } from './types';
import { JobListPanel } from './components/JobListPanel';
import { JobDetailView } from './components/JobDetailView';
import { Toast } from './components/Toast';
import { Header } from './components/Header';
import { FilterBar } from './components/FilterBar';
import { StatsCard } from './components/StatsCard';
import { ResumePreview } from './components/ResumePreview';
import { BatchEvaluate } from './components/BatchEvaluate';
import { GlassCard } from './components/GlassCard';
import { Editor } from './components/Editor';
import {
  Loader2,
  Sparkles,
  AlertCircle,
  PenLine,
  Printer,
  Check,
  Briefcase,
  Upload,
  Download,
} from 'lucide-react';

const App: React.FC = () => {
  // --- UI State ---
  // Initialize viewMode from URL hash (e.g., #resume -> 'resume')
  const [viewMode, setViewModeRaw] = useState<ViewMode>(() => {
    const hash = window.location.hash.replace('#', '');
    if (hash === 'resume') return 'resume';
    if (hash === 'evaluated') return 'evaluated';
    if (hash === 'pending') return 'pending';
    return 'all';
  });

  // Wrap setViewMode to push browser history state
  const setViewMode = useCallback((mode: ViewMode) => {
    setViewModeRaw(mode);
    const hash = mode === 'all' ? '' : `#${mode}`;
    window.history.pushState({ viewMode: mode }, '', hash || window.location.pathname);
  }, []);

  // Listen for browser back/forward
  useEffect(() => {
    const handlePopState = (event: PopStateEvent) => {
      const mode = event.state?.viewMode;
      if (mode) {
        setViewModeRaw(mode);
      } else {
        // Fallback: read from hash
        const hash = window.location.hash.replace('#', '');
        setViewModeRaw(hash === 'resume' ? 'resume' : 'all');
      }
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);
  const [filters, setFilters] = useState<FilterOptions>({
    searchQuery: '',
    verdict: 'all',
    action: 'apply', // Default to Apply Now tab
    sortBy: 'date',
    sortOrder: 'desc',
  });
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false);
  const [newJobText, setNewJobText] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  // Lifted state for Resume Tailoring
  const [tailoringJobId, setTailoringJobId] = useState<string | null>(null);

  // App-level toast (for import/analysis flows)
  const [appToast, setAppToast] = useState<{ message: string; type: 'error' | 'success' } | null>(null);
  const showAppToast = (message: string, type: 'error' | 'success') => {
    setAppToast({ message, type });
    setTimeout(() => setAppToast(null), 4500);
  };

  // Google Docs Import state
  const [isGDocImportOpen, setIsGDocImportOpen] = useState(false);
  const [gDocInput, setGDocInput] = useState('');
  const [isImportingGDoc, setIsImportingGDoc] = useState(false);

  // --- Profile / Resume State (Hook) ---
  const {
    resumeData,
    setResumeData,
    isResumeLoading,
    isUploading,
    isGeneratingPdf,
    fileInputRef,
    handleFileUpload,
    generatePdf
  } = useResumeState();

  // --- Resume Builder UI State ---
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateType>('modern');
  const printRef = useRef<HTMLDivElement>(null);

  // --- Jobs Data (Hook) ---
  const {
    jobs,
    stats,
    totalJobs,
    loading,
    loadingMore,
    error,
    hasMore,
    loadMore,
    refresh: loadData
  } = useJobs(viewMode, filters);

  // Search-only filter for selection hook (JobListPanel owns the sort)
  const searchFilteredJobs = React.useMemo(() => {
    if (!filters.searchQuery) return jobs;
    const query = filters.searchQuery.toLowerCase();
    return jobs.filter(j =>
      j.company_name?.toLowerCase().includes(query) ||
      j.title?.toLowerCase().includes(query)
    );
  }, [jobs, filters.searchQuery]);

  // --- Selection (Hook) ---
  const {
    selectedIds,
    isDeleting,
    toggleSelectJob,
    toggleSelectAll,
    handleDeleteSelected
  } = useJobSelection(totalJobs, searchFilteredJobs, filters, () => loadData(true)); // Refresh silently on delete

  // --- Handlers ---
  const handleJobClick = (job: JobWithEvaluation) => {
    setSelectedJobId(job.id);
  };

  const handleAnalyzeNewJob = async () => {
    if (!newJobText.trim()) return;
    setAnalyzing(true);
    try {
      const response = await importJob(newJobText.trim());

      if (response && response.id) {
        setSelectedJobId(response.id);
        await evaluateJob(response.id);
        await loadData();
        setSelectedJobId(response.id);

        if (response.count && response.count > 1) {
          showAppToast(`Imported ${response.count} jobs. Analyzing the newest one.`, 'success');
        } else {
          showAppToast('Job imported & analyzed successfully!', 'success');
        }
      } else {
        throw new Error("Import returned no ID");
      }
    } catch (error) {
      console.error('Import/Analyze failed', error);
      showAppToast('Failed to import/analyze job. Ensure it is a valid LinkedIn URL.', 'error');
    } finally {
      setAnalyzing(false);
      setIsAddModalOpen(false);
      setNewJobText('');
    }
  };

  const handlePrint = () => {
    window.focus();
    setTimeout(() => {
      window.print();
    }, 150);
  };

  const extractGoogleDocId = (input: string): string => {
    const match = input.match(/\/d\/([a-zA-Z0-9_-]+)/);
    return match ? match[1] : input; // If no match, assume raw ID
  };

  const handleGDocImport = async () => {
    if (!gDocInput.trim()) return;
    setIsImportingGDoc(true);
    try {
      const documentId = extractGoogleDocId(gDocInput.trim());
      await apiClient.importFromGoogleDoc(documentId);

      // Poll for completion — same as PDF upload
      const poll = setInterval(async () => {
        try {
          const resume = await apiClient.getMasterResume();
          if (resume && resume.status === 'error') {
            clearInterval(poll);
            setIsImportingGDoc(false);
            showAppToast(`Resume parsing failed: ${resume.error || 'Unknown error'}`, 'error');
            return;
          }
          if (resume && resume.status !== 'processing' && resume.fullName) {
            clearInterval(poll);
            setResumeData(resume);
            setIsImportingGDoc(false);
            setIsGDocImportOpen(false);
            setGDocInput('');
          }
        } catch {
          // Still processing
        }
      }, 2000);

      // Timeout after 60s
      setTimeout(() => {
        clearInterval(poll);
        if (isImportingGDoc) {
          setIsImportingGDoc(false);
          showAppToast('Import timed out. The resume may still be processing — try refreshing.', 'error');
        }
      }, 60000);
    } catch (error) {
      console.error('Google Doc import failed:', error);
      showAppToast('Failed to import from Google Docs. Please check the URL and try again.', 'error');
      setIsImportingGDoc(false);
    }
  };

  const selectedJob = jobs.find(j => j.id === selectedJobId) || null;

  const templatesList: { id: TemplateType, label: string, desc: string }[] = [
    { id: 'modern', label: 'Modern', desc: 'Clean, balanced, standard' },
    { id: 'classic', label: 'Classic', desc: 'Serif, traditional, formal' },
    { id: 'compact', label: 'Compact', desc: 'Dense, single page optimized' },
    { id: 'tech', label: 'Technical', desc: 'Monospaced, code-like' },
    { id: 'minimal', label: 'Traditional', desc: 'Ivy League, ATS-Standard' },
    { id: 'ats_friendly', label: 'ATS Friendly', desc: ' optimized for ATS parsing' },
  ];

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 selection:bg-blue-100 selection:text-blue-900 font-sans">
      {/* Abstract Background Blobs - Hide in print */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none print:hidden">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] rounded-full bg-blue-100/50 blur-[100px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] rounded-full bg-purple-100/50 blur-[100px]" />
        <div className="absolute top-[30%] left-[60%] w-[20%] h-[20%] rounded-full bg-emerald-50/60 blur-[80px]" />
      </div>

      <div className="print:hidden">
        <Header
          onAddJob={() => setIsAddModalOpen(true)}
          onBatchEvaluate={() => setIsBatchModalOpen(true)}
          totalJobs={totalJobs}
          evaluatedCount={stats?.total_evaluated || 0}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
        />
      </div>

      <main className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 print:p-0 print:m-0 print:max-w-none print:w-full">

        {viewMode !== 'resume' && (
          <div className="print:hidden">
            <StatsCard stats={stats} totalJobs={totalJobs} />
          </div>
        )}

        {viewMode !== 'resume' && (
          <div className="print:hidden">
            <FilterBar
              viewMode={viewMode}
              onViewModeChange={setViewMode}
              filters={filters}
              onFiltersChange={setFilters}
            />
          </div>
        )}

        {error && (
          <div className="bg-rose-50 border border-rose-200 rounded-xl p-4 mb-6 flex items-center print:hidden">
            <AlertCircle className="w-5 h-5 text-rose-500 mr-3" />
            <p className="text-rose-700">{error}</p>
            <button
              onClick={() => loadData()}
              className="ml-auto px-3 py-1 bg-rose-100 hover:bg-rose-200 text-rose-700 rounded-lg text-sm font-medium"
            >
              Retry
            </button>
          </div>
        )}

        {viewMode === 'resume' ? (
          <div>
            {/* Resume Toolbar */}
            <div className="mb-8 animate-in slide-in-from-top-2 relative z-40 print:hidden">
              <div className="flex flex-col lg:flex-row gap-6 items-start lg:items-center justify-between p-6 rounded-2xl bg-white border border-slate-200 shadow-xl">

                {/* Template Selector */}
                <div className="flex-1 w-full lg:w-auto overflow-hidden">
                  <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Select Template</h4>
                  <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-slate-200">
                    {templatesList.map(t => (
                      <button
                        key={t.id}
                        onClick={() => setSelectedTemplate(t.id)}
                        className={`
                              flex flex-col items-start min-w-[140px] p-3 rounded-xl border transition-all text-left group cursor-pointer shrink-0
                              ${selectedTemplate === t.id
                            ? 'bg-slate-900 text-white border-slate-900 shadow-md transform scale-[1.02]'
                            : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'}
                            `}
                      >
                        <div className="flex justify-between w-full mb-1">
                          <span className="font-bold text-sm">{t.label}</span>
                          {selectedTemplate === t.id && <Check size={16} className="text-emerald-400" />}
                        </div>
                        <span className={`text-[10px] leading-tight ${selectedTemplate === t.id ? 'text-slate-300' : 'text-slate-400'}`}>
                          {t.desc}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex items-center gap-3 border-t lg:border-t-0 lg:border-l border-slate-100 pt-4 lg:pt-0 lg:pl-6">
                  <input
                    type="file"
                    accept=".pdf"
                    ref={fileInputRef}
                    className="hidden"
                    onChange={handleFileUpload}
                  />

                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isUploading}
                    className="flex items-center gap-2 px-4 py-3 rounded-xl bg-blue-50 border border-blue-100 hover:bg-blue-100 text-blue-700 font-semibold transition-all shadow-sm"
                  >
                    {isUploading ? (
                      <Loader2 size={18} className="animate-spin" />
                    ) : (
                      <Upload size={18} />
                    )}
                    <span>{isUploading ? 'Parsing...' : 'Upload PDF'}</span>
                  </button>

                  <button
                    onClick={() => setIsGDocImportOpen(true)}
                    disabled={isImportingGDoc}
                    className="flex items-center gap-2 px-4 py-3 rounded-xl bg-emerald-50 border border-emerald-100 hover:bg-emerald-100 text-emerald-700 font-semibold transition-all shadow-sm"
                  >
                    {isImportingGDoc ? (
                      <Loader2 size={18} className="animate-spin" />
                    ) : (
                      <Download size={18} />
                    )}
                    <span>{isImportingGDoc ? 'Importing...' : 'Import Google Doc'}</span>
                  </button>

                  <button
                    onClick={() => setIsEditorOpen(true)}
                    className="flex items-center gap-2 px-4 py-3 rounded-xl bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold transition-all shadow-sm"
                  >
                    <PenLine size={18} />
                    <span>Edit Data</span>
                  </button>

                  <button
                    onClick={() => generatePdf(selectedTemplate)}
                    disabled={isGeneratingPdf}
                    className="flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold shadow-lg transition-all hover:scale-105 active:scale-95 cursor-pointer"
                  >
                    {isGeneratingPdf ? (
                      <Loader2 size={18} className="animate-spin" />
                    ) : (
                      <Download size={18} />
                    )}
                    <span>Download PDF</span>
                  </button>

                  <button
                    onClick={handlePrint}
                    className="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-bold shadow-lg transition-all hover:scale-105 active:scale-95 cursor-pointer"
                  >
                    <Printer size={18} />
                    <span>Print / Preview</span>
                  </button>
                </div>
              </div>

              <div className="mt-4 text-center">
                <p className="text-slate-400 text-xs flex items-center justify-center gap-2 inline-block px-4 py-1 rounded-full bg-white/50 border border-slate-100">
                  <AlertCircle size={12} />
                  <span>Tip: Use <strong>"Typst PDF"</strong> for high-quality generation, or <strong>"Print"</strong> for browser-based saving.</span>
                </p>
              </div>
            </div>

            <div className="flex justify-center pb-12 print:pb-0 print:block">
              {isResumeLoading ? (
                <div className="py-20 flex flex-col items-center">
                  <Loader2 className="w-10 h-10 text-slate-300 animate-spin mb-4" />
                  <p className="text-slate-500 font-medium animate-pulse">
                    {isUploading || isImportingGDoc ? 'Analyzing resume with AI...' : 'Loading resume data...'}
                  </p>
                </div>
              ) : resumeData.experience.length === 0 && resumeData.skills.length === 0 ? (
                <div className="py-20 flex flex-col items-center max-w-md text-center">
                  <div className="w-20 h-20 bg-slate-100 rounded-full flex items-center justify-center mb-6">
                    <Upload className="w-10 h-10 text-slate-300" />
                  </div>
                  <h3 className="text-lg font-bold text-slate-700 mb-2">No Resume Found</h3>
                  <p className="text-slate-500 mb-6">
                    Upload a PDF or import from Google Docs to get started. Your resume will be parsed by AI and saved for tailoring.
                  </p>
                  <div className="flex gap-3">
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      className="flex items-center gap-2 px-5 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold transition-all shadow-md"
                    >
                      <Upload size={18} />
                      Upload PDF
                    </button>
                    <button
                      onClick={() => setIsGDocImportOpen(true)}
                      className="flex items-center gap-2 px-5 py-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold transition-all shadow-md"
                    >
                      <Download size={18} />
                      Import Google Doc
                    </button>
                  </div>
                </div>
              ) : (
                <div id="resume-preview-container" className="animate-in fade-in slide-in-from-bottom-4 duration-500 w-full flex justify-center print:absolute print:top-0 print:left-0 print:w-full print:m-0 print:block">
                  <ResumePreview data={resumeData} targetRef={printRef} template={selectedTemplate} />
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="print:hidden flex h-[calc(100vh-140px)] gap-6 overflow-hidden">
            {/* LEFT SIDEBAR: Job List */}
            <div className="w-full lg:w-[360px] flex-shrink-0 flex flex-col bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
              {/* Action tab strip */}
              <div className="flex border-b border-slate-100 px-3 pt-2 gap-0.5 flex-shrink-0">
                {([
                  { action: 'apply',  label: 'Apply now',    dot: 'bg-green-500',  active: 'text-green-700 border-green-500' },
                  { action: 'tailor', label: 'Tailor first', dot: 'bg-amber-500',  active: 'text-amber-700 border-amber-500' },
                  { action: 'skip',   label: 'Skip',         dot: 'bg-slate-300',  active: 'text-slate-600 border-slate-400' },
                ] as const).map(({ action, label, dot, active }) => {
                  const count = stats?.by_action[action] ?? 0;
                  const isActive = filters.action === action;
                  return (
                    <button
                      key={action}
                      onClick={() => setFilters(prev => ({ ...prev, action }))}
                      className={`flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium border-b-2 transition-colors whitespace-nowrap ${
                        isActive
                          ? `${active} bg-white`
                          : 'text-slate-400 border-transparent hover:text-slate-600'
                      }`}
                    >
                      <div className={`w-[5px] h-[5px] rounded-full ${dot}`} />
                      {label}
                      {count > 0 && (
                        <span className={`tabular-nums text-[10px] ${isActive ? 'opacity-70' : 'text-slate-300'}`}>
                          {count}
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>

              <JobListPanel
                jobs={searchFilteredJobs}
                totalJobs={totalJobs}
                loading={loading}
                loadingMore={loadingMore}
                hasMore={hasMore}
                loadMore={loadMore}
                showSectionHeaders={filters.action === 'all'}
                activeAction={filters.action as 'apply' | 'tailor' | 'skip' | 'all'}
                selectedJobId={selectedJobId}
                selectedIds={selectedIds}
                isDeleting={isDeleting}
                onJobClick={handleJobClick}
                onToggleSelect={toggleSelectJob}
                onToggleSelectAll={toggleSelectAll}
                onDeleteSelected={handleDeleteSelected}
              />
            </div>

            {/* RIGHT MAIN: Job Details */}
            <div className="flex-1 min-w-0 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden relative">
              {selectedJob ? (
                <JobDetailView
                  job={selectedJob}
                  onEvaluate={() => loadData(true)}
                  tailoringJobId={tailoringJobId}
                  onTailorStart={setTailoringJobId}
                  onTailorEnd={() => setTailoringJobId(null)}
                />
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-slate-400">
                  <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-4">
                    <Briefcase className="w-8 h-8 text-slate-300" />
                  </div>
                  <p className="font-medium">Select a job to view details</p>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      <div className="print:hidden">
        <BatchEvaluate
          isOpen={isBatchModalOpen}
          onClose={() => setIsBatchModalOpen(false)}
          onComplete={() => loadData(false)}
        />
      </div>

      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 print:hidden">
          <div
            className="absolute inset-0 bg-slate-900/20 backdrop-blur-sm transition-opacity"
            onClick={() => !analyzing && setIsAddModalOpen(false)}
          />
          <GlassCard className="w-full max-w-2xl p-6 z-20 bg-white/95 shadow-2xl">
            <h2 className="text-xl font-bold mb-4 flex items-center text-slate-900">
              <Sparkles className="w-5 h-5 mr-2 text-blue-600" />
              Import from LinkedIn
            </h2>
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-700 mb-1">LinkedIn Job URL</label>
              <input
                type="text"
                className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                placeholder="https://www.linkedin.com/jobs/view/..."
                value={newJobText}
                onChange={(e) => setNewJobText(e.target.value)}
                disabled={analyzing}
              />
              <p className="text-xs text-slate-500 mt-2">
                Paste a LinkedIn job URL. We will scrape and analyze it automatically.
              </p>
            </div>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg font-medium transition-colors"
                disabled={analyzing}
              >
                Cancel
              </button>
              <button
                onClick={handleAnalyzeNewJob}
                disabled={analyzing || !newJobText.trim()}
                className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium shadow-md transition-all flex items-center gap-2"
              >
                {analyzing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    Start Analysis
                    <Sparkles className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </GlassCard>
        </div>
      )}

      {isGDocImportOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 print:hidden">
          <div
            className="absolute inset-0 bg-slate-900/20 backdrop-blur-sm transition-opacity"
            onClick={() => !isImportingGDoc && setIsGDocImportOpen(false)}
          />
          <GlassCard className="w-full max-w-lg p-6 z-20 bg-white/95 shadow-2xl">
            <h2 className="text-xl font-bold mb-4 flex items-center text-slate-900">
              <Download className="w-5 h-5 mr-2 text-emerald-600" />
              Import from Google Docs
            </h2>
            <div className="mb-4">
              <label className="block text-sm font-medium text-slate-700 mb-1">Google Doc URL or ID</label>
              <input
                type="text"
                className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-slate-700 placeholder:text-slate-400 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-all"
                placeholder="https://docs.google.com/document/d/1abc.../edit"
                value={gDocInput}
                onChange={(e) => setGDocInput(e.target.value)}
                disabled={isImportingGDoc}
              />
              <p className="text-xs text-slate-500 mt-2">
                Paste a Google Doc URL or document ID. The content will be parsed by AI and saved as your master resume.
              </p>
            </div>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => { setIsGDocImportOpen(false); setGDocInput(''); }}
                className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg font-medium transition-colors"
                disabled={isImportingGDoc}
              >
                Cancel
              </button>
              <button
                onClick={handleGDocImport}
                disabled={isImportingGDoc || !gDocInput.trim()}
                className="px-6 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-medium shadow-md transition-all flex items-center gap-2"
              >
                {isImportingGDoc ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Importing...
                  </>
                ) : (
                  'Import Resume'
                )}
              </button>
            </div>
          </GlassCard>
        </div>
      )}

      {isEditorOpen && (
        <Editor
          data={resumeData}
          onChange={(newData) => setResumeData(newData)}
          onClose={() => setIsEditorOpen(false)}
        />
      )}

      {appToast && (
        <Toast
          message={appToast.message}
          type={appToast.type}
          onDismiss={() => setAppToast(null)}
        />
      )}
    </div>
  );
};

export default App;