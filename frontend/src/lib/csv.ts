/**
 * Just enough CSV reading in the browser to show the landlord their own column names
 * and a few example rows, so they can say which column is which. The real parsing
 * happens on the server; this never decides what gets imported.
 */

/** One CSV line into fields, honouring quotes ("Smith, J" stays one field). */
export function splitCsvLine(line: string): string[] {
  const fields: string[] = [];
  let field = "";
  let quoted = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (quoted) {
      if (ch === '"' && line[i + 1] === '"') {
        field += '"';
        i++;
      } else if (ch === '"') quoted = false;
      else field += ch;
    } else if (ch === '"') quoted = true;
    else if (ch === ",") {
      fields.push(field.trim());
      field = "";
    } else field += ch;
  }
  fields.push(field.trim());
  return fields;
}

export interface CsvGlimpse {
  columns: string[];
  examples: string[][]; // up to three rows, to show what each column holds
}

/** The header row and a few rows after it. Skips a byte-order mark and blank lines. */
export function glimpse(text: string, rows = 3): CsvGlimpse {
  const lines = text
    .replace(/^\uFEFF/, "")
    .split(/\r\n|\n|\r/)
    .filter((l) => l.trim() !== "");
  const [header, ...rest] = lines;
  return {
    columns: header ? splitCsvLine(header).filter((c) => c !== "") : [],
    examples: rest.slice(0, rows).map(splitCsvLine),
  };
}

/** The start of a file as text. FileReader, not Blob.text(), so older Safari copes too. */
export function readStart(file: Blob, bytes = 64 * 1024): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.onerror = () => reject(reader.error ?? new Error("Couldn’t read the file"));
    reader.readAsText(file.slice(0, bytes));
  });
}
