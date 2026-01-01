import React, { useEffect, useState } from 'react';
import { apiClient } from '../services/apiClient';
import { User, Mail, Phone, MapPin, Globe, Briefcase, GraduationCap, Award, Code, Upload, AlertCircle } from 'lucide-react';

interface ResumeData {
    basics?: {
        name?: string;
        label?: string;
        email?: string;
        phone?: string;
        url?: string;
        summary?: string;
        location?: {
            city?: string;
            countryCode?: string;
            region?: string;
        };
    };
    work?: Array<{
        name?: string;
        position?: string;
        startDate?: string;
        endDate?: string;
        summary?: string;
        highlights?: string[];
    }>;
    education?: Array<{
        institution?: string;
        area?: string;
        studyType?: string;
        startDate?: string;
        endDate?: string;
    }>;
    skills?: Array<{
        name?: string;
        keywords?: string[];
    }>;
}

export const ResumePreview: React.FC = () => {
    const [resume, setResume] = useState<any | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [isPolling, setIsPolling] = useState(false);

    useEffect(() => {
        fetchResume();
    }, []);

    // Polling effect when processing
    useEffect(() => {
        let interval: any;
        if (resume?.status === 'processing' || isPolling) {
            interval = setInterval(async () => {
                const data = await apiClient.getMasterResume();
                if (data && data.status !== 'processing') {
                    setResume(data);
                    setIsPolling(false);
                    clearInterval(interval);
                }
            }, 3000); // Check every 3 seconds
        }
        return () => clearInterval(interval);
    }, [resume?.status, isPolling]);

    const fetchResume = async () => {
        try {
            setLoading(true);
            const data = await apiClient.getMasterResume();
            setResume(data);
            if (data?.status === 'processing') {
                setIsPolling(true);
            }
        } catch (err) {
            console.error(err);
            // Don't set error if we just don't have a resume yet (404)
            if (resume === null) {
                // Leave as null, UI will show upload
            } else {
                setError('Failed to load resume info.');
            }
        } finally {
            setLoading(false);
        }
    };

    const formatDate = (dateString?: string) => {
        if (!dateString) return '';
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
        } catch {
            return dateString;
        }
    };

    if (loading && !isPolling) {
        return (
            <div className="flex items-center justify-center p-12 h-[60vh]">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-8 h-8 border-4 border-slate-200 border-t-blue-600 rounded-full animate-spin"></div>
                    <p className="text-slate-500 font-medium animate-pulse">
                        Loading resume...
                    </p>
                </div>
            </div>
        );
    }

    // Special Processing UI
    if (resume?.status === 'processing' || isPolling) {
        return (
            <div className="max-w-xl mx-auto my-12 p-12 bg-white rounded-2xl shadow-xl border border-slate-200 text-center">
                <div className="relative w-24 h-24 mx-auto mb-8">
                    <div className="absolute inset-0 border-4 border-blue-50 border-t-blue-600 rounded-full animate-spin"></div>
                    <div className="absolute inset-4 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center">
                        <Upload className="w-8 h-8 animate-bounce" />
                    </div>
                </div>

                <h2 className="text-2xl font-bold text-slate-900 mb-4">Parsing Your Resume...</h2>
                <div className="space-y-4 max-w-sm mx-auto">
                    <p className="text-slate-500">
                        Our AI is extracting your experience and skills. This usually takes about a minute.
                    </p>
                    <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                        <div className="bg-blue-600 h-full animate-shimmer" style={{ width: '60%', backgroundSize: '200% 100%', backgroundImage: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent)' }}></div>
                    </div>
                    <p className="text-xs text-slate-400 font-medium uppercase tracking-wider">
                        Tailoring to your profile
                    </p>
                </div>
            </div>
        );
    }

    // Handle background error
    if (resume?.status === 'error') {
        return (
            <div className="max-w-xl mx-auto my-12 p-8 bg-white rounded-2xl shadow-xl border border-slate-200 text-center">
                <div className="w-16 h-16 bg-rose-50 text-rose-600 rounded-2xl flex items-center justify-center mx-auto mb-6">
                    <AlertCircle className="w-8 h-8" />
                </div>
                <h2 className="text-2xl font-bold text-slate-900 mb-2">Parsing Failed</h2>
                <p className="text-slate-500 mb-6">{resume.error || 'An unknown error occurred during parsing.'}</p>
                <button
                    onClick={() => setResume(null)}
                    className="px-6 py-2 bg-slate-900 text-white rounded-xl font-medium hover:bg-slate-800 transition-all"
                >
                    Try Again
                </button>
            </div>
        );
    }

    // Upload UI if no resume found
    if (error || !resume) {
        const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
            const file = event.target.files?.[0];
            if (!file) return;

            try {
                setLoading(true);
                setError(null);
                const data = await apiClient.uploadResume(file);
                setResume(data); // Immediate status: processing
                setIsPolling(true);
                setLoading(false);
            } catch (err: any) {
                console.error(err);
                setLoading(false);
                setError(err.message || 'Failed to upload and parse resume');
            }
        };

        return (
            <div className="max-w-xl mx-auto my-12 p-8 bg-white rounded-2xl shadow-xl border border-slate-200 text-center">
                <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-6">
                    <Briefcase className="w-8 h-8" />
                </div>

                <h2 className="text-2xl font-bold text-slate-900 mb-2">Upload Your Resume</h2>
                <p className="text-slate-500 mb-8">
                    Upload your PDF resume to get started. We'll use AI to parse it into a structured format for tailoring.
                </p>

                {error && (
                    <div className="mb-6 p-4 bg-rose-50 text-rose-600 rounded-xl text-sm border border-rose-100 flex items-center justify-center">
                        <AlertCircle className="w-4 h-4 mr-2" />
                        {error}
                    </div>
                )}

                <label className="relative block group cursor-pointer">
                    <div className="border-2 border-dashed border-slate-200 rounded-xl p-12 transition-all group-hover:border-blue-500 group-hover:bg-blue-50/50">
                        <div className="flex flex-col items-center">
                            <div className="p-4 bg-slate-100 rounded-full mb-4 group-hover:bg-blue-100 transition-colors">
                                <Upload className="w-6 h-6 text-slate-400 group-hover:text-blue-600" />
                            </div>
                            <span className="text-slate-900 font-medium mb-1">Click to upload PDF</span>
                            <span className="text-slate-400 text-sm">or drag and drop here</span>
                        </div>
                    </div>
                    <input
                        type="file"
                        accept=".pdf"
                        onChange={handleFileUpload}
                        className="hidden"
                    />
                </label>
            </div>
        );
    }

    const { basics, work, education, skills } = resume;

    return (
        <div className="max-w-4xl mx-auto my-8">
            {/* Actions Bar */}
            <div className="flex justify-end mb-4">
                <button
                    onClick={() => {
                        setResume(null);
                        setError(null);
                    }}
                    className="flex items-center px-4 py-2 bg-white border border-slate-200 text-slate-700 rounded-lg hover:bg-slate-50 transition-colors shadow-sm font-medium text-sm"
                >
                    <Upload className="w-4 h-4 mr-2" />
                    Upload New Resume
                </button>
            </div>

            {/* Paper Sheet */}
            <div className="bg-white shadow-xl rounded-xl overflow-hidden min-h-[1100px] border border-slate-200/50">

                {/* Header */}
                <div className="bg-slate-900 text-white p-12 text-center">
                    <h1 className="text-4xl font-bold tracking-tight mb-2">{basics?.name}</h1>
                    <p className="text-xl text-slate-300 font-medium tracking-wide mb-6">{basics?.label}</p>

                    <div className="flex flex-wrap justify-center gap-6 text-sm text-slate-300">
                        {basics?.email && (
                            <div className="flex items-center gap-2">
                                <Mail className="w-4 h-4" />
                                <span>{basics.email}</span>
                            </div>
                        )}
                        {basics?.phone && (
                            <div className="flex items-center gap-2">
                                <Phone className="w-4 h-4" />
                                <span>{basics.phone}</span>
                            </div>
                        )}
                        {basics?.location?.city && (
                            <div className="flex items-center gap-2">
                                <MapPin className="w-4 h-4" />
                                <span>{basics.location.city}, {basics.location.countryCode}</span>
                            </div>
                        )}
                        {basics?.url && (
                            <div className="flex items-center gap-2">
                                <Globe className="w-4 h-4" />
                                <span>{basics.url}</span>
                            </div>
                        )}
                    </div>
                </div>

                {/* Content */}
                <div className="p-12 space-y-8">

                    {/* Summary */}
                    {basics?.summary && (
                        <section>
                            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4 border-b border-slate-100 pb-2">
                                Professional Summary
                            </h2>
                            <p className="text-slate-700 leading-relaxed text-justify">
                                {basics.summary}
                            </p>
                        </section>
                    )}

                    {/* Experience */}
                    {work && work.length > 0 && (
                        <section>
                            <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-6 border-b border-slate-100 pb-2 flex items-center gap-2">
                                <Briefcase className="w-4 h-4" /> Experience
                            </h2>
                            <div className="space-y-8">
                                {work.map((job, i) => (
                                    <div key={i}>
                                        <div className="flex justify-between items-baseline mb-2">
                                            <h3 className="text-lg font-bold text-slate-900">{job.position}</h3>
                                            <span className="text-sm text-slate-500 font-medium whitespace-nowrap">
                                                {formatDate(job.startDate)} — {formatDate(job.endDate) || 'Present'}
                                            </span>
                                        </div>
                                        <div className="text-blue-600 font-medium mb-3">{job.name}</div>
                                        {job.summary && <p className="text-slate-600 mb-2">{job.summary}</p>}
                                        {job.highlights && (
                                            <ul className="space-y-2">
                                                {job.highlights.map((highlight, j) => (
                                                    <li key={j} className="text-slate-600 text-sm leading-relaxed flex items-start">
                                                        <span className="mr-2 text-slate-400">•</span>
                                                        {highlight}
                                                    </li>
                                                ))}
                                            </ul>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </section>
                    )}

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-12">

                        {/* Education */}
                        {education && education.length > 0 && (
                            <section>
                                <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-6 border-b border-slate-100 pb-2 flex items-center gap-2">
                                    <GraduationCap className="w-4 h-4" /> Education
                                </h2>
                                <div className="space-y-6">
                                    {education.map((edu, i) => (
                                        <div key={i}>
                                            <h3 className="font-bold text-slate-900">{edu.institution}</h3>
                                            <div className="text-slate-700">{edu.studyType} in {edu.area}</div>
                                            <div className="text-sm text-slate-500 mt-1">
                                                {formatDate(edu.startDate)} — {formatDate(edu.endDate)}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </section>
                        )}

                        {/* Skills */}
                        {skills && skills.length > 0 && (
                            <section>
                                <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-6 border-b border-slate-100 pb-2 flex items-center gap-2">
                                    <Code className="w-4 h-4" /> Skills
                                </h2>
                                <div className="space-y-4">
                                    {skills.map((skill, i) => (
                                        <div key={i}>
                                            <h3 className="font-semibold text-slate-900 mb-2">{skill.name}</h3>
                                            <div className="flex flex-wrap gap-2">
                                                {skill.keywords?.map((kw, j) => (
                                                    <span key={j} className="px-2 py-1 bg-slate-100 text-slate-700 text-xs rounded-md font-medium">
                                                        {kw}
                                                    </span>
                                                ))}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </section>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};
