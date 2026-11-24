import type JSZip from 'jszip'
export type WorkbookResult = { files: { key: string; name: string; rows: number; csv: string; lines: number[] }[]; errors: string[]; errorCount: number }
export function convertWorkbook(input: ArrayBuffer, mapping: Record<string, string[]>, zipLib: typeof JSZip): Promise<WorkbookResult>
export function pack(result: WorkbookResult, zipLib: typeof JSZip): Promise<Uint8Array<ArrayBuffer>>
