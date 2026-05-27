import type { Customer } from '../../types';

interface CustomerBarProps {
  customer: Customer | null;
  onCustomerChange: (customer: Customer | null) => void;
}

export default function CustomerBar({ customer, onCustomerChange }: CustomerBarProps) {
  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex-shrink-0 w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center">
            <svg className="w-5 h-5 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          </div>
          <div className="min-w-0">
            {customer ? (
              <>
                <p className="font-medium text-gray-900 truncate">{customer.name}</p>
                <p className="text-sm text-gray-500 truncate">{customer.phone}</p>
              </>
            ) : (
              <p className="text-gray-500">Pelanggan Umum</p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {customer && customer.memberTier && (
            <span className="px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-700 rounded-full">
              {customer.memberTier}
            </span>
          )}
          <button
            className="btn-secondary text-sm py-2 px-3"
            onClick={() => {
              // Would open customer search modal
              onCustomerChange(null);
            }}
          >
            {customer ? 'Ganti' : 'Cari'}
          </button>
        </div>
      </div>

      {customer?.loyaltyPoints !== undefined && (
        <div className="mt-2 pt-2 border-t border-gray-100">
          <p className="text-sm text-gray-500">
            Poin loyalitas:{' '}
            <span className="font-medium text-primary-600">
              {customer.loyaltyPoints.toLocaleString('id-ID')}
            </span>
          </p>
        </div>
      )}
    </div>
  );
}
