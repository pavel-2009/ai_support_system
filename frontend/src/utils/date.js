export function formatTime(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function formatConversationTimestamp(dateString) {
  if (!dateString) return '';
  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) return '';
  return date.toDateString() === new Date().toDateString()
    ? formatTime(dateString)
    : date.toLocaleDateString([], { day: 'numeric', month: 'short' });
}
