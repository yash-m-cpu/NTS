import React from 'react';

export interface Column<T> {
  header: string;
  accessorKey?: keyof T;
  cell?: (row: T) => React.ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  emptyMessage?: string;
}

export function DataTable<T extends Record<string, any>>({
  columns,
  data,
  emptyMessage = 'No data available'
}: DataTableProps<T>) {
  if (!data || data.length === 0) {
    return (
      <div className="w-full text-center py-8 text-sm text-slate-400 bg-slate-900/60 border border-slate-800 rounded-lg">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="w-full overflow-x-auto border border-slate-800 rounded-xl bg-slate-900/80 shadow-sm">
      <table className="w-full text-left text-sm text-slate-300">
        <thead className="bg-slate-950/80 text-xs uppercase tracking-wider text-slate-400 border-b border-slate-800">
          <tr>
            {columns.map((col, idx) => (
              <th key={idx} className={`px-4 py-3 font-semibold ${col.className || ''}`}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/80">
          {data.map((row, rowIdx) => (
            <tr
              key={rowIdx}
              className="hover:bg-slate-800/50 transition-colors"
            >
              {columns.map((col, colIdx) => {
                let content: React.ReactNode = null;
                if (col.cell) {
                  content = col.cell(row);
                } else if (col.accessorKey) {
                  content = String(row[col.accessorKey] ?? '');
                }
                return (
                  <td key={colIdx} className={`px-4 py-3 text-slate-200 ${col.className || ''}`}>
                    {content}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
