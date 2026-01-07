Resume PDF Style Guide
This guide documents the HTML structure and CSS rules used to generate the compact 
resume.pdf
.

1. Job Header Layout (Split Lines)
To display the Company/Date on the first line and Role/Location on the second line:

HTML Pattern:

<!-- Line 1: Company and Dates -->
<h3 style="margin-bottom: 0;">
  <span style="float: right; font-weight: normal; font-size: 13px;">
    Jan 2020 – Present
  </span>
  Company Name
</h3>
<!-- Line 2: Role and Location -->
<div style="font-size: 13px; margin-bottom: 4px;">
  <span style="float: right;">Location, City</span>
  <strong>Job Title</strong>
</div>
2. Bullet Point Alignment (Hanging Indent)
To align bullet points strictly to the left (flush with headers) while keeping multi-line text indented correctly (hanging indent):

CSS:

ul {
  /* Remove default left margin */
  margin: 4px 0 6px 0;
  
  /* Use padding for the bullet indentation space */
  padding-left: 1.2em;
  
  /* 'outside' ensures the bullet is in the padding area, 
     so text wraps nicely under the first line's text */
  list-style-position: outside;
}
li {
  font-size: 13px;
  /* Optional: Tighten spacing */
  margin-bottom: 0px; 
}
3. Technologies & Skills (Compact List)
For the "Technologies and Skills" section, we use a compact list with reduced line height and margin.

HTML:

<ul class="compact-list">
  <li>
    <strong>Category</strong>: Item 1, Item 2, Item 3
  </li>
  <li>
    <strong>Category 2</strong>: Item A, Item B
  </li>
</ul>
CSS:

.compact-list li {
  margin-bottom: 0;
  line-height: 1.3; /* Tighter line height for this section */
}
4. Date Formatting
Dates are formatted as "Mon YYYY" (e.g., "Jun 2022").

JavaScript Helper:

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
function formatDate(dateStr) {
  if (!dateStr) return '';
  const str = String(dateStr);
  const [year, month] = str.split('-');
  if (!year || !month) return str;
  const mIndex = parseInt(month, 10) - 1;
  if (mIndex < 0 || mIndex > 11) return str;
  return `${MONTHS[mIndex]} ${year}`;
}
5. Global Typography
CSS:

body {
  font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
  line-height: 1.4;
  color: #111;
  margin: 24px; /* Page margins */
}
h2 {
  font-size: 16px;
  margin: 10px 0 6px;
  text-transform: uppercase;
  letter-spacing: .5px;
}
