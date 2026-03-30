export type DriverAvailability = "OFFLINE" | "ONLINE" | "BUSY";

export type RideOfferStatus = "PENDING" | "ACCEPTED" | "REJECTED" | "EXPIRED";

export type RideStage =
  | "DRIVER_ASSIGNED"
  | "DRIVER_EN_ROUTE"
  | "DRIVER_ARRIVED"
  | "RIDE_STARTED"
  | "RIDE_COMPLETED"
  | "CANCELLED";

export interface DriverVehicle {
  vehicle_id: string;
  make: string;
  model: string;
  year: number;
  color: string;
  plate_number: string;
  vehicle_type: string;
}

export interface DriverProfile {
  driver_id: string;
  full_name: string;
  email: string;
  phone_number: string;
  created_at?: string | null;
  rating_avg: number;
  total_rides_completed: number;
  availability: DriverAvailability;
  is_approved: boolean;
  kyc_status: string;
  vehicle: DriverVehicle | null;
  reassigned_ride_id?: string | null;
  reassignment_notice?: string | null;
  reassignment_at?: string | null;
}

export interface DriverStats {
  rides_today: number;
  earned_today: number;
  rating_avg: number;
  total_rides: number;
  currency: string;
}

export interface RideOffer {
  offer_id: string;
  ride_id: string;
  status: RideOfferStatus;
  vehicle_type: string;
  pickup_address: string;
  pickup_latitude: number;
  pickup_longitude: number;
  dropoff_address: string;
  dropoff_longitude: number;
  dropoff_latitude: number;
  estimated_fare: number;
  estimated_distance_km: number;
  estimated_duration_min: number;
  expires_at: string;
  created_at: string;
}

export interface ActiveRide {
  ride_id: string;
  stage: RideStage;
  rider_name: string;
  rider_phone: string | null;
  pickup_address: string;
  pickup_latitude: number;
  pickup_longitude: number;
  dropoff_address: string;
  dropoff_latitude: number;
  dropoff_longitude: number;
  vehicle_type: string;
  seats: number;
  fare_amount: number;
  started_at: string | null;
  eta_minutes: number | null;
}
