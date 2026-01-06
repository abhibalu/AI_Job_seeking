import React, { useState } from 'react';
import { ResumeData, Experience, Education } from '../types';
import { Plus, Trash2, GripVertical, FileJson, X, ChevronDown, ChevronRight, Briefcase, GraduationCap } from 'lucide-react';

interface EditorProps {
    data: ResumeData;
    onChange: (data: ResumeData) => void;
    onClose?: () => void;
}

export const Editor: React.FC<EditorProps> = ({ data, onChange, onClose }) => {
    const [showImport, setShowImport] = useState(false);
    const [jsonInput, setJsonInput] = useState('');

    // State for collapsible items
    const [expandedExpIds, setExpandedExpIds] = useState<string[]>([]);
    const [expandedEduIds, setExpandedEduIds] = useState<string[]>([]);

    const toggleExp = (id: string) => {
        setExpandedExpIds(prev => prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]);
    };

    const toggleEdu = (id: string) => {
        setExpandedEduIds(prev => prev.includes(id) ? prev.filter(p => p !== id) : [...prev, id]);
    };

    const handleInputChange = (field: keyof ResumeData, value: string) => {
        onChange({ ...data, [field]: value });
    };

    // --- JSON Import Logic ---
    const handleImport = () => {
        try {
            const parsed = JSON.parse(jsonInput);

            const formatLocation = (loc: any) => {
                if (!loc) return "";
                if (typeof loc === 'string') return loc;
                const parts = [loc.city, loc.region, loc.postalCode, loc.countryCode].filter(Boolean);
                return parts.join(', ');
            };

            const formatDate = (dateString: string) => {
                if (!dateString) return "";
                try {
                    const date = new Date(dateString);
                    return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
                } catch {
                    return dateString;
                }
            };

            const newData: ResumeData = {
                fullName: parsed.basics?.name || data.fullName,
                title: parsed.basics?.label || data.title,
                email: parsed.basics?.email || data.email,
                phone: parsed.basics?.phone || data.phone,
                location: formatLocation(parsed.basics?.location) || data.location,
                websites: parsed.basics?.profiles?.map((p: any) => p.url) || [],
                summary: parsed.basics?.summary || "",
                experience: parsed.work?.map((w: any) => ({
                    id: Math.random().toString(36).substr(2, 9),
                    company: w.name || "",
                    role: w.position || "",
                    period: `${formatDate(w.startDate)} - ${w.endDate ? formatDate(w.endDate) : 'Present'}`,
                    location: w.location || "",
                    achievements: w.highlights || []
                })) || [],
                education: parsed.education?.map((e: any) => ({
                    id: Math.random().toString(36).substr(2, 9),
                    institution: e.institution || "",
                    degree: `${e.studyType || ''} ${e.area || ''}`.trim(),
                    period: `${formatDate(e.startDate)} - ${e.endDate ? formatDate(e.endDate) : 'Present'}`,
                    location: ""
                })) || [],
                skills: parsed.skills?.map((s: any) => s.name) || []
            };

            onChange(newData);
            setJsonInput('');
            setShowImport(false);
            alert('Resume updated from JSON successfully!');
        } catch (e) {
            alert('Invalid JSON format. Please check your input.');
        }
    };

    // --- Websites ---
    const handleWebsiteChange = (index: number, value: string) => {
        const newWebsites = [...data.websites];
        newWebsites[index] = value;
        onChange({ ...data, websites: newWebsites });
    };

    const addWebsite = () => {
        onChange({ ...data, websites: [...data.websites, ""] });
    };

    const removeWebsite = (index: number) => {
        onChange({ ...data, websites: data.websites.filter((_, i) => i !== index) });
    };

    // --- Experience ---
    const handleExperienceChange = (id: string, field: keyof Experience, value: any) => {
        const updatedExperience = data.experience.map(exp =>
            exp.id === id ? { ...exp, [field]: value } : exp
        );
        onChange({ ...data, experience: updatedExperience });
    };

    const handleAchievementChange = (expId: string, index: number, value: string) => {
        const updatedExperience = data.experience.map(exp => {
            if (exp.id === expId) {
                const newAchievements = [...exp.achievements];
                newAchievements[index] = value;
                return { ...exp, achievements: newAchievements };
            }
            return exp;
        });
        onChange({ ...data, experience: updatedExperience });
    };

    const addAchievement = (expId: string) => {
        const updatedExperience = data.experience.map(exp => {
            if (exp.id === expId) {
                return { ...exp, achievements: [...exp.achievements, ""] };
            }
            return exp;
        });
        onChange({ ...data, experience: updatedExperience });
    };

    const removeAchievement = (expId: string, index: number) => {
        const updatedExperience = data.experience.map(exp => {
            if (exp.id === expId) {
                const newAchievements = exp.achievements.filter((_, i) => i !== index);
                return { ...exp, achievements: newAchievements };
            }
            return exp;
        });
        onChange({ ...data, experience: updatedExperience });
    };

    const addExperience = () => {
        const id = Date.now().toString();
        const newExp: Experience = {
            id,
            company: "New Company",
            role: "Role",
            period: "2024 - Present",
            location: "Location",
            achievements: ["Achievement"]
        };
        onChange({ ...data, experience: [newExp, ...data.experience] });
        setExpandedExpIds(prev => [id, ...prev]);
    };

    const removeExperience = (id: string) => {
        onChange({ ...data, experience: data.experience.filter(e => e.id !== id) });
        setExpandedExpIds(prev => prev.filter(i => i !== id));
    };

    // --- Education ---
    const handleEducationChange = (id: string, field: keyof Education, value: string) => {
        const updatedEducation = data.education.map(edu =>
            edu.id === id ? { ...edu, [field]: value } : edu
        );
        onChange({ ...data, education: updatedEducation });
    };

    const addEducation = () => {
        const id = Date.now().toString();
        const newEdu: Education = {
            id,
            institution: "Institution Name",
            degree: "Degree",
            period: "Year",
            location: "Location"
        };
        onChange({ ...data, education: [...data.education, newEdu] });
        setExpandedEduIds(prev => [id, ...prev]);
    };

    const removeEducation = (id: string) => {
        onChange({ ...data, education: data.education.filter(e => e.id !== id) });
        setExpandedEduIds(prev => prev.filter(i => i !== id));
    };

    // --- Skills ---
    const handleSkillChange = (index: number, value: string) => {
        const newSkills = [...data.skills];
        newSkills[index] = value;
        onChange({ ...data, skills: newSkills });
    };

    const addSkill = () => {
        onChange({ ...data, skills: [...data.skills, "Category: Skill 1, Skill 2"] });
    };

    const removeSkill = (index: number) => {
        onChange({ ...data, skills: data.skills.filter((_, i) => i !== index) });
    };

    return (
        <div className="h-full flex flex-col text-slate-800 bg-white/95 backdrop-blur-xl border-l border-slate-200 shadow-2xl">
            {/* Header */}
            <div className="flex justify-between items-center p-6 border-b border-slate-200 bg-white/50 backdrop-blur-md sticky top-0 z-10">
                <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                    <FileJson className="text-blue-600" />
                    Edit Profile
                </h2>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setShowImport(!showImport)}
                        className="flex items-center gap-1 text-xs bg-slate-100 text-slate-600 px-3 py-1.5 rounded-full hover:bg-slate-200 transition font-medium border border-slate-200"
                    >
                        <FileJson size={14} />
                        {showImport ? "Hide" : "Import JSON"}
                    </button>
                    {onClose && (
                        <button
                            onClick={onClose}
                            className="p-1.5 rounded-full hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition"
                        >
                            <X size={20} />
                        </button>
                    )}
                </div>
            </div>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto p-6 scrollbar-thin scrollbar-thumb-slate-200 scrollbar-track-transparent">
                {showImport && (
                    <div className="mb-8 p-4 bg-slate-50 rounded-xl border border-slate-200 animate-in fade-in slide-in-from-top-2 shadow-inner">
                        <p className="text-xs text-slate-500 mb-2">Paste JSON Resume compatible JSON below.</p>
                        <textarea
                            className="w-full h-40 p-3 text-xs font-mono bg-white border border-slate-200 rounded-lg mb-3 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none text-slate-800 shadow-sm"
                            placeholder='{ "basics": { ... } }'
                            value={jsonInput}
                            onChange={(e) => setJsonInput(e.target.value)}
                        />
                        <button
                            onClick={handleImport}
                            className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm font-semibold hover:bg-blue-500 transition shadow-lg shadow-blue-200"
                        >
                            Apply JSON Data
                        </button>
                    </div>
                )}

                {/* Section: Personal Info */}
                <div className="space-y-4 mb-8">
                    <h3 className="font-semibold text-slate-400 uppercase text-xs tracking-wider border-b border-slate-100 pb-2">Personal Information</h3>
                    <div className="grid grid-cols-1 gap-4">
                        <div className="group">
                            <label className="block text-xs text-slate-500 mb-1 group-focus-within:text-blue-600 transition-colors">Full Name</label>
                            <input
                                type="text"
                                className="w-full p-2.5 bg-white border border-slate-200 rounded-lg focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition text-sm text-slate-800 shadow-sm"
                                value={data.fullName}
                                onChange={(e) => handleInputChange('fullName', e.target.value)}
                            />
                        </div>
                        <div className="group">
                            <label className="block text-xs text-slate-500 mb-1 group-focus-within:text-blue-600 transition-colors">Job Title</label>
                            <input
                                type="text"
                                className="w-full p-2.5 bg-white border border-slate-200 rounded-lg focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition text-sm text-slate-800 shadow-sm"
                                value={data.title || ''}
                                onChange={(e) => handleInputChange('title', e.target.value)}
                            />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="group">
                                <label className="block text-xs text-slate-500 mb-1 group-focus-within:text-blue-600 transition-colors">Phone</label>
                                <input
                                    type="text"
                                    className="w-full p-2.5 bg-white border border-slate-200 rounded-lg focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition text-sm text-slate-800 shadow-sm"
                                    value={data.phone}
                                    onChange={(e) => handleInputChange('phone', e.target.value)}
                                />
                            </div>
                            <div className="group">
                                <label className="block text-xs text-slate-500 mb-1 group-focus-within:text-blue-600 transition-colors">Email</label>
                                <input
                                    type="email"
                                    className="w-full p-2.5 bg-white border border-slate-200 rounded-lg focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition text-sm text-slate-800 shadow-sm"
                                    value={data.email}
                                    onChange={(e) => handleInputChange('email', e.target.value)}
                                />
                            </div>
                        </div>
                        <div className="group">
                            <label className="block text-xs text-slate-500 mb-1 group-focus-within:text-blue-600 transition-colors">Location</label>
                            <input
                                type="text"
                                className="w-full p-2.5 bg-white border border-slate-200 rounded-lg focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition text-sm text-slate-800 shadow-sm"
                                value={data.location}
                                onChange={(e) => handleInputChange('location', e.target.value)}
                            />
                        </div>

                        {/* Websites */}
                        <div className="space-y-2 pt-2">
                            <label className="block text-xs text-slate-500 mb-1">Links / Websites</label>
                            {data.websites.map((site, idx) => (
                                <div key={idx} className="flex gap-2">
                                    <input
                                        type="text"
                                        placeholder="https://..."
                                        className="w-full p-2.5 bg-white border border-slate-200 rounded-lg focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition text-sm text-slate-800 shadow-sm"
                                        value={site}
                                        onChange={(e) => handleWebsiteChange(idx, e.target.value)}
                                    />
                                    <button
                                        onClick={() => removeWebsite(idx)}
                                        className="p-2 text-slate-400 hover:text-rose-500 transition"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                </div>
                            ))}
                            <button onClick={addWebsite} className="text-xs font-medium text-blue-600 hover:text-blue-500 flex items-center gap-1 mt-1 transition-colors">
                                <Plus size={12} /> Add Link
                            </button>
                        </div>

                        <div className="pt-2 group">
                            <label className="block text-xs text-slate-500 mb-1 group-focus-within:text-blue-600 transition-colors">Professional Summary</label>
                            <textarea
                                rows={4}
                                className="w-full p-2.5 bg-white border border-slate-200 rounded-lg focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition text-sm text-slate-800 shadow-sm resize-none"
                                value={data.summary || ''}
                                onChange={(e) => handleInputChange('summary', e.target.value)}
                            />
                        </div>
                    </div>
                </div>

                {/* Section: Experience */}
                <div className="space-y-4 mb-8">
                    <div className="flex justify-between items-center border-b border-slate-100 pb-2">
                        <h3 className="font-semibold text-slate-400 uppercase text-xs tracking-wider">Experience</h3>
                        <button
                            onClick={addExperience}
                            className="flex items-center gap-1 text-xs bg-blue-50 text-blue-600 border border-blue-100 px-2 py-1 rounded hover:bg-blue-100 transition font-medium"
                        >
                            <Plus size={12} /> Add
                        </button>
                    </div>

                    <div className="space-y-3">
                        {data.experience.map((exp) => {
                            const isExpanded = expandedExpIds.includes(exp.id);
                            return (
                                <div key={exp.id} className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden transition-all duration-300 hover:shadow-md">
                                    {/* Collapsible Header */}
                                    <div
                                        className="flex items-center justify-between p-3.5 cursor-pointer hover:bg-slate-50 transition-colors group"
                                        onClick={() => toggleExp(exp.id)}
                                    >
                                        <div className="flex items-center gap-3 overflow-hidden">
                                            <div className={`p-2 rounded-lg transition-colors duration-300 ${isExpanded ? 'bg-blue-100 text-blue-600' : 'bg-slate-100 text-slate-500'}`}>
                                                <Briefcase size={16} />
                                            </div>
                                            <div className="flex flex-col truncate pr-2">
                                                <span className="text-sm font-semibold text-slate-800 truncate group-hover:text-blue-600 transition-colors">{exp.company || 'New Company'}</span>
                                                <span className="text-[10px] text-slate-500 truncate uppercase tracking-wide">{exp.role || 'Role'}</span>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <button
                                                onClick={(e) => { e.stopPropagation(); removeExperience(exp.id); }}
                                                className="p-2 text-slate-400 hover:text-rose-500 hover:bg-rose-50 rounded-lg transition opacity-0 group-hover:opacity-100"
                                                title="Delete"
                                            >
                                                <Trash2 size={15} />
                                            </button>
                                            {isExpanded ? <ChevronDown size={16} className="text-slate-400" /> : <ChevronRight size={16} className="text-slate-400" />}
                                        </div>
                                    </div>

                                    {/* Collapsible Content */}
                                    {isExpanded && (
                                        <div className="p-4 border-t border-slate-100 bg-slate-50/50 animate-in slide-in-from-top-2">
                                            <div className="grid grid-cols-1 gap-3 mb-4">
                                                <div>
                                                    <label className="block text-[10px] text-slate-400 mb-0.5 uppercase">Role</label>
                                                    <input
                                                        type="text"
                                                        className="w-full p-2 bg-white border border-slate-200 rounded text-sm font-medium focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none text-slate-800 transition-colors"
                                                        value={exp.role}
                                                        onChange={(e) => handleExperienceChange(exp.id, 'role', e.target.value)}
                                                    />
                                                </div>
                                                <div>
                                                    <label className="block text-[10px] text-slate-400 mb-0.5 uppercase">Company</label>
                                                    <input
                                                        type="text"
                                                        className="w-full p-2 bg-white border border-slate-200 rounded text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none text-slate-800 transition-colors"
                                                        value={exp.company}
                                                        onChange={(e) => handleExperienceChange(exp.id, 'company', e.target.value)}
                                                    />
                                                </div>
                                                <div className="grid grid-cols-2 gap-3">
                                                    <div>
                                                        <label className="block text-[10px] text-slate-400 mb-0.5 uppercase">Period</label>
                                                        <input
                                                            type="text"
                                                            className="w-full p-2 bg-white border border-slate-200 rounded text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none text-slate-800 transition-colors"
                                                            value={exp.period}
                                                            onChange={(e) => handleExperienceChange(exp.id, 'period', e.target.value)}
                                                        />
                                                    </div>
                                                    <div>
                                                        <label className="block text-[10px] text-slate-400 mb-0.5 uppercase">Location</label>
                                                        <input
                                                            type="text"
                                                            className="w-full p-2 bg-white border border-slate-200 rounded text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none text-slate-800 transition-colors"
                                                            value={exp.location || ''}
                                                            onChange={(e) => handleExperienceChange(exp.id, 'location', e.target.value)}
                                                        />
                                                    </div>
                                                </div>
                                            </div>

                                            <div className="space-y-2">
                                                <p className="text-[10px] font-semibold text-slate-400 uppercase">Achievements</p>
                                                {exp.achievements.map((ach, idx) => (
                                                    <div key={idx} className="flex gap-2 items-start group/ach">
                                                        <div className="mt-2 text-slate-300"><GripVertical size={14} /></div>
                                                        <textarea
                                                            rows={2}
                                                            className="w-full p-2 bg-white border border-slate-200 rounded text-sm resize-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none text-slate-800 transition-colors"
                                                            value={ach}
                                                            onChange={(e) => handleAchievementChange(exp.id, idx, e.target.value)}
                                                        />
                                                        <button
                                                            onClick={() => removeAchievement(exp.id, idx)}
                                                            className="mt-2 text-slate-300 hover:text-rose-500 transition opacity-0 group-hover/ach:opacity-100"
                                                        >
                                                            <Trash2 size={14} />
                                                        </button>
                                                    </div>
                                                ))}
                                                <button
                                                    onClick={() => addAchievement(exp.id)}
                                                    className="text-xs font-medium text-blue-600 hover:text-blue-500 flex items-center gap-1 mt-2 transition-colors"
                                                >
                                                    <Plus size={12} /> Add Achievement
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Section: Education */}
                <div className="space-y-4 mb-8">
                    <div className="flex justify-between items-center border-b border-slate-100 pb-2">
                        <h3 className="font-semibold text-slate-400 uppercase text-xs tracking-wider">Education</h3>
                        <button
                            onClick={addEducation}
                            className="flex items-center gap-1 text-xs bg-blue-50 text-blue-600 border border-blue-100 px-2 py-1 rounded hover:bg-blue-100 transition font-medium"
                        >
                            <Plus size={12} /> Add
                        </button>
                    </div>

                    <div className="space-y-3">
                        {data.education.map((edu) => {
                            const isExpanded = expandedEduIds.includes(edu.id);
                            return (
                                <div key={edu.id} className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden transition-all duration-300 hover:shadow-md">
                                    <div
                                        className="flex items-center justify-between p-3.5 cursor-pointer hover:bg-slate-50 transition-colors group"
                                        onClick={() => toggleEdu(edu.id)}
                                    >
                                        <div className="flex items-center gap-3 overflow-hidden">
                                            <div className={`p-2 rounded-lg transition-colors duration-300 ${isExpanded ? 'bg-blue-100 text-blue-600' : 'bg-slate-100 text-slate-500'}`}>
                                                <GraduationCap size={16} />
                                            </div>
                                            <div className="flex flex-col truncate pr-2">
                                                <span className="text-sm font-semibold text-slate-800 truncate group-hover:text-blue-600 transition-colors">{edu.degree || 'Degree'}</span>
                                                <span className="text-[10px] text-slate-500 truncate uppercase tracking-wide">{edu.institution || 'Institution'}</span>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <button
                                                onClick={(e) => { e.stopPropagation(); removeEducation(edu.id); }}
                                                className="p-2 text-slate-400 hover:text-rose-500 hover:bg-rose-50 rounded-lg transition opacity-0 group-hover:opacity-100"
                                            >
                                                <Trash2 size={15} />
                                            </button>
                                            {isExpanded ? <ChevronDown size={16} className="text-slate-400" /> : <ChevronRight size={16} className="text-slate-400" />}
                                        </div>
                                    </div>

                                    {isExpanded && (
                                        <div className="p-4 border-t border-slate-100 bg-slate-50/50 animate-in slide-in-from-top-2">
                                            <div className="grid grid-cols-1 gap-3">
                                                <div>
                                                    <label className="block text-[10px] text-slate-400 mb-0.5 uppercase">Degree</label>
                                                    <input
                                                        type="text"
                                                        className="w-full p-2 bg-white border border-slate-200 rounded text-sm font-medium focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none text-slate-800 transition-colors"
                                                        value={edu.degree}
                                                        onChange={(e) => handleEducationChange(edu.id, 'degree', e.target.value)}
                                                    />
                                                </div>
                                                <div>
                                                    <label className="block text-[10px] text-slate-400 mb-0.5 uppercase">Institution</label>
                                                    <input
                                                        type="text"
                                                        className="w-full p-2 bg-white border border-slate-200 rounded text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none text-slate-800 transition-colors"
                                                        value={edu.institution}
                                                        onChange={(e) => handleEducationChange(edu.id, 'institution', e.target.value)}
                                                    />
                                                </div>
                                                <div className="grid grid-cols-2 gap-3">
                                                    <div>
                                                        <label className="block text-[10px] text-slate-400 mb-0.5 uppercase">Period</label>
                                                        <input
                                                            type="text"
                                                            className="w-full p-2 bg-white border border-slate-200 rounded text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none text-slate-800 transition-colors"
                                                            value={edu.period}
                                                            onChange={(e) => handleEducationChange(edu.id, 'period', e.target.value)}
                                                        />
                                                    </div>
                                                    <div>
                                                        <label className="block text-[10px] text-slate-400 mb-0.5 uppercase">Location</label>
                                                        <input
                                                            type="text"
                                                            className="w-full p-2 bg-white border border-slate-200 rounded text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none text-slate-800 transition-colors"
                                                            value={edu.location}
                                                            onChange={(e) => handleEducationChange(edu.id, 'location', e.target.value)}
                                                        />
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Section: Skills */}
                <div className="space-y-4">
                    <div className="flex justify-between items-center border-b border-slate-100 pb-2">
                        <h3 className="font-semibold text-slate-400 uppercase text-xs tracking-wider">Skills</h3>
                        <button
                            onClick={addSkill}
                            className="flex items-center gap-1 text-xs bg-blue-50 text-blue-600 border border-blue-100 px-2 py-1 rounded hover:bg-blue-100 transition font-medium"
                        >
                            <Plus size={12} /> Add
                        </button>
                    </div>

                    <div className="space-y-3">
                        {data.skills.map((skill, idx) => (
                            <div key={idx} className="flex gap-2 items-center group">
                                <input
                                    type="text"
                                    className="w-full p-2.5 bg-white border border-slate-200 rounded-lg focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition text-sm text-slate-800 shadow-sm"
                                    value={skill}
                                    onChange={(e) => handleSkillChange(idx, e.target.value)}
                                />
                                <button
                                    onClick={() => removeSkill(idx)}
                                    className="p-2 text-slate-400 hover:text-rose-500 transition"
                                >
                                    <Trash2 size={16} />
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};
