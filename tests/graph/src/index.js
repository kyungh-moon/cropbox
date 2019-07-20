import React from 'react'
import ReactDOM from 'react-dom'
import CytoscapeComponent from 'react-cytoscapejs'
import Defiant from 'defiant.js/src/defiant.js'

import Cytoscape from 'cytoscape';
import COSEBilkent from 'cytoscape-cose-bilkent';
import FCOSE from 'cytoscape-fcose';

Cytoscape.use(COSEBilkent);
Cytoscape.use(FCOSE);

function shapeMap(el) {
  let t = el.data('type')
  if (t == 'accumulate') {
    return 'concave-hexagon'
  } else if (t == 'parameter') {
    return 'diamond'
  } else if (t == 'drive') {
    return 'rhomboid'
  } else if (t == 'flag') {
    return 'tag'
  } else if (t == 'optimize') {
    return 'star'
  } else {
    return 'ellipse'
  }
}

class App extends React.Component {
  constructor(props){
    super(props)

    this.state = {
      dataset: [],
      snapshot: null,
      tick: null,
      layout: {
        //name: 'fcose',
        name: 'cose-bilkent',
        //name: 'random',
        // animate: 'end',
        // animationEasing: 'ease-out',
        // animationDuration: 1000,
        // randomize: true,
        // //fit: false,
        // nodeDimensionsIncludeLabels: true,
        // nestingFactor: 5,
        // //padding: 10,
        // tile: true,
      },
      style: { width: '100vw', height: '100vh' },
      stylesheet: [
        {
          selector: 'node',
          style: {
            'border-width': 1,
            'border-style': 'solid',
            'border-color': '#333333',
            'background-color': '#666666',
            'label': 'data(label)',
            'font-size': 12,
            'font-family': 'Gill Sans, sans-serif',
            'shape': shapeMap,
            'padding': '7%',
          }
        },
        {
          selector: ':parent',
          style: {
            'background-opacity': 0.333,
            'font-size': 12,
            'font-style': 'italic',
          }
        },
        {
          selector: 'edge',
          style: {
            'label': 'data(label)',
            //'color': ,
            'font-size': 11,
            'font-family': 'Gill Sans, sans-serif',
            'text-opacity': 0.7,
            'width': 1,
            'curve-style': 'unbundled-bezier',
            'line-color': '#666666',
            'line-style': 'dotted',
            'target-arrow-color': '#666666',
            'target-arrow-shape': 'vee'
          }
        }
      ]
    }
  }

  componentDidMount() {
    this.load()
  }

  async load() {
    let response = await fetch('graph.json')
    let dataset = await response.json()
    let snapshot = Defiant.getSnapshot(dataset)
    this.setState({dataset, snapshot, tick: 1})
  }

  search(path, fallback=undefined) {
    if (this.state.snapshot) {
      let a = Defiant.search(this.state.snapshot, path)
      if (a.length > 0) return a[0]
    }
    return (fallback !== undefined) ? fallback : null
  }

  elements(tick) {
    let res = this.search(`//clock[tick=${tick}]/../elements`, [])
    return CytoscapeComponent.normalizeElements(res)
  }

  get maxTick() {
    return this.search('(//clock)[last()]/tick', 0)
  }

  handle(cy) {
    cy.layout(this.state.layout).run()
  }

  render() {
    const {tick, layout, style, stylesheet} = this.state
    return <CytoscapeComponent cy={cy => this.handle(cy)} elements={this.elements(tick)} layout={layout} style={style} stylesheet={stylesheet} />
  }
}

ReactDOM.render(<App />, document.getElementById('graph'))
