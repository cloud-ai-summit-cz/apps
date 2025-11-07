export enum PlaceStatus {
  PLANNED = 'planned',
  VISITED = 'visited',
  SKIPPED = 'skipped',
}

export enum TripStatus {
  PLANNED = 'planned',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  CANCELLED = 'cancelled',
}

export interface Place {
  place_number: number;
  name: string;
  planned_visit?: string;
  actual_visit?: string;
  status: PlaceStatus;
  notes?: string;
}

export interface GalleryImage {
  image_id: string;
  place_number?: number;
  landmark?: string;
  blob_name: string;
  caption?: string;
  uploaded_at: string;
  source: string;
}

export interface TripBase {
  title: string;
  description?: string;
  location_name: string;
  country_code: string;
  public_tracking_enabled: boolean;
}

export interface TripCreate extends TripBase {
  toy_id: string;
  places?: Place[];
}

export interface TripUpdate {
  title?: string;
  description?: string;
  location_name?: string;
  country_code?: string;
  public_tracking_enabled?: boolean;
  status?: TripStatus;
}

export interface Trip extends TripBase {
  id: string;
  toy_id: string;
  owner_oid: string;
  status: TripStatus;
  places: Place[];
  gallery: GalleryImage[];
  created_at: string;
  updated_at: string;
}

export interface TripListResponse {
  items: Trip[];
  total: number;
  limit: number;
  offset: number;
}
