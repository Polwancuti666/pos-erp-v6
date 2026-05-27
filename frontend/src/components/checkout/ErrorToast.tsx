import { useState, useEffect } from 'react';

interface Props {
  message: string;
  type?: 'error' | 'warning' | 'success';
  onDismiss?: () => void;
  autoHide?: number; // ms
}

const STYLES = {
  error: 'bg-red-600 text-white',
  warning: 'bg-yellow-500 text-white',
  success: 'bg-green-600 text-white',
};

export default function ErrorToast({ message, type = 'error', onDismiss, autoHide = 5000 }: Props) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    if (autoHide > 0) {
      const timer = setTimeout(() => { setVisible(false); onDismiss?.(); }, autoHide);
      return () => clearTimeout(timer);
    }
  }, [autoHide, onDismiss]);

  if (!visible) return null;

  return (
    <div className={`fixed top-16 inset-x-0 flex justify-center z-50 animate-fade-in px-4`}>
      <div className={`${STYLES[type]} px-4 py-3 rounded-xl shadow-lg text-sm max-w-md w-full flex items-center justify-between`}>
        <span>{message}</span>
        <button onClick={() => { setVisible(false); onDismiss?.(); }} className="ml-3 text-white/80 hover:text-white">
          ✕
        </button>
      </div>
    </div>
  );
}
