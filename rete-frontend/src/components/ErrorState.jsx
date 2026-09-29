export default function ErrorState({ message = "Couldn't load this data.", onRetry }) {
  return (
    <div style={{ padding: "12px 0" }}>
      <p className="text-xs text-[var(--color-line)]">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-xs text-[var(--color-accent)] hover:underline"
          style={{ marginTop: 6, background: "none", border: "none", cursor: "pointer", padding: 0 }}
        >
          Try again
        </button>
      )}
    </div>
  );
}