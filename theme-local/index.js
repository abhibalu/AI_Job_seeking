const fs = require('fs');
const path = require('path');
const Handlebars = require('handlebars');

// Helpers
Handlebars.registerHelper('join', function(arr, sep) {
  if (!Array.isArray(arr)) return '';
  return arr.join(typeof sep === 'string' ? sep : ', ');
});

Handlebars.registerHelper('linkedinUrl', function(profiles) {
  if (!Array.isArray(profiles)) return '';
  const p = profiles.find((x) => (x.network || '').toLowerCase() === 'linkedin');
  return p && (p.url || (p.username ? 'https://linkedin.com/in/' + p.username : '')) || '';
});

Handlebars.registerHelper('dateRange', function(start, end) {
  const s = start || '';
  const e = end || 'Present';
  if (!s && !e) return '';
  if (!s) return e;
  return `${s} – ${e}`;
});

Handlebars.registerHelper('isEdited', function(index, editedArray) {
  if (!Array.isArray(editedArray)) return false;
  return editedArray.includes(index);
});

Handlebars.registerHelper('getEditedBullets', function(workId, resume) {
  // Extract edited_bullets array for a specific work item ID
  const meta = resume?.meta?.modifications?.work;
  if (!meta || !workId) return [];
  const edits = meta[workId];
  return Array.isArray(edits?.edited_bullets) ? edits.edited_bullets : [];
});

module.exports = {
  render: function(resume) {
    const templatePath = path.join(__dirname, 'template.hbs');
    const templateSrc = fs.readFileSync(templatePath, 'utf8');
    const template = Handlebars.compile(templateSrc, { noEscape: true });
    return template(resume);
  }
};
