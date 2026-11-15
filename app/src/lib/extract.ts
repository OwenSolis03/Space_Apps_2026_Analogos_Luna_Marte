// Pulls single functions and classes out of the real source files, so the Algorithm page shows the
// code that the pipeline runs and never a retyped copy.

/**
 * Returns the source of a top-level or nested Python `def`/`class` (with its decorators), or of a TS
 * function, by header text. The header is matched at the start of a line after indentation.
 * Throws if the header is not found, so a renamed function breaks the build instead of the page.
 */
export function extractBlock(source: string, header: string): string {
  const lines = source.split("\n");
  const start = lines.findIndex((l) => l.trimStart().startsWith(header));
  if (start < 0) throw new Error(`extractBlock: "${header}" not found`);
  const indent = lines[start]!.length - lines[start]!.trimStart().length;
  let first = start;
  while (first > 0 && lines[first - 1]!.trim().startsWith("@")) first--; // decorators
  let end = lines.length;
  for (let i = start + 1; i < lines.length; i++) {
    const l = lines[i]!;
    if (l.trim() === "") continue;
    const ind = l.length - l.trimStart().length;
    const t = l.trimStart();
    // a multi-line signature closes with ")" or "}" at the header's indent: still the same block
    if (ind <= indent && !t.startsWith(")") && !t.startsWith("}")) {
      end = i;
      break;
    }
  }
  while (end > start && lines[end - 1]!.trim() === "") end--;
  return lines
    .slice(first, end)
    .map((l) => l.slice(indent))
    .join("\n");
}

/**
 * Returns the lines from the first line that starts with `startHeader` up to (not including) the first
 * line that starts with `endHeaderExclusive`. Used for TS functions that close at column 0.
 */
export function extractBetween(source: string, startHeader: string, endHeaderExclusive: string): string {
  const lines = source.split("\n");
  const start = lines.findIndex((l) => l.trimStart().startsWith(startHeader));
  if (start < 0) throw new Error(`extractBetween: "${startHeader}" not found`);
  let end = lines.findIndex((l, i) => i > start && l.trimStart().startsWith(endHeaderExclusive));
  if (end < 0) end = lines.length;
  while (end > start && lines[end - 1]!.trim() === "") end--;
  return lines.slice(start, end).join("\n");
}
