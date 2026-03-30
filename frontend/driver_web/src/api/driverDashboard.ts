import { ApiRequestError, apiRequest } from "./client";
import type {
  ActiveRide,
  DriverAvailability,
  DriverProfile,
  DriverStats,
  DriverVehicle,
} from "../types/driverOperations";

type ApiEnvelope<T> = {
  data?: T;
} & T;

type UnknownRecord = Record<string, unknown>;
type RideHistoryResponse = {
  items?: unknown[];
};

type TrackingPoint = {
  latitude: number | string;
  longitude: number | string;
};

type LiveRideState = {
  eta_minutes?: number | null;
  pickup_location?: TrackingPoint | null;
  dropoff_location?: TrackingPoint | null;
};

function unwrap<T>(payload: ApiEnvelope<T>): T {
  if (payload && typeof payload === "object" && "data" in payload && payload.data !== undefined) {
    return payload.data as T;
  }
  return payload as T;
}

function toNumber(value: unknown, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function toString(value: unknown, fallback = "") {
  return typeof value === "string" ? value : fallback;
}

function toBoolean(value: unknown) {
  return value === true;
}

function normalizeAvailability(value: unknown): DriverAvailability {
  const normalized = String(value ?? "OFFLINE").toUpperCase();
  if (normalized === "ONLINE" || normalized === "BUSY") {
    return normalized;
  }
  return "OFFLINE";
}

function availabilityFromFlags(isOnline: unknown, isAvailable: unknown): DriverAvailability {
  const online = isOnline === true;
  const available = isAvailable === true;

  if (!online) {
    return "OFFLINE";
  }

  return available ? "ONLINE" : "BUSY";
}

function mapVehicle(payload: unknown): DriverVehicle | null {
  const source = (payload ?? {}) as UnknownRecord;
  if (!source || !Object.keys(source).length) {
    return null;
  }
  return {
    vehicle_id: toString(source.vehicle_id ?? source.vehicleId ?? source.id),
    make: toString(source.make),
    model: toString(source.model),
    year: toNumber(source.year),
    color: toString(source.color, "Unknown"),
    plate_number: toString(source.plate_number ?? source.plateNumber),
    vehicle_type: toString(source.vehicle_type ?? source.vehicleType),
  };
}

function mapProfile(payload: unknown): DriverProfile {
  const source = (payload ?? {}) as UnknownRecord;
  return {
    driver_id: toString(source.driver_id ?? source.driverId ?? source.id),
    full_name: toString(source.full_name ?? source.fullName ?? source.name, "Driver"),
    email: toString(source.email),
    phone_number: toString(source.phone_number ?? source.phoneNumber),
    created_at: toString(source.created_at ?? source.createdAt) || null,
    rating_avg: toNumber(source.rating_avg ?? source.ratingAvg),
    total_rides_completed: toNumber(source.total_rides_completed ?? source.totalRidesCompleted),
    availability:
      source.availability != null || source.status === "ONLINE" || source.status === "OFFLINE" || source.status === "BUSY"
        ? normalizeAvailability(source.availability ?? source.status)
        : availabilityFromFlags(source.is_online ?? source.isOnline, source.is_available ?? source.isAvailable),
    is_approved: source.is_approved === true || source.isApproved === true,
    kyc_status: toString(source.kyc_status ?? source.kycStatus, "draft"),
    vehicle: mapVehicle(source.vehicle),
    reassigned_ride_id: toString(source.reassigned_ride_id ?? source.reassignedRideId) || null,
    reassignment_notice: toString(source.reassignment_notice ?? source.reassignmentNotice) || null,
    reassignment_at: toString(source.reassignment_at ?? source.reassignmentAt) || null,
  };
}

function mapStats(payload: unknown): DriverStats {
  const source = (payload ?? {}) as UnknownRecord;
  return {
    rides_today: toNumber(source.rides_today ?? source.ridesToday),
    earned_today: toNumber(source.earned_today ?? source.earnedToday),
    rating_avg: toNumber(source.rating_avg ?? source.ratingAvg),
    total_rides: toNumber(source.total_rides ?? source.totalRides),
    currency: toString(source.currency, "USD"),
  };
}

function isActiveRideStatus(value: unknown) {
  const normalized = String(value ?? "").toUpperCase();
  return (
    normalized === "DRIVER_ASSIGNED" ||
    normalized === "DRIVER_EN_ROUTE" ||
    normalized === "DRIVER_ARRIVED" ||
    normalized === "RIDE_STARTED"
  );
}

function normalizeStage(value: unknown): ActiveRide["stage"] {
  const normalized = String(value ?? "DRIVER_ASSIGNED").toUpperCase();
  if (
    normalized === "DRIVER_ASSIGNED" ||
    normalized === "DRIVER_EN_ROUTE" ||
    normalized === "DRIVER_ARRIVED" ||
    normalized === "RIDE_STARTED" ||
    normalized === "RIDE_COMPLETED" ||
    normalized === "CANCELLED"
  ) {
    return normalized as ActiveRide["stage"];
  }
  return "DRIVER_ASSIGNED";
}

function mapActiveRide(payload: unknown): ActiveRide {
  const source = (payload ?? {}) as UnknownRecord;
  return {
    ride_id: toString(source.ride_id ?? source.rideId ?? source.id),
    stage: normalizeStage(source.stage ?? source.status),
    rider_name: toString(source.rider_name ?? source.riderName, "Rider"),
    rider_phone: toString(source.rider_phone ?? source.riderPhone) || null,
    pickup_address: toString(source.pickup_address ?? source.pickupAddress),
    pickup_latitude: toNumber(source.pickup_latitude ?? source.pickupLatitude),
    pickup_longitude: toNumber(source.pickup_longitude ?? source.pickupLongitude),
    dropoff_address: toString(source.dropoff_address ?? source.dropoffAddress),
    dropoff_latitude: toNumber(source.dropoff_latitude ?? source.dropoffLatitude),
    dropoff_longitude: toNumber(source.dropoff_longitude ?? source.dropoffLongitude),
    vehicle_type: toString(source.vehicle_type ?? source.vehicleType),
    seats: toNumber(source.seats, 4),
    fare_amount: toNumber(source.fare_amount ?? source.fareAmount),
    started_at: toString(source.started_at ?? source.startedAt) || null,
    eta_minutes: source.eta_minutes == null && source.etaMinutes == null ? null : toNumber(source.eta_minutes ?? source.etaMinutes),
  };
}

export async function getDriverProfile(): Promise<DriverProfile> {
  const response = await apiRequest<ApiEnvelope<unknown>>("/drivers/me", { method: "GET" });
  return mapProfile(unwrap(response));
}

export async function getDriverStats(): Promise<DriverStats> {
  const response = await apiRequest<ApiEnvelope<unknown>>("/drivers/me/stats", { method: "GET" });
  return mapStats(unwrap(response));
}

export async function setAvailability(status: "ONLINE" | "OFFLINE"): Promise<{ availability: DriverAvailability }> {
  const response = await apiRequest<ApiEnvelope<unknown>>("/drivers/me/availability", {
    method: "POST",
    body: {
      is_online: status === "ONLINE",
      is_available: status === "ONLINE",
    },
  });
  const source = unwrap(response) as UnknownRecord;
  return {
    availability: availabilityFromFlags(source.is_online ?? source.isOnline, source.is_available ?? source.isAvailable),
  };
}

export async function getActiveRide(): Promise<ActiveRide | null> {
  try {
    const historyResponse = await apiRequest<ApiEnvelope<RideHistoryResponse>>("/drivers/me/rides?page=1&page_size=25", {
      method: "GET",
    });
    const history = unwrap(historyResponse);
    const items = Array.isArray(history?.items) ? history.items : [];
    const activeItem = items.find((item) => isActiveRideStatus((item as UnknownRecord).status)) as UnknownRecord | undefined;

    if (!activeItem) {
      return null;
    }

    const rideId = toString(activeItem.ride_id ?? activeItem.rideId ?? activeItem.id);
    if (!rideId) {
      return null;
    }

    const [detailResponse, liveResponse, profileResponse] = await Promise.all([
      apiRequest<ApiEnvelope<unknown>>(`/rides/${rideId}`, { method: "GET" }),
      apiRequest<ApiEnvelope<LiveRideState>>(`/tracking/rides/${rideId}/live`, { method: "GET" }),
      apiRequest<ApiEnvelope<unknown>>("/drivers/me", { method: "GET" }),
    ]);

    const detail = unwrap(detailResponse) as UnknownRecord;
    const live = unwrap(liveResponse) as LiveRideState;
    const profile = unwrap(profileResponse) as UnknownRecord;

    const pickup = live?.pickup_location;
    const dropoff = live?.dropoff_location;

    return mapActiveRide({
      ride_id: toString(detail.id ?? detail.ride_id ?? rideId),
      status: detail.status,
      rider_name: "Assigned rider",
      rider_phone: null,
      pickup_address: detail.pickup_address,
      pickup_latitude: pickup?.latitude,
      pickup_longitude: pickup?.longitude,
      dropoff_address: detail.dropoff_address,
      dropoff_latitude: dropoff?.latitude,
      dropoff_longitude: dropoff?.longitude,
      vehicle_type: detail.vehicle && typeof detail.vehicle === "object" ? (detail.vehicle as UnknownRecord).vehicle_type : "",
      seats:
        detail.vehicle && typeof detail.vehicle === "object"
          ? toNumber((detail.vehicle as UnknownRecord).seat_capacity, 4)
          : 4,
      fare_amount: toNumber(detail.final_fare_amount, 0),
      started_at: toString(detail.started_at) || null,
      eta_minutes: live?.eta_minutes ?? null,
      driver_online: toBoolean(profile.is_online ?? profile.isOnline),
    });
  } catch (error) {
    if (error instanceof ApiRequestError && error.status === 404) {
      return null;
    }
    throw error;
  }
}
