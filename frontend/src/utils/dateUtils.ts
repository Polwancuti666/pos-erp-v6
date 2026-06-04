/**
 * Parse a date string from the server.
 * Server stores timestamps without timezone suffix (e.g., "2026-06-03 09:27:43"),
 * and they are already in the user's local timezone (WIB / Asia/Jakarta)
 * because the DB session timezone is set to Asia/Jakarta.
 * We just parse as-is — no timezone conversion needed.
 */
export function parseUTCDate(dateStr: string | undefined | null): Date {
  if (!dateStr) return new Date();
  // If already has timezone info, parse normally
  if (dateStr.endsWith('Z') || dateStr.includes('+') || (dateStr.includes('-') && dateStr.lastIndexOf('-') > 10)) {
    return new Date(dateStr);
  }
  // Replace space with T for ISO format, but DON'T append Z — timestamps are already local time
  return new Date(dateStr.replace(' ', 'T'));
}

/**
 * Format a server timestamp to localized string.
 */
export function formatDateTime(dateStr: string | undefined | null, options?: Intl.DateTimeFormatOptions): string {
  const date = parseUTCDate(dateStr);
  return date.toLocaleString('id-ID', options || {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}
