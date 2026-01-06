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
        <div className="h-full flex flex-col text-white">
            {/* Header */}
            <div className="flex justify-between items-center p-6 border-b border-white/10 bg-[#0f172a]/50 backdrop-blur-md sticky top-0 z-10">
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                    <FileJson className="text-pink-500" />
                    Edit Profile
                </h2>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => setShowImport(!showImport)}
                        className="flex items-center gap-1 text-xs bg-white/10 text-white/80 px-3 py-1.5 rounded-full hover:bg-white/20 transition font-medium border border-white/10"
                    >
                        <FileJson size={14} />
                        {showImport ? "Hide" : "Import JSON"}
                    </button>
                    {onClose && (
                        <button
                            onClick={onClose}
                            className="p-1.5 rounded-full hover:bg-white/10 text-white/60 hover:text-white transition"
                        >
                            <X size={20} />
                        </button>
                    )}
                </div>
            </div>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto p-6 scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent">
                {showImport && (
                    <div className="mb-8 p-4 bg-black/30 rounded-xl border border-white/10 animate-in fade-in slide-in-from-top-2">
                        <p className="text-xs text-white/50 mb-2">Paste JSON Resume compatible JSON below.</p>
                        <textarea
                            className="w-full h-40 p-3 text-xs font-mono bg-black/40 border border-white/10 rounded-lg mb-3 focus:border-pink-500 focus:ring-1 focus:ring-pink-500 outline-none text-white/90"
                            placeholder='{ "basics": { ... } }'
                            value={jsonInput}
                            onChange={(e) => setJsonInput(e.target.value)}
                        />
                        <button
                            onClick={handleImport}
                            className="w-full bg-pink-600 text-white py-2 rounded-lg text-sm font-semibold hover:bg-pink-500 transition shadow-lg shadow-pink-900/40"
                        >
                            Apply JSON Data
                        </button>
                    </div>
                )}

                {/* Section: Personal Info */}
                <div className="space-y-4 mb-8">
                    <h3 className="font-semibold text-white/40 uppercase text-xs tracking-wider border-b border-white/10 pb-2">Personal Information</h3>
                    <div className="grid grid-cols-1 gap-4">
                        <div className="group">
                            <label className="block text-xs text-white/50 mb-1 group-focus-within:text-pink-400 transition-colors">Full Name</label>
                            <input
                                type="text"
                                className="w-full p-2.5 bg-white/5 border border-white/10 rounded-lg focus:bg-white/10 focus:border-pink-500/50 focus:ring-1 focus:ring-pink-500/50 outline-none transition text-sm text-white"
                                value={data.fullName}
                                onChange={(e) => handleInputChange('fullName', e.target.value)}
                            />
                        </div>
                        <div className="group">
                            <label className="block text-xs text-white/50 mb-1 group-focus-within:text-pink-400 transition-colors">Job Title</label>
                            <input
                                type="text"
                                className="w-full p-2.5 bg-white/5 border border-white/10 rounded-lg focus:bg-white/10 focus:border-pink-500/50 focus:ring-1 focus:ring-pink-500/50 outline-none transition text-sm text-white"
                                value={data.title || ''}
                                onChange={(e) => handleInputChange('title', e.target.value)}
                            />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div className="group">
                                <label className="block text-xs text-white/50 mb-1 group-focus-within:text-pink-400 transition-colors">Phone</label>
                                <input
                                    type="text"
                                    className="w-full p-2.5 bg-white/5 border border-white/10 rounded-lg focus:bg-white/10 focus:border-pink-500/50 focus:ring-1 focus:ring-pink-500/50 outline-none transition text-sm text-white"
                                    value={data.phone}
                                    onChange={(e) => handleInputChange('phone', e.target.value)}
                                />
                            </div>
                            <div className="group">
                                <label className="block text-xs text-white/50 mb-1 group-focus-within:text-pink-400 transition-colors">Email</label>
                                <input
                                    type="email"
                                    className="w-full p-2.5 bg-white/5 border border-white/10 rounded-lg focus:bg-white/10 focus:border-pink-500/50 focus:ring-1 focus:ring-pink-500/50 outline-none transition text-sm text-white"
                                    value={data.email}
                                    onChange={(e) => handleInputChange('email', e.target.value)}
                                />
                            </div>
                        </div>
                        <div className="group">
                            <label className="block text-xs text-white/50 mb-1 group-focus-within:text-pink-400 transition-colors">Location</label>
                            <input
                                type="text"
                                className="w-full p-2.5 bg-white/5 border border-white/10 rounded-lg focus:bg-white/10 focus:border-pink-500/50 focus:ring-1 focus:ring-pink-500/50 outline-none transition text-sm text-white"
                                value={data.location}
                                onChange={(e) => handleInputChange('location', e.target.value)}
                            />
                        </div>

                        {/* Websites */}
                        <div className="space-y-2 pt-2">
                            <label className="block text-xs text-white/50 mb-1">Links / Websites</label>
                            {data.websites.map((site, idx) => (
                                <div key={idx} className="flex gap-2">
                                    <input
                                        type="text"
                                        placeholder="https://..."
                                        className="w-full p-2.5 bg-white/5 border border-white/10 rounded-lg focus:bg-white/10 focus:border-pink-500/50 outline-none transition text-sm text-white"
                                        value={site}
                                        onChange={(e) => handleWebsiteChange(idx, e.target.value)}
                                    />
                                    <button
                                        onClick={() => removeWebsite(idx)}
                                        className="p-2 text-white/40 hover:text-red-400 transition"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                </div>
                            ))}
                            <button onClick={addWebsite} className="text-xs font-medium text-pink-400 hover:text-pink-300 flex items-center gap-1 mt-1 transition-colors">
                                <Plus size={12} /> Add Link
                            </button>
                        </div>

                        <div className="pt-2 group">
                            <label className="block text-xs text-white/50 mb-1 group-focus-within:text-pink-400 transition-colors">Professional Summary</label>
                            <textarea
                                rows={4}
                                className="w-full p-2.5 bg-white/5 border border-white/10 rounded-lg focus:bg-white/10 focus:border-pink-500/50 outline-none transition text-sm text-white resize-none"
                                value={data.summary || ''}
                                onChange={(e) => handleInputChange('summary', e.target.value)}
                            />
                        </div>
                    </div>
                </div>

                {/* Section: Experience */}
                <div className="space-y-4 mb-8">
                    <div className="flex justify-between items-center border-b border-white/10 pb-2">
                        <h3 className="font-semibold text-white/40 uppercase text-xs tracking-wider">Experience</h3>
                        <button
                            onClick={addExperience}
                            className="flex items-center gap-1 text-xs bg-pink-500/10 text-pink-400 border border-pink-500/20 px-2 py-1 rounded hover:bg-pink-500/20 transition font-medium"
                        >
                            <Plus size={12} /> Add
                        </button>
                    </div>

                    <div className="space-y-3">
                        {data.experience.map((exp) => {
                            const isExpanded = expandedExpIds.includes(exp.id);
                            return (
                                <div key={exp.id} className="bg-white/5 rounded-xl border border-white/5 overflow-hidden transition-all duration-300">
                                    {/* Collapsible Header */}
                                    <div
                                        className="flex items-center justify-between p-3.5 cursor-pointer hover:bg-white/10 transition-colors group"
                                        onClick={() => toggleExp(exp.id)}
                                    >
                                        <div className="flex items-center gap-3 overflow-hidden">
                                            <div className={`p-2 rounded-lg transition-colors duration-300 ${isExpanded ? 'bg-pink-500/20 text-pink-400' : 'bg-white/5 text-white/40'}`}>
                                                <Briefcase size={16} />
                                            </div>
                                            <div className="flex flex-col truncate pr-2">
                                                <span className="text-sm font-semibold text-white truncate group-hover:text-pink-200 transition-colors">{exp.company || 'New Company'}</span>
                                                <span className="text-[10px] text-white/50 truncate uppercase tracking-wide">{exp.role || 'Role'}</span>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <button
                                                onClick={(e) => { e.stopPropagation(); removeExperience(exp.id); }}
                                                className="p-2 text-white/20 hover:text-red-400 hover:bg-white/5 rounded-lg transition opacity-0 group-hover:opacity-100"
                                                title="Delete"
                                            >
                                                <Trash2 size={15} />
                                            </button>
                                            {isExpanded ? <ChevronDown size={16} className="text-white/40" /> : <ChevronRight size={16} className="text-white/40" />}
                                        </div>
                                    </div>

                                    {/* Collapsible Content */}
                                    {isExpanded && (
                                        <div className="p-4 border-t border-white/5 bg-black/20 animate-in slide-in-from-top-2">
                                            <div className="grid grid-cols-1 gap-3 mb-4">
                                                <div>
                                                    <label className="block text-[10px] text-white/40 mb-0.5 uppercase">Role</label>
                                                    <input
                                                        type="text"
                                                        className="w-full p-2 bg-white/5 border border-white/10 rounded text-sm font-medium focus:bg-black/40 focus:border-pink-500/50 outline-none text-white transition-colors"
                                                        value={exp.role}
                                                        onChange={(e) => handleExperienceChange(exp.id, 'role', e.target.value)}
                                                    />
                                                </div>
                                                <div>
                                                    <label className="block text-[10px] text-white/40 mb-0.5 uppercase">Company</label>
                                                    <input
                                                        type="text"
                                                        className="w-full p-2 bg-white/5 border border-white/10 rounded text-sm focus:bg-black/40 focus:border-pink-500/50 outline-none text-white transition-colors"
                                                        value={exp.company}
                                                        onChange={(e) => handleExperienceChange(exp.id, 'company', e.target.value)}
                                                    />
                                                </div>
                                                <div className="grid grid-cols-2 gap-3">
                                                    <div>
                                                        <label className="block text-[10px] text-white/40 mb-0.5 uppercase">Period</label>
                                                        <input
                                                            type="text"
                                                            className="w-full p-2 bg-white/5 border border-white/10 rounded text-sm focus:bg-black/40 focus:border-pink-500/50 outline-none text-white transition-colors"
                                                            value={exp.period}
                                                            onChange={(e) => handleExperienceChange(exp.id, 'period', e.target.value)}
                                                        />
                                                    </div>
                                                    <div>
                                                        <label className="block text-[10px] text-white/40 mb-0.5 uppercase">Location</label>
                                                        <input
                                                            type="text"
                                                            className="w-full p-2 bg-white/5 border border-white/10 rounded text-sm focus:bg-black/40 focus:border-pink-500/50 outline-none text-white transition-colors"
                                                            value={exp.location || ''}
                                                            onChange={(e) => handleExperienceChange(exp.id, 'location', e.target.value)}
                                                        />
                                                    </div>
                                                </div>
                                            </div>

                                            <div className="space-y-2">
                                                <p className="text-[10px] font-semibold text-white/40 uppercase">Achievements</p>
                                                {exp.achievements.map((ach, idx) => (
                                                    <div key={idx} className="flex gap-2 items-start group/ach">
                                                        <div className="mt-2 text-white/20"><GripVertical size={14} /></div>
                                                        <textarea
                                                            rows={2}
                                                            className="w-full p-2 bg-white/5 border border-white/10 rounded text-sm resize-none focus:bg-black/40 focus:border-pink-500/50 outline-none text-white transition-colors"
                                                            value={ach}
                                                            onChange={(e) => handleAchievementChange(exp.id, idx, e.target.value)}
                                                        />
                                                        <button
                                                            onClick={() => removeAchievement(exp.id, idx)}
                                                            className="mt-2 text-white/20 hover:text-red-400 transition opacity-0 group-hover/ach:opacity-100"
                                                        >
                                                            <Trash2 size={14} />
                                                        </button>
                                                    </div>
                                                ))}
                                                <button
                                                    onClick={() => addAchievement(exp.id)}
                                                    className="text-xs font-medium text-pink-400 hover:text-pink-300 flex items-center gap-1 mt-2 transition-colors"
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
                    <div className="flex justify-between items-center border-b border-white/10 pb-2">
                        <h3 className="font-semibold text-white/40 uppercase text-xs tracking-wider">Education</h3>
                        <button
                            onClick={addEducation}
                            className="flex items-center gap-1 text-xs bg-pink-500/10 text-pink-400 border border-pink-500/20 px-2 py-1 rounded hover:bg-pink-500/20 transition font-medium"
                        >
                            <Plus size={12} /> Add
                        </button>
                    </div>

                    <div className="space-y-3">
                        {data.education.map((edu) => {
                            const isExpanded = expandedEduIds.includes(edu.id);
                            return (
                                <div key={edu.id} className="bg-white/5 rounded-xl border border-white/5 overflow-hidden transition-all duration-300">
                                    <div
                                        className="flex items-center justify-between p-3.5 cursor-pointer hover:bg-white/10 transition-colors group"
                                        onClick={() => toggleEdu(edu.id)}
                                    >
                                        <div className="flex items-center gap-3 overflow-hidden">
                                            <div className={`p-2 rounded-lg transition-colors duration-300 ${isExpanded ? 'bg-pink-500/20 text-pink-400' : 'bg-white/5 text-white/40'}`}>
                                                <GraduationCap size={16} />
                                            </div>
                                            <div className="flex flex-col truncate pr-2">
                                                <span className="text-sm font-semibold text-white truncate group-hover:text-pink-200 transition-colors">{edu.degree || 'Degree'}</span>
                                                <span className="text-[10px] text-white/50 truncate uppercase tracking-wide">{edu.institution || 'Institution'}</span>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <button
                                                onClick={(e) => { e.stopPropagation(); removeEducation(edu.id); }}
                                                className="p-2 text-white/20 hover:text-red-400 hover:bg-white/5 rounded-lg transition opacity-0 group-hover:opacity-100"
                                            >
                                                <Trash2 size={15} />
                                            </button>
                                            {isExpanded ? <ChevronDown size={16} className="text-white/40" /> : <ChevronRight size={16} className="text-white/40" />}
                                        </div>
                                    </div>

                                    {isExpanded && (
                                        <div className="p-4 border-t border-white/5 bg-black/20 animate-in slide-in-from-top-2">
                                            <div className="grid grid-cols-1 gap-3">
                                                <div>
                                                    <label className="block text-[10px] text-white/40 mb-0.5 uppercase">Degree</label>
                                                    <input
                                                        type="text"
                                                        className="w-full p-2 bg-white/5 border border-white/10 rounded text-sm font-medium focus:bg-black/40 focus:border-pink-500/50 outline-none text-white transition-colors"
                                                        value={edu.degree}
                                                        onChange={(e) => handleEducationChange(edu.id, 'degree', e.target.value)}
                                                    />
                                                </div>
                                                <div>
                                                    <label className="block text-[10px] text-white/40 mb-0.5 uppercase">Institution</label>
                                                    <input
                                                        type="text"
                                                        className="w-full p-2 bg-white/5 border border-white/10 rounded text-sm focus:bg-black/40 focus:border-pink-500/50 outline-none text-white transition-colors"
                                                        value={edu.institution}
                                                        onChange={(e) => handleEducationChange(edu.id, 'institution', e.target.value)}
                                                    />
                                                </div>
                                                <div className="grid grid-cols-2 gap-3">
                                                    <div>
                                                        <label className="block text-[10px] text-white/40 mb-0.5 uppercase">Period</label>
                                                        <input
                                                            type="text"
                                                            className="w-full p-2 bg-white/5 border border-white/10 rounded text-sm focus:bg-black/40 focus:border-pink-500/50 outline-none text-white transition-colors"
                                                            value={edu.period}
                                                            onChange={(e) => handleEducationChange(edu.id, 'period', e.target.value)}
                                                        />
                                                    </div>
                                                    <div>
                                                        <label className="block text-[10px] text-white/40 mb-0.5 uppercase">Location</label>
                                                        <input
                                                            type="text"
                                                            className="w-full p-2 bg-white/5 border border-white/10 rounded text-sm focus:bg-black/40 focus:border-pink-500/50 outline-none text-white transition-colors"
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
                    <div className="flex justify-between items-center border-b border-white/10 pb-2">
                        <h3 className="font-semibold text-white/40 uppercase text-xs tracking-wider">Skills</h3>
                        <button
                            onClick={addSkill}
                            className="flex items-center gap-1 text-xs bg-pink-500/10 text-pink-400 border border-pink-500/20 px-2 py-1 rounded hover:bg-pink-500/20 transition font-medium"
                        >
                            <Plus size={12} /> Add
                        </button>
                    </div>

                    <div className="space-y-3">
                        {data.skills.map((skill, idx) => (
                            <div key={idx} className="flex gap-2 items-center group">
                                <input
                                    type="text"
                                    className="w-full p-2.5 bg-white/5 border border-white/10 rounded-lg focus:bg-white/10 focus:border-pink-500/50 outline-none transition text-sm text-white"
                                    value={skill}
                                    onChange={(e) => handleSkillChange(idx, e.target.value)}
                                />
                                <button
                                    onClick={() => removeSkill(idx)}
                                    className="p-2 text-white/20 hover:text-red-400 transition"
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
