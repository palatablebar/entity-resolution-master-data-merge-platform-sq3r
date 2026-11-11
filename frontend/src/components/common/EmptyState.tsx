interface Props {
  title: string;
  hint?: string;
}

export const EmptyState = ({ title, hint }: Props) => (
  <div className="empty">
    <div style={{ fontFamily: 'var(--font-display)', fontSize: 18, marginBottom: 6 }}>{title}</div>
    {hint ? <div style={{ fontSize: 13 }}>{hint}</div> : null}
  </div>
);
