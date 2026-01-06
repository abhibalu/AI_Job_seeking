import React from 'react';
import { ResumeData } from '../types';

export type TemplateType = 'modern' | 'classic' | 'compact' | 'tech' | 'minimal';

interface ResumePreviewProps {
    data: ResumeData;
    targetRef?: React.RefObject<HTMLDivElement>;
    template?: TemplateType;
}

export const ResumePreview: React.FC<ResumePreviewProps> = ({ data, targetRef, template = 'modern' }) => {

    // --- Style Configurations ---
    const styles = {
        modern: {
            container: "font-roboto text-gray-800 p-8 sm:p-12",
            header: "flex flex-col items-center text-center mb-6",
            name: "text-3xl sm:text-4xl font-bold text-gray-900 uppercase tracking-wide mb-2",
            title: "text-xl text-gray-700 font-medium mb-3",
            contactBar: "text-sm text-gray-600 flex flex-wrap justify-center gap-x-3 gap-y-1 mb-2 font-medium",
            separator: "w-16 h-1 bg-gray-200 mx-auto mb-6 rounded-full",
            sectionTitle: "text-xs font-bold text-gray-400 uppercase tracking-[0.15em] mb-4 border-b border-gray-100 pb-2",
            expItem: "relative pl-4 border-l-2 border-gray-100 mb-5",
            expRole: "font-bold text-md text-gray-900 uppercase",
            expCompany: "font-normal text-gray-500 mx-1",
            expDate: "text-xs font-semibold text-gray-500 uppercase tracking-wide whitespace-nowrap bg-gray-50 px-2 py-0.5 rounded",
            skillsLayout: "grid grid-cols-1 gap-y-1",
        },
        classic: {
            container: "font-serif text-gray-900 p-10 sm:p-14 leading-relaxed",
            header: "text-center mb-8 border-b-2 border-gray-900 pb-6",
            name: "text-4xl font-serif font-bold text-gray-900 mb-2",
            title: "text-lg italic text-gray-700 mb-2",
            contactBar: "text-sm font-serif text-gray-700 flex flex-wrap justify-center gap-x-4",
            separator: "hidden",
            sectionTitle: "text-lg font-serif font-bold text-gray-900 uppercase border-b border-gray-300 mb-4 pb-1 mt-6",
            expItem: "mb-6",
            expRole: "font-bold text-lg text-gray-900",
            expCompany: "italic text-gray-700",
            expDate: "text-sm font-serif italic text-gray-600 float-right",
            skillsLayout: "flex flex-wrap gap-x-6 gap-y-2",
        },
        compact: {
            container: "font-roboto text-gray-900 p-6 sm:p-8 text-sm",
            header: "flex flex-row justify-between items-start mb-4 border-b border-gray-300 pb-4",
            name: "text-2xl font-bold text-gray-900 uppercase leading-none mb-1",
            title: "text-sm font-semibold text-gray-600 uppercase tracking-wider",
            contactBar: "text-xs text-gray-600 flex flex-col items-end gap-0.5",
            separator: "hidden",
            sectionTitle: "text-sm font-bold text-gray-800 uppercase bg-gray-100 px-2 py-1 mb-2 mt-4",
            expItem: "mb-3",
            expRole: "font-bold text-sm text-gray-900",
            expCompany: "text-gray-700 font-medium",
            expDate: "text-xs text-gray-500 float-right font-mono",
            skillsLayout: "text-xs",
        },
        tech: {
            container: "font-mono text-gray-800 p-8 sm:p-10 text-sm",
            header: "mb-6",
            name: "text-3xl font-bold text-blue-900 mb-1 tracking-tighter",
            title: "text-md text-blue-600 font-medium mb-3",
            contactBar: "text-xs text-gray-500 grid grid-cols-2 sm:grid-cols-4 gap-2 border-y border-gray-100 py-2",
            separator: "hidden",
            sectionTitle: "text-sm font-bold text-blue-800 uppercase tracking-widest mb-3 mt-6 flex items-center gap-2 before:content-['#'] before:text-blue-400",
            expItem: "mb-5 pl-0",
            expRole: "font-bold text-gray-900",
            expCompany: "text-blue-700",
            expDate: "text-xs text-gray-400 block sm:inline sm:ml-2",
            skillsLayout: "flex flex-wrap gap-2",
        },
        minimal: {
            // Replaced with "Traditional / Ivy League" style
            container: "font-serif text-black p-10 sm:p-12 max-w-[210mm] mx-auto leading-normal",
            header: "text-center mb-6",
            name: "text-3xl font-bold text-black mb-2 uppercase tracking-wide font-serif",
            title: "hidden", // Usually traditional resumes don't have a title under name, just contact
            contactBar: "text-sm text-black flex flex-wrap justify-center gap-x-2 font-serif",
            separator: "hidden",
            sectionTitle: "text-md font-bold text-black uppercase tracking-wider border-b border-black mb-3 mt-5 pb-0.5 font-serif",
            expItem: "mb-4",
            expRole: "font-bold text-black font-serif",
            expCompany: "italic text-black font-serif",
            expDate: "text-black font-serif",
            skillsLayout: "grid grid-cols-1 gap-y-1",
        }
    };

    const activeStyle = styles[template];

    return (
        <div className="relative group perspective-1000 print:perspective-none w-full flex justify-center print:block print:w-auto">

            {/* Visual Depth/Shadow (Screen only) */}
            <div className="absolute inset-0 bg-black/40 blur-2xl transform translate-y-8 scale-95 rounded-[20px] -z-10 print:hidden transition-all duration-500 group-hover:translate-y-12 group-hover:blur-3xl group-hover:scale-90 opacity-60"></div>

            <div
                ref={targetRef}
                className={`
          bg-white 
          w-full max-w-[210mm] min-h-[297mm] 
          shadow-2xl 
          print:shadow-none print:w-full print:max-w-none print:min-h-0 print:p-0 print:overflow-visible
          relative
          z-10
          transition-transform duration-500
          group-hover:-translate-y-2
          ${activeStyle.container}
        `}
            >
                {/* --- HEADER --- */}
                <header className={activeStyle.header}>
                    {template === 'compact' ? (
                        // Compact Header Layout
                        <>
                            <div>
                                <h1 className={activeStyle.name}>{data.fullName}</h1>
                                {data.title && <p className={activeStyle.title}>{data.title}</p>}
                            </div>
                            <div className={activeStyle.contactBar}>
                                <span>{data.phone}</span>
                                <a href={`mailto:${data.email}`} className="hover:underline">{data.email}</a>
                                <span>{data.location}</span>
                                {data.websites.slice(0, 1).map((s, i) => (
                                    <span key={i} className="text-blue-600">{s.replace(/^https?:\/\//, '')}</span>
                                ))}
                            </div>
                        </>
                    ) : (
                        // Standard Header Layout
                        <>
                            <h1 className={activeStyle.name}>{data.fullName}</h1>
                            {/* For Minimal/Traditional, we typically hide the job title in header to focus on Name + Contact */}
                            {template !== 'minimal' && data.title && <p className={activeStyle.title}>{data.title}</p>}

                            <div className={activeStyle.contactBar}>
                                <span>{data.phone}</span>
                                <span className={`${template === 'tech' ? 'hidden' : 'text-black/50 mx-1'}`}>|</span>
                                <a href={`mailto:${data.email}`} className="hover:underline transition-colors">{data.email}</a>
                                <span className={`${template === 'tech' ? 'hidden' : 'text-black/50 mx-1'}`}>|</span>
                                <span>{data.location}</span>

                                {data.websites.length > 0 && (
                                    <>
                                        <span className={`${template === 'tech' ? 'hidden' : 'text-black/50 mx-1'}`}>|</span>
                                        {data.websites.map((site, index) => (
                                            <React.Fragment key={index}>
                                                {index > 0 && <span className={`${template === 'tech' ? 'hidden' : 'text-black/50 mx-1'}`}>|</span>}
                                                <a href={site} target="_blank" rel="noreferrer" className="hover:underline transition-colors break-all">
                                                    {site.replace(/^https?:\/\//, '')}
                                                </a>
                                            </React.Fragment>
                                        ))}
                                    </>
                                )}
                            </div>
                        </>
                    )}
                </header>

                {/* Separator (Modern only) */}
                <div className={activeStyle.separator}></div>

                {/* --- SUMMARY --- */}
                {data.summary && (
                    <section className={template === 'compact' ? "mb-4" : "mb-6"}>
                        <h3 className={activeStyle.sectionTitle}>
                            {template === 'minimal' ? 'Personal Profile' : 'Professional Summary'}
                        </h3>
                        <p className="text-sm leading-relaxed text-justify opacity-90">
                            {data.summary}
                        </p>
                    </section>
                )}

                {/* --- EXPERIENCE --- */}
                <section className={template === 'compact' ? "mb-4" : "mb-6"}>
                    <h3 className={activeStyle.sectionTitle}>Experience</h3>
                    <div className="space-y-4">
                        {data.experience.map((exp) => {

                            // Minimal / Traditional Style (Strict Layout based on screenshot)
                            if (template === 'minimal') {
                                return (
                                    <div key={exp.id} className="mb-4">
                                        <div className="flex justify-between items-baseline">
                                            <h4 className="font-bold text-black text-base uppercase">{exp.role}</h4>
                                            <span className="text-black text-sm font-serif whitespace-nowrap">{exp.period}</span>
                                        </div>
                                        <div className="flex justify-between items-baseline mb-1">
                                            <span className="italic text-black font-serif">{exp.company}</span>
                                            {exp.location && <span className="italic text-black font-serif text-sm">{exp.location}</span>}
                                        </div>
                                        <ul className="list-disc list-outside ml-5 text-sm leading-snug text-black space-y-1 mt-1">
                                            {exp.achievements.map((point, index) => (
                                                <li key={index} className="pl-1">{point}</li>
                                            ))}
                                        </ul>
                                    </div>
                                );
                            }

                            // Standard Layouts
                            return (
                                <div key={exp.id} className={activeStyle.expItem}>
                                    {/* Header Line */}
                                    <div className={`flex flex-col sm:flex-row justify-between sm:items-baseline mb-1 ${template === 'tech' ? 'font-mono' : ''}`}>
                                        <div className="text-md">
                                            <span className={activeStyle.expRole}>{exp.role}</span>
                                            {template === 'classic' ? <br /> : null}
                                            {exp.company && (
                                                <>
                                                    {template !== 'classic' && template !== 'tech' && <span className="font-normal text-gray-400 mx-1">at</span>}
                                                    <span className={activeStyle.expCompany}>{exp.company}</span>
                                                </>
                                            )}
                                        </div>
                                        {/* Date */}
                                        <div className={activeStyle.expDate}>
                                            {exp.period}
                                        </div>
                                    </div>

                                    {exp.location && template !== 'compact' && (
                                        <p className="text-xs text-gray-400 mb-2 italic">{exp.location}</p>
                                    )}

                                    <ul className={`list-disc list-outside ml-4 text-sm opacity-90 space-y-1 marker:text-gray-400 ${template === 'compact' ? 'mt-1' : ''}`}>
                                        {exp.achievements.map((point, index) => (
                                            <li key={index} className="leading-snug pl-1">{point}</li>
                                        ))}
                                    </ul>
                                </div>
                            );
                        })}
                    </div>
                </section>

                {/* --- EDUCATION --- */}
                {data.education && data.education.length > 0 && (
                    <section className={template === 'compact' ? "mb-4" : "mb-6"}>
                        <h3 className={activeStyle.sectionTitle}>Education</h3>
                        <div className="space-y-4">
                            {data.education.map((edu) => {
                                // Minimal / Traditional Style
                                if (template === 'minimal') {
                                    return (
                                        <div key={edu.id} className="mb-2">
                                            <div className="flex justify-between items-baseline">
                                                <span className="font-bold text-black">{edu.institution}</span>
                                                <span className="text-black text-sm whitespace-nowrap">{edu.period}</span>
                                            </div>
                                            <div className="flex justify-between items-baseline">
                                                <span className="italic text-black">{edu.degree}</span>
                                                <span className="italic text-black text-sm">{edu.location}</span>
                                            </div>
                                        </div>
                                    );
                                }

                                return (
                                    <div key={edu.id} className="flex flex-col sm:flex-row justify-between sm:items-baseline">
                                        <div className="text-sm">
                                            <div className={`font-bold text-base ${template === 'classic' ? 'text-gray-900' : 'text-gray-800'}`}>{edu.degree}</div>
                                            <div className={`${template === 'classic' ? 'italic' : ''} text-gray-600`}>{edu.institution}</div>
                                        </div>
                                        <div className={`${activeStyle.expDate} mt-1 sm:mt-0`}>
                                            {edu.period}
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    </section>
                )}

                {/* --- SKILLS --- */}
                <section>
                    <h3 className={activeStyle.sectionTitle}>
                        {template === 'minimal' ? 'Technical Skills' : 'Skills'}
                    </h3>

                    {template === 'compact' ? (
                        // Compact: Comma separated list
                        <div className="text-sm text-gray-800 leading-relaxed">
                            {data.skills.map(s => s.replace(':', '')).join(' • ')}
                        </div>
                    ) : (
                        <ul className={activeStyle.skillsLayout}>
                            {data.skills.map((skill, index) => {
                                if (template === 'tech') {
                                    // Tech: Tag style
                                    return (
                                        <li key={index} className="px-2 py-1 bg-gray-100 text-blue-900 rounded text-xs font-medium font-mono border border-gray-200">
                                            {skill}
                                        </li>
                                    );
                                }

                                return (
                                    <li key={index} className="leading-snug text-sm text-gray-800">
                                        {/* Check if skill has a label like "Language: Value" to split */}
                                        {skill.includes(':') ? (
                                            <>
                                                <span className={`font-bold ${template === 'minimal' ? 'text-black' : 'text-gray-800'}`}>{skill.split(':')[0]}:</span>
                                                <span className="opacity-90 ml-2">{skill.substring(skill.indexOf(':') + 1)}</span>
                                            </>
                                        ) : (
                                            <span>{skill}</span>
                                        )}
                                    </li>
                                );
                            })}
                        </ul>
                    )}
                </section>

            </div>
        </div>
    );
};
