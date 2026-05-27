interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  icon?: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'primary';
}

const variantStyles = {
  default: 'bg-white border-gray-200',
  success: 'bg-success-50 border-success-200',
  warning: 'bg-warning-50 border-warning-200',
  danger: 'bg-danger-50 border-danger-200',
  primary: 'bg-primary-50 border-primary-200',
};

const iconBgStyles = {
  default: 'bg-gray-100 text-gray-600',
  success: 'bg-success-100 text-success-600',
  warning: 'bg-warning-100 text-warning-600',
  danger: 'bg-danger-100 text-danger-600',
  primary: 'bg-primary-100 text-primary-600',
};

export default function MetricCard({
  title,
  value,
  subtitle,
  trend,
  icon,
  variant = 'default',
}: MetricCardProps) {
  return (
    <div
      className={`rounded-xl border p-4 transition-all duration-150 ${variantStyles[variant]}`}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-500 truncate">{title}</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">{value}</p>
          {subtitle && (
            <p className="mt-1 text-sm text-gray-500">{subtitle}</p>
          )}
          {trend && (
            <div className="mt-1 flex items-center gap-1">
              <span
                className={`text-sm font-medium ${
                  trend.isPositive ? 'text-success-600' : 'text-danger-600'
                }`}
              >
                {trend.isPositive ? '↑' : '↓'} {Math.abs(trend.value)}%
              </span>
              <span className="text-xs text-gray-400">vs kemarin</span>
            </div>
          )}
        </div>
        {icon && (
          <div
            className={`flex-shrink-0 p-2 rounded-lg ${iconBgStyles[variant]}`}
          >
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}
