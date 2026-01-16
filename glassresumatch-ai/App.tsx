import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Evaluation, EvaluationStats } from './services/apiClient';
import {
  fetchJobsWithEvaluations,
  fetchEvaluations,
  evaluateJob,
  deleteJobs,
  importJob,
  getAllJobIds,
  getEvaluationStats,
  getEvaluation,
  JobWithEvaluation
} from './services/jobService';
import apiClient from './services/apiClient';
import { ViewMode, FilterOptions, ResumeData, INITIAL_DATA } from './types';
import { JobListItem } from './components/JobListItem';
import { JobDetailView } from './components/JobDetailView';
import { Pagination } from './components/Pagination';
import { Header } from './components/Header';
import { FilterBar } from './components/FilterBar';
import { StatsCard } from './components/StatsCard';
import { ResumePreview, TemplateType } from './components/ResumePreview';
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
  ChevronRight,
  User,
  Eye,
  Upload,
  Download,
  Trash2
} from 'lucide-react';

const App: React.FC = () => {
  // --- Job Board Data state ---
  const [jobs, setJobs] = useState<JobWithEvaluation[]>([]);
  const [stats, setStats] = useState<EvaluationStats | null>(null);
  const [totalJobs, setTotalJobs] = useState(0);

  // --- Resume Builder State ---
  const [resumeData, setResumeData] = useState<ResumeData>(INITIAL_DATA);
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateType>('modern');
  const [isResumeLoading, setIsResumeLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);
  const printRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // --- UI state ---
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [evaluatingJobId, setEvaluatingJobId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [isDeleting, setIsDeleting] = useState(false);

  // --- Filter state ---
  const [viewMode, setViewMode] = useState<ViewMode>('all');
  const [filters, setFilters] = useState<FilterOptions>({
    searchQuery: '',
    verdict: 'all',
    action: 'all',
    sortBy: 'score',
    sortOrder: 'desc',
  });

  // --- Modals ---
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isBatchModalOpen, setIsBatchModalOpen] = useState(false);
  const [newJobText, setNewJobText] = useState('');
  const [analyzing, setAnalyzing] = useState(false);

  const ITEMS_PER_PAGE = 9;

  // --- Fetch Jobs Data ---
  // --- Fetch Jobs Data ---
  const loadData = useCallback(async (silent = false) => {
    // If we are in resume view, we technically don't need to refresh jobs, 
    // but we'll stick to the original behavior to keep state fresh or handle it gracefully.
    if (viewMode === 'resume') return;

    if (!silent) setLoading(true);
    setError(null);
    try {
      const statsResult = await getEvaluationStats().catch(() => null);
      setStats(statsResult);

      if (viewMode === 'evaluated') {
        const actionFilter = filters.action !== 'all' ? filters.action : undefined;
        const evaluationsResult = await fetchEvaluations(currentPage, ITEMS_PER_PAGE, actionFilter);

        const jobsWithEvals: JobWithEvaluation[] = evaluationsResult.data.map(e => ({
          id: e.job_id,
          title: e.title_role,
          company_name: e.company_name,
          location: null,
          posted_at: null,
          applicants_count: null,
          company_website: null,
          evaluation: e,
          isEvaluated: true,
        }));

        setJobs(jobsWithEvals);
        setTotalJobs(evaluationsResult.total);
      } else {
        const jobsResult = await fetchJobsWithEvaluations(currentPage, ITEMS_PER_PAGE);
        setJobs(jobsResult.data);
        setTotalJobs(jobsResult.total);
      }
    } catch (err) {
      console.error('Failed to load data:', err);
      setError('Failed to load jobs. Make sure the API server is running.');
    } finally {
      if (!silent) setLoading(false);
    }
  }, [currentPage, viewMode, filters.action]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // --- Fetch Resume Data ---
  const fetchResume = useCallback(async () => {
    try {
      setIsResumeLoading(true);
      const backendData = await apiClient.getMasterResume();

      // Check if processing
      if (backendData.status === 'processing') {
        // Return true to indicate we should keep polling
        return true;
      }

      // Check if error
      if (backendData.status === 'error') {
        console.error("Resume parsing error:", backendData.error);
        alert(`Resume parsing failed: ${backendData.error}\n\nPlease try again or check the backend logs.`);
        return false;
      }


      // 1. Saved Format (Flat ResumeData)
      if (backendData && backendData.fullName) {
        setResumeData(backendData);
        setIsUploading(false);
        return false;
      }

      // 2. Legacy/Parsed Format (JSON Resume Schema)
      if (backendData && backendData.basics) {
        // Map Nested JSON Resume to Flat ResumeData
        const mappedData: ResumeData = {
          fullName: backendData.basics.name || "Your Name",
          title: backendData.basics.label || "Professional Title",
          email: backendData.basics.email || "",
          phone: backendData.basics.phone || "",
          location: backendData.basics.location ?
            `${backendData.basics.location.city || ''}, ${backendData.basics.location.region || ''} ${backendData.basics.location.countryCode || ''}`.replace(/^, /, '').replace(/, $/, '')
            : "",
          websites: [
            backendData.basics.url || "",
            ...(backendData.basics.profiles?.map((p: any) => p.url) || [])
          ].filter(Boolean),
          summary: backendData.basics.summary || "",
          experience: backendData.work?.map((w: any) => ({
            id: Math.random().toString(36).substr(2, 9),
            company: w.name || "",
            role: w.position || "",
            period: `${w.startDate || ''} - ${w.endDate || 'Present'}`,
            location: w.location || "",
            achievements: w.highlights || []
          })) || [],
          education: backendData.education?.map((e: any) => ({
            id: Math.random().toString(36).substr(2, 9),
            institution: e.institution || "",
            degree: `${e.studyType || ''} ${e.area || ''}`,
            period: `${e.startDate || ''} - ${e.endDate || ''}`,
            location: "",
            score: e.score || ""
          })) || [],
          skills: backendData.skills?.map((s: any) =>
            s.keywords && s.keywords.length > 0
              ? `${s.name}: ${s.keywords.join(', ')}`
              : s.name
          ) || []
        };
        setResumeData(mappedData);
        setIsUploading(false); // Stop loading if we were uploading
      }
      return false; // Stop polling
    } catch (err) {
      console.error("Failed to load resume", err);
      return false; // Stop polling on error
    } finally {
      setIsResumeLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchResume();
  }, [fetchResume]);

  // --- Resume Upload Handler ---
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setIsResumeLoading(true);

    try {
      await apiClient.uploadResume(file);

      // Start polling for completion
      const pollInterval = setInterval(async () => {
        const serverStillProcessing = await fetchResume();
        if (!serverStillProcessing) {
          clearInterval(pollInterval);
          setIsUploading(false);
        }
      }, 2000); // Check every 2 seconds

      // Timeout after 60 seconds
      setTimeout(() => {
        clearInterval(pollInterval);
        setIsUploading(false);
        setIsResumeLoading(false);
      }, 60000);

    } catch (error) {
      console.error("Upload failed", error);
      setIsUploading(false);
      setIsResumeLoading(false);
      alert("Failed to upload resume. Please try again.");
    } finally {
      // Clear input
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // --- Resume Handlers ---
  const handlePrint = () => {
    window.focus();
    setTimeout(() => {
      window.print();
    }, 150);
  };

  const handleDownloadPdf = async () => {
    setIsGeneratingPdf(true);
    try {
      const blob = await apiClient.generatePdf(resumeData, selectedTemplate);

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${resumeData.fullName.replace(/\s+/g, '_')}_Resume.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error("PDF generation failed", error);
      alert("Failed to generate PDF. Please ensure the backend server has 'typst' installed.");
    } finally {
      setIsGeneratingPdf(false);
    }
  };


  const templates: { id: TemplateType, label: string, desc: string }[] = [
    { id: 'modern', label: 'Modern', desc: 'Clean, balanced, standard' },
    { id: 'classic', label: 'Classic', desc: 'Serif, traditional, formal' },
    { id: 'compact', label: 'Compact', desc: 'Dense, single page optimized' },
    { id: 'tech', label: 'Technical', desc: 'Monospaced, code-like' },
    { id: 'minimal', label: 'Traditional', desc: 'Ivy League, ATS-Standard' },
    { id: 'ats_friendly', label: 'ATS Friendly', desc: ' optimized for ATS parsing' },
  ];

  // --- Filter and sort jobs ---
  const filteredJobs = jobs.filter(job => {
    if (viewMode === 'evaluated' && !job.isEvaluated) return false;
    if (viewMode === 'pending' && job.isEvaluated) return false;
    if (filters.searchQuery) {
      const query = filters.searchQuery.toLowerCase();
      const matchesCompany = job.company_name?.toLowerCase().includes(query);
      const matchesTitle = job.title?.toLowerCase().includes(query);
      if (!matchesCompany && !matchesTitle) return false;
    }
    if (filters.verdict !== 'all' && job.evaluation?.verdict !== filters.verdict) return false;
    if (filters.action !== 'all' && job.evaluation?.recommended_action !== filters.action) return false;
    return true;
  }).sort((a, b) => {
    const multiplier = filters.sortOrder === 'asc' ? 1 : -1;
    switch (filters.sortBy) {
      case 'score':
        return ((b.evaluation?.job_match_score || 0) - (a.evaluation?.job_match_score || 0)) * multiplier;
      case 'company':
        return ((a.company_name || '').localeCompare(b.company_name || '')) * multiplier;
      case 'date':
        return ((b.posted_at || '').localeCompare(a.posted_at || '')) * multiplier;
      default:
        return 0;
    }
  });

  const selectedJob = jobs.find(j => j.id === selectedJobId) || null;

  const handleJobClick = async (job: JobWithEvaluation) => {
    setSelectedJobId(job.id);
  };

  const handleEvaluateJob = async (jobId: string) => {
    setEvaluatingJobId(jobId);
    try {
      await evaluateJob(jobId);
      await loadData(true);
      // If the evaluated job is the one currently selected, reload updates it automatically via selectedJob derivation
    } catch (err) {
      console.error('Failed to evaluate job:', err);
      setError('Failed to evaluate job. Please try again.');
    } finally {
      setEvaluatingJobId(null);
    }
  };

  const handleAnalyzeNewJob = async () => {
    if (!newJobText.trim()) return;
    setAnalyzing(true);
    try {
      // Assuming text is a URL
      // Assuming text is a URL
      const response = await importJob(newJobText.trim());

      if (response && response.id) {
        // Find and select the job (it might be newly added)
        setSelectedJobId(response.id);

        // Auto-start evaluation for the FIRST job (or only job)
        await evaluateJob(response.id);

        await loadData(); // Reload list

        // Re-select after reload
        setSelectedJobId(response.id);

        if (response.count && response.count > 1) {
          alert(`Batch Import Successful! Imported ${response.count} jobs. Analyzing the newest one.`);
        } else {
          alert('Job Imported & Analyzed Successfully!');
        }
      } else {
        throw new Error("Import returned no ID");
      }

    } catch (error) {
      console.error('Import/Analyze failed', error);
      alert('Failed to import/analyze job. Ensure it is a valid LinkedIn URL.');
    } finally {
      setAnalyzing(false);
      setIsAddModalOpen(false);
      setNewJobText('');
    }
  };

  // --- Selection Handlers ---
  const toggleSelectJob = (id: string) => {
    const newSelected = new Set(selectedIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    setSelectedIds(newSelected);
  };

  const toggleSelectAll = async () => {
    if (selectedIds.size === totalJobs && totalJobs > 0) {
      // If all are selected (based on count), unselect all
      setSelectedIds(new Set());
    } else {
      try {
        if (filters.searchQuery) {
          // If filtering, select only visible for now (simplification)
          setSelectedIds(new Set(filteredJobs.map(j => j.id)));
        } else {
          // Global Select All - Fetch all IDs
          const allIds = await getAllJobIds();
          setSelectedIds(new Set(allIds));
        }
      } catch (err) {
        console.error("Failed to select all", err);
        alert("Failed to select all jobs");
      }
    }
  };

  const handleDeleteSelected = async () => {
    if (selectedIds.size === 0) return;
    if (!confirm(`Are you sure you want to delete ${selectedIds.size} jobs?`)) return;

    setIsDeleting(true);
    try {
      await deleteJobs(Array.from(selectedIds));
      setSelectedIds(new Set());
      await loadData();
    } catch (err) {
      console.error('Failed to delete jobs:', err);
      alert('Failed to delete jobs');
    } finally {
      setIsDeleting(false);
    }
  };

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

      {/* Main Container - Reset padding/margins for print */}
      <main className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 print:p-0 print:m-0 print:max-w-none print:w-full">

        {/* Stats Card - Show only in job views */}
        {viewMode !== 'resume' && (
          <div className="print:hidden">
            <StatsCard stats={stats} totalJobs={totalJobs} />
          </div>
        )}

        {/* Filter Bar - Show only in job views */}
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

        {/* Error Message */}
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

        {/* --- MAIN CONTENT AREA --- */}
        {viewMode === 'resume' ? (
          <div>
            {/* Resume Toolbar - Hide in print */}
            <div className="mb-8 animate-in slide-in-from-top-2 relative z-40 print:hidden">
              <div className="flex flex-col lg:flex-row gap-6 items-start lg:items-center justify-between p-6 rounded-2xl bg-white border border-slate-200 shadow-xl">

                {/* Template Selector */}
                <div className="flex-1 w-full lg:w-auto overflow-hidden">
                  <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Select Template</h4>
                  <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-slate-200">
                    {templates.map(t => (
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

                {/* Action Buttons */}
                <div className="flex items-center gap-3 border-t lg:border-t-0 lg:border-l border-slate-100 pt-4 lg:pt-0 lg:pl-6">

                  {/* File Upload Input */}
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
                    onClick={() => setIsEditorOpen(true)}
                    className="flex items-center gap-2 px-4 py-3 rounded-xl bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold transition-all shadow-sm"
                  >
                    <PenLine size={18} />
                    <span>Edit Data</span>
                  </button>

                  <button
                    onClick={handleDownloadPdf}
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

            {/* Resume Preview - Position absolutely for print */}
            <div className="flex justify-center pb-12 print:pb-0 print:block">
              {isResumeLoading ? (
                <div className="py-20 flex flex-col items-center">
                  <Loader2 className="w-10 h-10 text-slate-300 animate-spin mb-4" />
                  <p className="text-slate-500 font-medium animate-pulse">
                    {isUploading ? 'Analyzing resume with AI...' : 'Loading resume data...'}
                  </p>
                </div>
              ) : (
                <div id="resume-preview-container" className="animate-in fade-in slide-in-from-bottom-4 duration-500 w-full flex justify-center print:absolute print:top-0 print:left-0 print:w-full print:m-0 print:block">
                  <ResumePreview data={resumeData} targetRef={printRef} template={selectedTemplate} />
                </div>
              )}
            </div>
          </div>
        ) : (
          // --- JOB BOARD CONTENT ---
          <div className="print:hidden">
            {loading ? (
              <div className="flex flex-col items-center justify-center h-[60vh]">
                <Loader2 className="w-12 h-12 text-slate-300 animate-spin mb-4" />
                <p className="text-slate-500 animate-pulse font-medium">Loading jobs...</p>
              </div>
            ) : filteredJobs.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-[40vh]">
                <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mb-4">
                  <Sparkles className="w-8 h-8 text-slate-300" />
                </div>
                <p className="text-slate-500 font-medium">No jobs match your filters</p>
                <button
                  onClick={() => {
                    setViewMode('all');
                    setFilters({
                      searchQuery: '',
                      verdict: 'all',
                      action: 'all',
                      sortBy: 'score',
                      sortOrder: 'desc',
                    });
                  }}
                  className="mt-3 text-blue-600 hover:text-blue-700 text-sm font-medium"
                >
                  Clear filters
                </button>
              </div>
            ) : (
              <div className="flex h-[calc(100vh-140px)] gap-6 overflow-hidden">
                {/* LEFT SIDEBAR: Job List */}
                <div className="w-full lg:w-[400px] flex-shrink-0 flex flex-col bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
                  <div className="p-3 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center h-12">
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={totalJobs > 0 && selectedIds.size === totalJobs}
                        onChange={toggleSelectAll}
                        className="w-4 h-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                      />
                      <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                        {selectedIds.size > 0 ? `${selectedIds.size} Selected` : `${totalJobs} Jobs`}
                      </p>
                    </div>

                    {selectedIds.size > 0 && (
                      <button
                        onClick={handleDeleteSelected}
                        disabled={isDeleting}
                        className="flex items-center gap-1 text-xs font-bold text-rose-600 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 px-2 py-1 rounded transition-colors"
                      >
                        {isDeleting ? <Loader2 size={12} className="animate-spin" /> : <Trash2 size={12} />}
                        Delete
                      </button>
                    )}
                  </div>
                  <div className="flex-1 overflow-y-auto min-h-0 scrollbar-thin scrollbar-thumb-slate-200">
                    {filteredJobs.map((job) => (
                      <JobListItem
                        key={job.id}
                        job={job}
                        isActive={selectedJobId === job.id}
                        isSelected={selectedIds.has(job.id)}
                        onToggleSelect={() => toggleSelectJob(job.id)}
                        onClick={() => handleJobClick(job)}
                      />
                    ))}
                    {/* Pagination inside sidebar */}
                    <div className="p-4 border-t border-slate-100">
                      <Pagination
                        currentPage={currentPage}
                        totalPages={Math.ceil(totalJobs / ITEMS_PER_PAGE)}
                        onPageChange={setCurrentPage}
                      />
                    </div>
                  </div>
                </div>

                {/* RIGHT MAIN: Job Details */}
                <div className="flex-1 min-w-0 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden relative">
                  {selectedJob ? (
                    <JobDetailView
                      job={selectedJob}
                      onEvaluate={() => {
                        // Reload data to reflect new status (silent refresh)
                        loadData(true);
                      }}
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
          </div>
        )}
      </main>

      {/* Batch Evaluate Modal */}
      <div className="print:hidden">
        <BatchEvaluate
          isOpen={isBatchModalOpen}
          onClose={() => setIsBatchModalOpen(false)}
          onComplete={loadData}
        />
      </div>

      {/* Add New Job Modal */}
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
            <div className="flex justify-end mt-4 space-x-3">
              <button
                onClick={() => setIsAddModalOpen(false)}
                disabled={analyzing}
                className="px-4 py-2 rounded-lg hover:bg-slate-100 text-slate-500 font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleAnalyzeNewJob}
                disabled={analyzing || !newJobText.trim()}
                className="px-6 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-medium shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed flex items-center transition-all"
              >
                {analyzing ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  'Analyze Match'
                )}
              </button>
            </div>
          </GlassCard>
        </div>
      )}

      {/* Editor Slide-over */}
      <div
        className={`
            fixed inset-y-0 right-0 z-50 w-full md:w-[600px] bg-[#0f172a] shadow-2xl transform transition-transform duration-300 ease-in-out border-l border-white/10 print:hidden
            ${isEditorOpen ? 'translate-x-0' : 'translate-x-full pointer-events-none'}
          `}
      >
        {isEditorOpen && (
          <Editor
            data={resumeData}
            onChange={setResumeData}
            onClose={() => setIsEditorOpen(false)}
          />
        )}
      </div>

      {/* Backdrop for Editor */}
      {isEditorOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-40 backdrop-blur-sm transition-opacity print:hidden"
          onClick={() => setIsEditorOpen(false)}
        />
      )}

    </div>
  );
};

export default App;