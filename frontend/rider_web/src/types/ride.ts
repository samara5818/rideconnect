export type VehicleType = "ECONOMY" | "COMFORT" | "PREMIUM" | "XL";

export type PaymentMethod = "CASH" | "CARD" | "DIGITAL_WALLET";

export type RideStatus =
  | "REQUESTED"
  | "MATCHING"
  | "NO_DRIVERS_FOUND"
  | "DRIVER_ASSIGNED"
  | "DRIVER_EN_ROUTE"
  | "DRIVER_ARRIVED"
  | "RIDE_STARTED"
  | "RIDE_COMPLETED"
  | "CANCELLED";

export type RideFeedbackStatus = "PENDING" | "SUBMITTED" | "SKIPPED";

export interface AddressResult {
  display_name: string;
  latitude: number;
  longitude: number;
}

export interface FareEstimate {
  estimate_id?: string;
  vehicle_type: VehicleType;
  total_estimated_fare: number;
  currency: string;
  eta_pickup_minutes: number;
  available: boolean;
}

export interface FareEstimateResponse {
  pickup: AddressResult;
  dropoff: AddressResult;
  estimates: FareEstimate[];
  route_distance_km: number;
  route_duration_min: number;
}

export interface RideRequest {
  pickup_latitude: number;
  pickup_longitude: number;
  pickup_address: string;
  dropoff_latitude: number;
  dropoff_longitude: number;
  dropoff_address: string;
  ride_type: "ON_DEMAND" | "SCHEDULED";
  vehicle_type: VehicleType;
  fare_estimate_id?: string | null;
  payment_method: PaymentMethod;
  seats: number;
}

export interface RideDriver {
  driver_id: string;
  full_name: string;
  rating_avg: number;
  total_rides_completed: number;
  vehicle_make: string;
  vehicle_model: string;
  vehicle_year: number;
  vehicle_color: string;
  plate_number: string;
  vehicle_type: VehicleType;
  current_latitude: number | null;
  current_longitude: number | null;
  eta_minutes: number | null;
}

export interface RideFareBreakdown {
  base_fare: number;
  distance_fare: number;
  time_fare: number;
  booking_fee: number;
  platform_fee: number;
  total: number;
}

export interface RideResponse {
  ride_id: string;
  status: RideStatus;
  ride_status: RideStatus;
  pickup_address: string;
  dropoff_address: string;
  vehicle_type: VehicleType;
  payment_method: PaymentMethod;
  payment_status: string;
  feedback_status: RideFeedbackStatus;
  completion_acknowledged: boolean;
  completed_at: string | null;
  receipt_available: boolean;
  can_rate_driver: boolean;
  can_tip: boolean;
  rider_rating: number | null;
  rider_comment: string | null;
  dispatch_retry_count?: number | null;
  fare_breakdown: RideFareBreakdown | null;
  final_fare_amount: number | null;
  estimated_fare: number;
  driver: RideDriver | null;
  created_at: string;
}

export interface RideStatusPoll {
  ride_id: string;
  status: RideStatus;
  driver: RideDriver | null;
  eta_minutes: number | null;
  dispatch_retry_count?: number | null;
}
