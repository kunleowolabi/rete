export default function InfoTable({ columns, rows }) {
  return (
    <table className="w-full text-xs">
      <thead>
        <tr className="border-b border-white/10 text-white/40">
          {columns.map((c) => (
            <th key={c.key} className="text-left font-medium" style={{ padding: "6px 8px 6px 0" }}>
              {c.label}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={i} className="border-b border-white/5 last:border-0">
            {columns.map((c) => (
              <td key={c.key} className="text-white" style={{ padding: "8px 8px 8px 0" }}>
                {c.render ? c.render(row) : row[c.key]}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}