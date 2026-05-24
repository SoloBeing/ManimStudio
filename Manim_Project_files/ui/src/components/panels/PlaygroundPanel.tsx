import { useImperativeHandle, useMemo, useState } from 'react';
import CodeMirror from '@uiw/react-codemirror';
import { python } from '@codemirror/lang-python';
import { oneDark } from '@codemirror/theme-one-dark';
import type { PanelHandle } from '../../types';

const TEMPLATE = `from manim import *

class ManimScene(Scene):
    def construct(self):
        # Write any Manim code here

        circle = Circle(radius=1.5, color=BLUE)
        square = Square(side_length=2.5, color=RED)

        self.play(Create(circle), run_time=1.2)
        self.play(Transform(circle, square), run_time=1.5)
        self.play(FadeOut(circle), run_time=0.8)
        self.wait(1)
`;

function detectScenes(src: string): string[] {
  const names: string[] = [];
  const re = /^class\s+(\w+)\s*\([^)]*Scene[^)]*\)/gm;
  let m: RegExpExecArray | null;
  while ((m = re.exec(src)) !== null) names.push(m[1]);
  return names;
}

export function PlaygroundPanel({ ref }: { ref?: React.Ref<PanelHandle> }) {
  const [source, setSource] = useState(TEMPLATE);
  const [selectedScene, setSelectedScene] = useState('');

  const scenes = useMemo(() => detectScenes(source), [source]);
  const effectiveScene = scenes.includes(selectedScene) ? selectedScene : (scenes[0] ?? '');

  useImperativeHandle(ref, () => ({
    getParams: () => ({
      mode: 'playground',
      params: { source },
      sceneName: effectiveScene,
    }),
  }));

  const extensions = useMemo(() => [python()], []);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, gap: 6 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div className="sec-hdr" style={{ padding: 0 }}>Manim Source</div>
        <button
          className="btn btn--discard"
          style={{ padding: '2px 8px', fontSize: 10 }}
          onClick={() => setSource(TEMPLATE)}
        >Reset</button>
      </div>

      <div style={{ flex: 1, minHeight: 0, borderRadius: 4, overflow: 'hidden' }}>
        <CodeMirror
          value={source}
          height="100%"
          theme={oneDark}
          extensions={extensions}
          onChange={setSource}
          style={{ height: '100%', fontSize: 12 }}
        />
      </div>

      <div className="field-row">
        <label style={{ minWidth: 'auto', marginRight: 8, fontSize: 10, color: 'var(--dim)', fontWeight: 700, letterSpacing: '0.1em' }}>
          SCENE
        </label>
        {scenes.length > 0 ? (
          <select className="app-select" value={effectiveScene}
            onChange={e => setSelectedScene(e.target.value)}>
            {scenes.map(s => <option key={s}>{s}</option>)}
          </select>
        ) : (
          <select className="app-select" disabled>
            <option>No scene detected</option>
          </select>
        )}
      </div>
    </div>
  );
}
