const fs = require('fs');
const path = require('path');

const files = [
  ['node_modules/sortablejs/Sortable.min.js', 'js/sortable.min.js'],
  ['node_modules/tiny-markdown-editor/dist/tiny-mde.min.js', 'js/tiny-mde.min.js'],
  ['node_modules/tiny-markdown-editor/dist/tiny-mde.min.css', 'css/tiny-mde.min.css'],
];

for (const [src, dest] of files) {
  fs.copyFileSync(path.resolve(__dirname, src), path.resolve(__dirname, dest));
}
