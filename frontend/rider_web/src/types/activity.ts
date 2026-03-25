export type RideHistoryStatus =
  | "MATCHING"
  | "NO_DRIVERS_FOUND"
  | "DRIVER_ASSIGNED"
  | "DRIVER_EN_ROUTE"
  | "DRIVER_ARRIVED"
  | "RIDE_STARTED"
  | "RIDE_COMPLETED"
  | "CANCELLED";

export interface RiderRideHistory {
  ride_id: string;
  status: RideHistoryStatus;
  pickup_address: string;
  dropoff_address: string;
  vehicle_type: string;
  vehicle_make: string;
  vehicle_model: string;
  plate_number?: string;
  driver_name: string;
  fare_amount: number | null;
  payment_method: string;
  duration_minutes: number | null;
  distance_km: number | null;
  rider_rating: number | null;
  rider_comment: string | null;
  receipt_available?: boolean;
  can_rate_driver?: boolean;
  feedback_status?: "PENDING" | "SUBMITTED" | "SKIPPED";
  fare_breakdown?: RideFareBreakdown | null;
  created_at: string;
  completed_at: string | null;
}

export interface RiderActivitySummary {
  total_rides: number;
  total_spent: number;
  average_distance_km: number;
  average_rating_given: number;
  currency: string;
}

export interface RiderActivityResponse {
  rides: RiderRideHistory[];
  summary: RiderActivitySummary;
  total_count: number;
}

export type ActivityFilterTab = "ALL" | "ONGOING" | "UPCOMING" | "PAST" | "PAYMENTS";

export type RiderActivityEventType =
  | "RIDE_COMPLETED"
  | "RIDE_CANCELLED"
  | "DRIVER_ASSIGNED"
  | "DRIVER_ARRIVED"
  | "PAYMENT_PROCESSED"
  | "RECEIPT_AVAILABLE"
  | "REFUND_ISSUED"
  | "SUPPORT_UPDATE"
  | "SCHEDULED_RIDE";

export interface RideFareBreakdown {
  base_fare: number;
  distance_time_fare: number;
  fees: number;
  taxes: number;
  tip: number;
  total: number;
  currency: string;
}

export interface RiderActivityItem {
  id: string;
  ride_id: string | null;
  type: RiderActivityEventType;
  status: string;
  title: string;
  route_label: string;
  pickup_address: string;
  dropoff_address: string;
  driver_name: string;
  vehicle_label: string;
  plate_number: string;
  amount: number | null;
  currency: string;
  timestamp: string;
  payment_method: string;
  duration_minutes: number | null;
  distance_miles: number | null;
  receipt_available: boolean;
  rider_comment: string | null;
  rider_rating: number | null;
  ride_type: string;
  event_note: string;
  cta_label: string;
}

export interface RiderCurrentRide {
  id: string;
  ride_id: string;
  status: string;
  pickup_address: string;
  dropoff_address: string;
  short_route: string;
  driver_name: string;
  vehicle_label: string;
  plate_number: string;
  eta_minutes: number | null;
  amount: number | null;
  currency: string;
  payment_method: string;
}

export interface RiderUpcomingRide {
  id: string;
  ride_id: string;
  scheduled_for: string;
  pickup_address: string;
  dropoff_address: string;
  short_route: string;
  ride_type: string;
  payment_method: string;
  status: "SCHEDULED";
}

export interface RiderActivityDetail extends RiderActivityItem {
  fare_breakdown: RideFareBreakdown;
}

export type ActivityFilter = ActivityFilterTab;

export interface ActivityStatsSummary {
  totalTrips: number;
  totalSpent: number;
  averageTripCost: number;
  averageTripDistanceMiles: number;
}

export interface ActivitySectionGroup {
  label: string;
  items: RiderActivityItem[];
}
