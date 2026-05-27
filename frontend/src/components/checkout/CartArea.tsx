import type { CartItem, Service } from '../../types';

interface CartAreaProps {
  items: CartItem[];
  onAddItem: (item: CartItem) => void;
  onRemoveItem: (itemId: string) => void;
  onUpdateQuantity: (itemId: string, quantity: number) => void;
}

// Mock services for demo
const MOCK_SERVICES: Service[] = [
  { id: '1', name: 'Creambath', category: 'Hair Care', price: 75000, duration: 45, isActive: true },
  { id: '2', name: 'Facial Gold', category: 'Facial', price: 150000, duration: 60, isActive: true },
  { id: '3', name: 'Manicure', category: 'Nail', price: 50000, duration: 30, isActive: true },
  { id: '4', name: 'Pedicure', category: 'Nail', price: 60000, duration: 30, isActive: true },
  { id: '5', name: 'Hair Spa', category: 'Hair Care', price: 100000, duration: 45, isActive: true },
  { id: '6', name: 'Body Massage', category: 'Body', price: 200000, duration: 90, isActive: true },
];

export default function CartArea({
  items,
  onAddItem,
  onRemoveItem,
  onUpdateQuantity,
}: CartAreaProps) {
  const handleAddService = (service: Service) => {
    const newItem: CartItem = {
      id: Date.now().toString(),
      serviceId: service.id,
      serviceName: service.name,
      price: service.price,
      quantity: 1,
      discount: 0,
      subtotal: service.price,
      staffId: 'staff-1',
      staffName: 'Staff Demo',
    };
    onAddItem(newItem);
  };

  return (
    <div className="space-y-4">
      {/* Service Quick Add */}
      <div className="card">
        <h3 className="section-title">Layanan</h3>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {MOCK_SERVICES.map((service) => (
            <button
              key={service.id}
              onClick={() => handleAddService(service)}
              className="p-3 rounded-lg border border-gray-200 hover:border-primary-300 hover:bg-primary-50 transition-colors text-left active:scale-[0.98]"
            >
              <p className="font-medium text-gray-900 text-sm truncate">
                {service.name}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                Rp {service.price.toLocaleString('id-ID')}
              </p>
            </button>
          ))}
        </div>
      </div>

      {/* Cart Items */}
      <div className="card">
        <div className="flex items-center justify-between mb-3">
          <h3 className="section-title mb-0">Keranjang</h3>
          <span className="text-sm text-gray-500">{items.length} item</span>
        </div>

        {items.length === 0 ? (
          <div className="text-center py-8 text-gray-400">
            <svg className="w-12 h-12 mx-auto mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 100 4 2 2 0 000-4z" />
            </svg>
            <p>Keranjang kosong</p>
            <p className="text-sm mt-1">Pilih layanan untuk memulai</p>
          </div>
        ) : (
          <div className="space-y-2">
            {items.map((item) => (
              <div
                key={item.id}
                className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg"
              >
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-gray-900 truncate">
                    {item.serviceName}
                  </p>
                  <p className="text-sm text-gray-500">
                    {item.staffName} • Rp{' '}
                    {item.price.toLocaleString('id-ID')}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() =>
                      onUpdateQuantity(item.id, item.quantity - 1)
                    }
                    className="w-8 h-8 rounded-full bg-white border border-gray-300 flex items-center justify-center hover:bg-gray-50 active:scale-95"
                    aria-label="Kurangi"
                  >
                    −
                  </button>
                  <span className="w-8 text-center font-medium">
                    {item.quantity}
                  </span>
                  <button
                    onClick={() =>
                      onUpdateQuantity(item.id, item.quantity + 1)
                    }
                    className="w-8 h-8 rounded-full bg-white border border-gray-300 flex items-center justify-center hover:bg-gray-50 active:scale-95"
                    aria-label="Tambah"
                  >
                    +
                  </button>
                </div>

                <div className="text-right">
                  <p className="font-semibold text-gray-900">
                    Rp {item.subtotal.toLocaleString('id-ID')}
                  </p>
                </div>

                <button
                  onClick={() => onRemoveItem(item.id)}
                  className="p-1 text-gray-400 hover:text-danger-600 transition-colors"
                  aria-label="Hapus"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
