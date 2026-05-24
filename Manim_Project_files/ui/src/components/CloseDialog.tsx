interface CloseDialogProps {
  onSave: () => void;
  onDiscard: () => void;
  onCancel: () => void;
}

export function CloseDialog({ onSave, onDiscard, onCancel }: CloseDialogProps) {
  return (
    <div className="close-dialog__overlay">
      <div className="close-dialog">
        <div className="close-dialog__title">Unsaved Render</div>
        <div className="close-dialog__body">
          You have an unsaved render. What would you like to do?
        </div>
        <div className="close-dialog__actions">
          <button className="btn btn--save"    onClick={onSave}>Save</button>
          <button className="btn btn--discard" onClick={onDiscard}>Discard</button>
          <button className="btn btn--cancel"  onClick={onCancel}>Cancel</button>
        </div>
      </div>
    </div>
  );
}
