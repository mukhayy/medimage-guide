export interface Region {
  id: string;
  number: number;
  label: string;
  mentioned: boolean;
  color: [number, number, number]; // RGB
  bbox: [number, number, number, number]; // [x1, y1, x2, y2]
  center: [number, number]; // [x, y]
}

export interface MRIData {
  visualization: string; // Image path
  regions: Region[];
  diagnosis: string;
  metadata: {
    filename: string;
    num_regions: number;
    mentioned_regions: number;
  };
}
