interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  actions?: React.ReactNode;
}

export default function Modal({ open, onClose, title, children, actions }: ModalProps) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center bg-black/40" onClick={onClose}>
      <div
        className="bg-white rounded-t-2xl sm:rounded-2xl w-full max-w-md p-6 animate-slide-up"
        onClick={e => e.stopPropagation()}
      >
        <h3 className="text-lg font-semibold text-charcoal mb-3">{title}</h3>
        <div className="text-gray-600 text-sm mb-6">{children}</div>
        {actions && <div className="flex gap-3">{actions}</div>}
      </div>
    </div>
  );
}
