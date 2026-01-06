
// modern.typ

#let resume(data) = {
  set text(font: "Roboto", size: 10pt, fill: rgb("#374151"))
  set page(
    paper: "us-letter", 
    margin: (x: 1.5cm, y: 1.5cm),
  )

  // --- Header ---
  align(center)[
    #text(24pt, weight: "bold", fill: rgb("#111827"), upper(data.fullName))
    \
    #v(0.5em)
    #text(14pt, weight: "medium", fill: rgb("#4b5563"), data.title)
    \
    #v(0.5em)
    #text(9pt, fill: rgb("#4b5563"))[
      #data.location | #data.phone | #data.email 
      #if data.websites.len() > 0 [ | #data.websites.join(" | ") ]
    ]
  ]

  v(1.5em)
  line(length: 100%, stroke: 1pt + rgb("#e5e7eb"))
  v(1.5em)

  // --- Summary ---
  if data.summary != "" {
    text(10pt, weight: "bold", fill: rgb("#9ca3af"), tracking: 1.5pt, upper("Professional Summary"))
    v(0.5em)
    block(text(data.summary, size: 10pt, leading: 0.6em))
    v(1.5em)
  }

  // --- Experience ---
  if data.experience.len() > 0 {
    text(10pt, weight: "bold", fill: rgb("#9ca3af"), tracking: 1.5pt, upper("Experience"))
    line(length: 100%, stroke: 0.5pt + rgb("#f3f4f6"))
    v(0.8em)
    
    for exp in data.experience {
      grid(
        columns: (1fr, auto),
        gutter: 1em,
        align(left)[
          #text(11pt, weight: "bold", fill: rgb("#111827"), exp.company)
          #h(0.5em)
          #text(10pt, weight: "regular", fill: rgb("#6b7280"), exp.location)
        ],
        align(right)[
          #text(9pt, weight: "medium", fill: rgb("#6b7280"), upper(exp.period))
        ]
      )
      v(0.3em)
      text(10pt, weight: "bold", fill: rgb("#374151"), exp.role)
      v(0.5em)
      
      if exp.achievements.len() > 0 {
        pad(left: 1em)[
           #for ach in exp.achievements [
             - #ach
           ]
        ]
      }
      v(1.2em)
    }
  }

  // --- Education ---
  if data.education.len() > 0 {
    text(10pt, weight: "bold", fill: rgb("#9ca3af"), tracking: 1.5pt, upper("Education"))
    line(length: 100%, stroke: 0.5pt + rgb("#f3f4f6"))
    v(0.8em)

    for edu in data.education {
       grid(
        columns: (1fr, auto),
        gutter: 1em,
        align(left)[
          #text(11pt, weight: "bold", fill: rgb("#111827"), edu.institution)
        ],
        align(right)[
          #text(9pt, weight: "medium", fill: rgb("#6b7280"), upper(edu.period))
        ]
      )
      v(0.3em)
      text(10pt, fill: rgb("#374151"), edu.degree)
      v(1em)
    }
  }

  // --- Skills ---
  if data.skills.len() > 0 {
    v(0.5em)
    text(10pt, weight: "bold", fill: rgb("#9ca3af"), tracking: 1.5pt, upper("Skills"))
    line(length: 100%, stroke: 0.5pt + rgb("#f3f4f6"))
    v(0.8em)
    
    // Simple list for now, or comma separated?
    // Let's do a wrapping list
    data.skills.join(" • ")
  }
}
