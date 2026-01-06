
// ats_friendly.typ
#import "@preview/ats-friendly-resume:0.1.1": *

#let resume(data) = {
  // --- Personal Info ---
  // In a real implementation, we would parse github/linkedin from 'websites' list 
  // or add dedicated fields. For now, we take from first available.
  
  let linkedin_url = ""
  let github_url = ""
  let portfolio_url = ""
  
  for url in data.websites {
    if "linkedin" in url.lower() { linkedin_url = url }
    else if "github" in url.lower() { github_url = url }
    else { portfolio_url = url }
  }

  show: resume.with(
    author: data.fullName,
    author-position: center,
    location: data.location,
    // email: data.email, // Package might expect 'email' arg
    // phone: data.phone, // Package might expect 'phone' arg
    // But existing packages sometimes differ. Checking user snippet:
    // It has commented out email/phone. Let's assume we pass them if we want them?
    // The user snippet uses 'linkedin', 'github', 'portfolio'.
    linkedin: linkedin_url,
    github: github_url,
    portfolio: portfolio_url,
    personal-info-position: center,
    color-enabled: false,
    text-color: "#000000", // Standard black for ATS
    font: "New Computer Modern",
    paper: "us-letter",
    author-font-size: 20pt,
    font-size: 10pt,
    lang: "en",
  )

  // --- Professional Summary ---
  if data.summary != "" {
    // The package might not have a dedicated 'summary' function, 
    // or we just put it as text. Let's try standard heading.
    [== Professional Summary]
    v(0.5em)
    data.summary
    v(1em)
  }

  // --- Skills ---
  if data.skills.len() > 0 {
    [== Technical Skills]
    // The user snippet uses bullet points for skills.
    // We'll just list them as bullets.
    for skill in data.skills {
       [- #skill]
    }
    v(1em)
  }

  // --- Experience ---
  if data.experience.len() > 0 {
    [== Experience]
    for exp in data.experience {
      work(
        company: exp.company,
        role: exp.role,
        dates: dates-util(
            start-date: exp.period.split("-").at(0).trim(), 
            end-date: exp.period.split("-").at(1).trim()
        ),
        location: exp.location,
        // tech-used: "React | TypeScript", // We don't have this in ResumeData yet
      )
      
      // Achievements
      for ach in exp.achievements {
        [- #ach]
      }
    }
  }

  // --- Projects ---
  // If we had projects in ResumeData, we'd map them here. 
  // For now, ResumeData only has experience/education/skills. 
  // We'll skip Projects to avoid errors.

  // --- Education ---
  if data.education.len() > 0 {
    [== Education]
    for edu in data.education {
      edu(
        institution: edu.institution,
        location: edu.location,
        degree: edu.degree,
        dates: dates-util(
             start-date: edu.period.split("-").at(0).trim(), 
             end-date: edu.period.split("-").at(1).trim()
        ),
      )
    }
  }
}
