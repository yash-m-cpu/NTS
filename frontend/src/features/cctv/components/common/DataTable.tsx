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
      <div className="w-full text-center py-8 text-sm text-gray-500 bg-white border border-gray-200 rounded-xl">
        {emptyMessage}
      </div>
    );
  }

  return (
    <div className="w-full overflow-x-auto border border-gray-200 rounded-xl bg-white shadow-sm">
      <table className="w-full text-left text-sm text-gray-700">
        <thead className="bg-gray-50 text-xs uppercase tracking-wider text-gray-500 border-b border-gray-200">
          <tr>
            {columns.map((col, idx) => (
              <th key={idx} className={`px-4 py-3 font-semibold ${col.className || ''}`}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {data.map((row, rowIdx) => (
            <tr
              key={rowIdx}
              className="hover:bg-gray-50/80 transition-colors"
            >
              {columns.map((col, colIdx) => {
                let content: React.ReactNode = null;
                if (col.cell) {
                  content = col.cell(row);
                } else if (col.accessorKey) {
                  content = String(row[col.accessorKey] ?? '');
                }
                return (
                  <td key={colIdx} className={`px-4 py-3 text-gray-800 ${col.className || ''}`}>
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
