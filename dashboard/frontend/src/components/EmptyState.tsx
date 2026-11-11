export function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="empty">
      <strong>{title}</strong>
      <div>{detail}</div>
    </div>
  );
}
