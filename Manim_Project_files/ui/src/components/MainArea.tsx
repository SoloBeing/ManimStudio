import type { RenderStatus } from '../types';

interface MainAreaProps {
  status: RenderStatus;
  videoUrl: string;
  onSave: () => void;
  onDiscard: () => void;
}

export function MainArea({ status, videoUrl, onSave, onDiscard }: MainAreaProps) {
  const hasPending = status === 'done' && !!videoUrl;
  const isImage    = videoUrl.toLowerCase().endsWith('.png');

  return (
    <div className="main-area">
      {status === 'rendering' && (
        <div className="main-area__idle">
          <div className="main-area__spinner" />
          <span className="main-area__idle-text">Rendering…</span>
        </div>
      )}

      {status !== 'rendering' && !videoUrl && (
        <div className="main-area__idle">
          <div className="main-area__idle-icon">▶</div>
          <span className="main-area__idle-text">
            {status === 'error'   ? 'Render failed — see build log'   :
             status === 'stopped' ? 'Render stopped'                  :
             'Configure parameters and click Render'}
          </span>
        </div>
      )}

      {videoUrl && isImage && (
        <img
          key={videoUrl}
          className="main-area__image"
          src={videoUrl}
          onContextMenu={e => e.preventDefault()}
        />
      )}

      {videoUrl && !isImage && (
        <video
          key={videoUrl}
          className="main-area__video"
          src={videoUrl}
          controls
          autoPlay
          controlsList="nodownload noremoteplayback"
          disablePictureInPicture
          onContextMenu={e => e.preventDefault()}
        />
      )}

      {hasPending && (
        <div className="main-area__actions">
          <button className="btn btn--discard" onClick={onDiscard}>Discard</button>
          <button className="btn btn--save"    onClick={onSave}>Save</button>
        </div>
      )}
    </div>
  );
}
