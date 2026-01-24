import { useState, useCallback, useEffect, useRef } from 'react';
import apiClient from '../services/apiClient';
import { ResumeData, INITIAL_DATA, TemplateType } from '../types';

export const useResumeState = () => {
    const [resumeData, setResumeData] = useState<ResumeData>(INITIAL_DATA);
    const [isResumeLoading, setIsResumeLoading] = useState(false);
    const [isUploading, setIsUploading] = useState(false);
    const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const fetchResume = useCallback(async () => {
        try {
            setIsResumeLoading(true);
            const backendData = await apiClient.getMasterResume();

            if (backendData.status === 'processing') return true; // Keep polling

            if (backendData.status === 'error') {
                console.error("Resume parsing error:", backendData.error);
                alert(`Resume parsing failed: ${backendData.error}\n\nPlease try again.`);
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
                setIsUploading(false);
            }
            return false;
        } catch (err) {
            console.error("Failed to load resume", err);
            return false;
        } finally {
            setIsResumeLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchResume();
    }, [fetchResume]);

    const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (!file) return;

        setIsUploading(true);
        setIsResumeLoading(true);

        try {
            await apiClient.uploadResume(file);

            // Start polling
            const pollInterval = setInterval(async () => {
                const serverStillProcessing = await fetchResume();
                if (!serverStillProcessing) {
                    clearInterval(pollInterval);
                    setIsUploading(false);
                }
            }, 2000);

            // Timeout after 60s
            setTimeout(() => {
                clearInterval(pollInterval);
                setIsUploading(false);
                setIsResumeLoading(false);
            }, 60000);

        } catch (error) {
            console.error("Upload failed", error);
            setIsUploading(false);
            setIsResumeLoading(false);
            alert("Failed to upload resume.");
        } finally {
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    const generatePdf = async (template: TemplateType) => {
        setIsGeneratingPdf(true);
        try {
            const blob = await apiClient.generatePdf(resumeData, template);
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
            alert("Failed to generate PDF.");
        } finally {
            setIsGeneratingPdf(false);
        }
    };

    return {
        resumeData,
        setResumeData,
        isResumeLoading,
        isUploading,
        isGeneratingPdf,
        fileInputRef,
        handleFileUpload,
        generatePdf
    };
};
