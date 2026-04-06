import { saveAs } from 'file-saver';

export function downloadBlob(data: Blob, filename: string): void {
  saveAs(data, filename);
}

export function downloadJson(data: unknown, filename: string): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json',
  });
  saveAs(blob, filename);
}
