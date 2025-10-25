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

module.exports = {
  render: function(resume) {
    const templatePath = path.join(__dirname, 'template.hbs');
    const templateSrc = fs.readFileSync(templatePath, 'utf8');
    const template = Handlebars.compile(templateSrc, { noEscape: true });
    return template(resume);
  }
};
