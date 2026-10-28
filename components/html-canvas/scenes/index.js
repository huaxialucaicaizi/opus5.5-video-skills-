// Scene registry. Storyboard scenes reference these by `component` name.
// To add a component: write scenes/<name>.js exporting default (f, params) => void, register it here,
// and document its params in components/html-canvas/README.md.
import kineticTitle from './kinetic-title.js';
import tokenSplit from './token-split.js';
import probBars from './prob-bars.js';
import appendLoop from './append-loop.js';
import takeaway from './takeaway.js';

export const scenes = {
  'kinetic-title': kineticTitle,
  'token-split': tokenSplit,
  'prob-bars': probBars,
  'append-loop': appendLoop,
  'takeaway': takeaway,
};
export default scenes;
