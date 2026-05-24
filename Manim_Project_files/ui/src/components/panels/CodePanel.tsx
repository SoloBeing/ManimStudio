import { useImperativeHandle, useState } from 'react';
import { Knob } from '../shared/Knob';
import { TextControls } from '../shared/TextControls';
import { DEFAULT_TEXT } from '../../types';
import type { PanelHandle, TextParams } from '../../types';

const LANGUAGES = ['Python', 'C', 'Cpp', 'Java', 'JavaScript', 'TypeScript', 'Rust', 'Go', 'Bash', 'SQL'];
const ANIMS = ['Write', 'FadeIn', 'FadeIn Up', 'Create', 'Typewriter'];

const DEFAULT_CODE = `def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

print(fibonacci(10))`;

export function CodePanel({ ref }: { ref?: React.Ref<PanelHandle> }) {
  const [code, setCode] = useState(DEFAULT_CODE);
  const [lang, setLang] = useState('Python');
  const [anim, setAnim] = useState('Write');
  const [bg, setBg] = useState('window');
  const [lineNos, setLineNos] = useState(true);
  const [fontSize, setFontSize] = useState(16.0);
  const [runTime, setRunTime] = useState(4.0);
  const [text, setText] = useState<TextParams>({ ...DEFAULT_TEXT });

  useImperativeHandle(ref, () => ({
    getParams: () => ({
      mode: 'code',
      params: {
        code_str: code,
        language: lang,
        anim,
        background: bg,
        add_line_numbers: lineNos,
        font_size: fontSize,
        run_time: runTime,
        ...text,
      },
    }),
  }));

  return (
    <>
      <div className="sec-hdr">Code Editor</div>
      <div className="code-editor-wrap">
        <textarea
          rows={10}
          value={code}
          onChange={e => setCode(e.target.value)}
          spellCheck={false}
        />
      </div>

      <div className="sec-sep" />
      <div className="sec-hdr">Language</div>
      <select className="app-select" value={lang} onChange={e => setLang(e.target.value)}>
        {LANGUAGES.map(l => <option key={l}>{l}</option>)}
      </select>

      <div className="sec-sep" />
      <div className="sec-hdr">Animation Style</div>
      <select className="app-select" value={anim} onChange={e => setAnim(e.target.value)}>
        {ANIMS.map(a => <option key={a}>{a}</option>)}
      </select>

      <div className="sec-sep" />
      <div className="sec-hdr">Display</div>
      <div className="field-row">
        <label>Background</label>
        <select className="app-select" value={bg} onChange={e => setBg(e.target.value)}>
          <option value="window">Window</option>
          <option value="rectangle">Rectangle</option>
        </select>
      </div>
      <div className="check-row">
        <label className="app-check">
          <input type="checkbox" checked={lineNos} onChange={e => setLineNos(e.target.checked)} /> Line numbers
        </label>
      </div>
      <Knob label="Font size"    min={8}   max={32}  value={fontSize} onChange={setFontSize} decimals={0} step={1} />
      <Knob label="Duration (s)" min={0.5} max={15.0} value={runTime}  onChange={setRunTime}  decimals={1} step={0.5} />

      <TextControls value={text} onChange={setText} />
    </>
  );
}
