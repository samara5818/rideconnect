import { getBaseUrl, request } from "./client";
import type {
  FareEstimateResponse,
  PaymentMethod,
  RideFareBreakdown,
  RideFeedbackStatus,
  RideDriver,
  RideRequest,
  RideResponse,
  RideStatus,
  RideStatusPoll,
  VehicleType,
} from "../types/ride";
import type { RideHistoryItem } from "../types/api";

const ESTIMATE_ORDER: VehicleType[] = ["ECONOMY", "COMFORT", "PREMIUM", "XL"];
const ACTIVE_RIDE_KEY = "rc_active_ride_id";
function createIdempotencyKey(prefix: string) {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function normalizePaymentMethod(method?: string | null): PaymentMethod {
  if (method === "CARD" || method === "DIGITAL_WALLET") {
    return method;
  }
  return "CASH";
}

function normalizeVehicleType(type?: string | null): VehicleType {
  switch ((type ?? "").toUpperCase()) {
    case "COMFORT":
      return "COMFORT";
    case "PREMIUM":
      return "PREMIUM";
    case "XL":
      return "XL";
    default:
      return "ECONOMY";
  }
}

function normalizeStatus(status?: string | null): RideStatus {
  switch ((status ?? "").toUpperCase()) {
    case "MATCHING":
      return "MATCHING";
    case "NO_DRIVERS_FOUND":
      return "NO_DRIVERS_FOUND";
    case "DRIVER_ASSIGNED":
      return "DRIVER_ASSIGNED";
    case "DRIVER_EN_ROUTE":
      return "DRIVER_EN_ROUTE";
    case "DRIVER_ARRIVED":
      return "DRIVER_ARRIVED";
    case "RIDE_STARTED":
      return "RIDE_STARTED";
    case "RIDE_COMPLETED":
      return "RIDE_COMPLETED";
    case "CANCELLED":
      return "CANCELLED";
    default:
      return "REQUESTED";
  }
}

function normalizeFeedbackStatus(status?: string | null): RideFeedbackStatus {
  switch ((status ?? "").toUpperCase()) {
    case "SUBMITTED":
    case "COMPLETED":
      return "SUBMITTED";
    case "SKIPPED":
      return "SKIPPED";
    default:
      return "PENDING";
  }
}

function normalizeRideResponse(data: any, rideId: string, fallback?: Partial<RideResponse>): RideResponse {
  const rideStatus = normalizeStatus(data?.ride_status ?? data?.status ?? fallback?.status);
  const feedbackStatus = normalizeFeedbackStatus(data?.feedback_status);
  const completionAcknowledged = Boolean(data?.completion_acknowledged);

  return {
    ride_id: data?.id ?? data?.ride_id ?? rideId,
    status: rideStatus,
    ride_status: rideStatus,
    pickup_address: data?.pickup_address ?? fallback?.pickup_address ?? "",
    dropoff_address: data?.dropoff_address ?? fallback?.dropoff_address ?? "",
    vehicle_type: normalizeVehicleType(data?.vehicle_type ?? data?.vehicle?.vehicle_type ?? fallback?.vehicle_type),
    payment_method: normalizePaymentMethod(data?.payment_method ?? fallback?.payment_method),
    payment_status: String(data?.payment_status ?? "PENDING"),
    feedback_status: feedbackStatus,
    completion_acknowledged: completionAcknowledged,
    completed_at: data?.completed_at ?? fallback?.completed_at ?? null,
    receipt_available: Boolean(data?.receipt_available),
    can_rate_driver: Boolean(data?.can_rate_driver),
    can_tip: Boolean(data?.can_tip ?? false),
    rider_rating: data?.rider_rating == null ? null : Number(data.rider_rating),
    rider_comment: typeof data?.rider_comment === "string" ? data.rider_comment : null,
    dispatch_retry_count:
      data?.dispatch_retry_count == null
        ? fallback?.dispatch_retry_count ?? null
        : Number(data.dispatch_retry_count),
    fare_breakdown: data?.fare_breakdown
      ? {
          base_fare: Number(data.fare_breakdown.base_fare ?? 0),
          distance_fare: Number(data.fare_breakdown.distance_fare ?? 0),
          time_fare: Number(data.fare_breakdown.time_fare ?? 0),
          booking_fee: Number(data.fare_breakdown.booking_fee ?? 0),
          platform_fee: Number(data.fare_breakdown.platform_fee ?? 0),
          total: Number(data.fare_breakdown.total ?? data?.final_fare_amount ?? data?.estimated_fare ?? 0),
        }
      : null,
    final_fare_amount:
      data?.final_fare_amount == null
        ? fallback?.final_fare_amount ?? null
        : Number(data.final_fare_amount),
    estimated_fare: Number(data?.estimated_fare ?? fallback?.estimated_fare ?? data?.final_fare_amount ?? 0),
    driver: data?.driver
      ? {
          driver_id: data.driver.driver_id ?? data.driver.id,
          full_name: data.driver.full_name ?? [data.driver.first_name, data.driver.last_name].filter(Boolean).join(" "),
          rating_avg: Number(data.driver.rating_avg ?? 0),
          total_rides_completed: Number(data.driver.total_rides_completed ?? 0),
          vehicle_make: data.driver.vehicle_make ?? data.vehicle?.make ?? "",
          vehicle_model: data.driver.vehicle_model ?? data.vehicle?.model ?? "",
          vehicle_year: Number(data.driver.vehicle_year ?? data.vehicle?.year ?? 0),
          vehicle_color: data.driver.vehicle_color ?? data.vehicle?.color ?? "",
          plate_number: data.driver.plate_number ?? data.vehicle?.plate_number ?? "",
          vehicle_type: normalizeVehicleType(data.driver.vehicle_type ?? data.vehicle?.vehicle_type),
          current_latitude: data.driver.current_latitude == null ? null : Number(data.driver.current_latitude),
          current_longitude: data.driver.current_longitude == null ? null : Number(data.driver.current_longitude),
          eta_minutes: data.driver.eta_minutes == null ? null : Number(data.driver.eta_minutes),
        }
      : fallback?.driver ?? null,
    created_at: data?.created_at ?? data?.requested_at ?? fallback?.created_at ?? new Date().toISOString(),
  };
}

export async function getFareEstimates(params: {
  pickup_lat: number;
  pickup_lng: number;
  pickup_address: string;
  dropoff_lat: number;
  dropoff_lng: number;
  dropoff_address: string;
  seats: number;
}): Promise<FareEstimateResponse> {
  const basePayload = {
    pickup_address: params.pickup_address,
    pickup_latitude: params.pickup_lat,
    pickup_longitude: params.pickup_lng,
    dropoff_address: params.dropoff_address,
    dropoff_latitude: params.dropoff_lat,
    dropoff_longitude: params.dropoff_lng,
    ride_type: "ON_DEMAND",
  };

  const estimateResults = await Promise.all(
    ESTIMATE_ORDER.filter((type) => type !== "COMFORT").map(async (vehicleType) => {
      try {
        const result = await request<any>("/rides/estimate", {
          method: "POST",
          body: JSON.stringify({
            ...basePayload,
            vehicle_type: vehicleType,
          }),
        });
        return result;
      } catch {
        return null;
      }
    }),
  );

  const normalized = estimateResults
    .filter(Boolean)
    .map((item: any) => ({
      estimate_id: item.estimate_id ?? undefined,
      vehicle_type: normalizeVehicleType(item.vehicle_type),
      total_estimated_fare: Number(item.total_estimated_fare ?? 0),
      currency: "USD",
      eta_pickup_minutes:
        item.vehicle_type === "ECONOMY" ? 4 :
        item.vehicle_type === "PREMIUM" ? 8 :
        item.vehicle_type === "XL" ? 9 : 6,
      available: true,
      distance_miles: Number(item.distance_miles ?? 0),
      duration_minutes: Number(item.duration_minutes ?? 0),
    }));

  if (!normalized.length) {
    throw new Error("No fare estimates available");
  }

  const primary = normalized[0];
  return {
    pickup: {
      display_name: params.pickup_address,
      latitude: params.pickup_lat,
      longitude: params.pickup_lng,
    },
    dropoff: {
      display_name: params.dropoff_address,
      latitude: params.dropoff_lat,
      longitude: params.dropoff_lng,
    },
    estimates: normalized.map(({ distance_miles: _distance, duration_minutes: _duration, ...estimate }) => estimate),
    route_distance_km: Number(primary.distance_miles ?? 0) * 1.60934,
    route_duration_min: Number(primary.duration_minutes ?? 0),
  };
}

export async function requestRide(payload: RideRequest): Promise<RideResponse> {
    const data = await request<any>("/rides/request", {
      method: "POST",
      headers: {
        "Idempotency-Key": createIdempotencyKey("ride-create"),
      },
      body: JSON.stringify({
        pickup_address: payload.pickup_address,
        pickup_latitude: payload.pickup_latitude,
        pickup_longitude: payload.pickup_longitude,
        dropoff_address: payload.dropoff_address,
        dropoff_latitude: payload.dropoff_latitude,
        dropoff_longitude: payload.dropoff_longitude,
        ride_type: payload.ride_type,
        vehicle_type: payload.vehicle_type,
        payment_method: payload.payment_method,
        fare_estimate_id: payload.fare_estimate_id ?? null,
      }),
    });
  return normalizeRideResponse(data, data.ride_id ?? data.id ?? "new-ride", {
    pickup_address: payload.pickup_address,
    dropoff_address: payload.dropoff_address,
    vehicle_type: payload.vehicle_type,
    payment_method: payload.payment_method,
    estimated_fare: 0,
    final_fare_amount: null,
    driver: null,
    created_at: new Date().toISOString(),
  });
}

export async function getRideStatus(rideId: string): Promise<RideStatusPoll> {
  const data = await request<any>(`/rides/${rideId}/status`).catch(async () => {
    const ride = await request<any>(`/rides/${rideId}`);
      return {
        ride_id: ride.id ?? ride.ride_id ?? rideId,
        status: ride.status,
        dispatch_retry_count: ride.dispatch_retry_count ?? null,
        driver: ride.driver
          ? {
            driver_id: ride.driver.id,
            full_name: [ride.driver.first_name, ride.driver.last_name].filter(Boolean).join(" "),
            rating_avg: Number(ride.driver.rating_avg ?? 0),
            total_rides_completed: Number(ride.driver.total_rides_completed ?? 0),
            vehicle_make: ride.vehicle?.make ?? "",
            vehicle_model: ride.vehicle?.model ?? "",
            vehicle_year: Number(ride.vehicle?.year ?? 0),
            vehicle_color: ride.vehicle?.color ?? "",
            plate_number: ride.vehicle?.plate_number ?? "",
            vehicle_type: normalizeVehicleType(ride.vehicle?.vehicle_type),
            current_latitude: null,
            current_longitude: null,
            eta_minutes: null,
          }
        : null,
      eta_minutes: null,
    };
  });

  return {
    ride_id: data.ride_id ?? rideId,
    status: normalizeStatus(data.status),
    dispatch_retry_count: data.dispatch_retry_count == null ? null : Number(data.dispatch_retry_count),
    driver: data.driver
      ? {
          driver_id: data.driver.driver_id ?? data.driver.id,
          full_name: data.driver.full_name ?? [data.driver.first_name, data.driver.last_name].filter(Boolean).join(" "),
          rating_avg: Number(data.driver.rating_avg ?? 0),
          total_rides_completed: Number(data.driver.total_rides_completed ?? 0),
          vehicle_make: data.driver.vehicle_make ?? data.vehicle_make ?? "",
          vehicle_model: data.driver.vehicle_model ?? data.vehicle_model ?? "",
          vehicle_year: Number(data.driver.vehicle_year ?? 0),
          vehicle_color: data.driver.vehicle_color ?? "",
          plate_number: data.driver.plate_number ?? "",
          vehicle_type: normalizeVehicleType(data.driver.vehicle_type),
          current_latitude: data.driver.current_latitude == null ? null : Number(data.driver.current_latitude),
          current_longitude: data.driver.current_longitude == null ? null : Number(data.driver.current_longitude),
          eta_minutes: data.driver.eta_minutes == null ? null : Number(data.driver.eta_minutes),
        }
      : null,
    eta_minutes: data.eta_minutes == null ? null : Number(data.eta_minutes),
  };
}

export async function cancelRide(rideId: string): Promise<void> {
  await request<void>(`/rides/${rideId}/cancel`, { method: "POST" });
}

export async function getRideDetail(rideId: string): Promise<RideResponse> {
  const data = await request<any>(`/rides/${rideId}`);
  return normalizeRideResponse(data, rideId);
}

export async function rateRide(rideId: string, payload: { rating: number; comment?: string }): Promise<void> {
  const token = window.localStorage.getItem("rc_rider_token");
  const response = await fetch(`${getBaseUrl()}/api/v1/rider/rides/${rideId}/rate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Could not submit rating");
  }
}

export async function getLatestRiderTrip(): Promise<RideResponse | null> {
  const activeRideId = window.localStorage.getItem(ACTIVE_RIDE_KEY);

  if (activeRideId) {
    try {
      const activeRide = await getRideDetail(activeRideId);
      if (activeRide.ride_status === "RIDE_COMPLETED" || activeRide.ride_status === "CANCELLED" || activeRide.ride_status === "NO_DRIVERS_FOUND") {
        window.localStorage.removeItem(ACTIVE_RIDE_KEY);
      } else {
        return activeRide;
      }
    } catch {
      window.localStorage.removeItem(ACTIVE_RIDE_KEY);
    }
  }

  try {
    const history = await request<any>("/rides/me/history?page=1&page_size=1");
    const item = history?.items?.[0];
    if (!item) {
      return null;
    }
    return getRideDetail(item.ride_id ?? item.id);
  } catch {
    return null;
  }
}

export async function acknowledgeRideCompletion(rideId: string, feedbackStatus?: RideFeedbackStatus) {
  await request(`/rider/rides/${rideId}/acknowledge-completion`, {
    method: "POST",
    body: JSON.stringify({
      ...(feedbackStatus ? { feedback_status: feedbackStatus } : {}),
    }),
  });
}

export async function getRides(): Promise<RideHistoryItem[]> {
  const data = await request<any[]>("/rides");
  return Array.isArray(data) ? data.map((item) => ({
    ride_id: item.ride_id ?? item.id ?? "",
    ride_request_id: item.ride_request_id ?? item.ride_id ?? item.id ?? "",
    status: normalizeStatus(item.status),
    pickup_label: item.pickup_address ?? item.pickup_label ?? "",
    destination_label: item.dropoff_address ?? item.destination_label ?? "",
    created_at: item.created_at ?? new Date().toISOString(),
    assigned_at: item.assigned_at ?? null,
    completed_at: item.completed_at ?? null,
    fare: item.final_fare_amount != null ? String(item.final_fare_amount) : item.estimated_fare != null ? String(item.estimated_fare) : null,
    driver_name: item.driver?.full_name ?? null,
    vehicle_name: item.driver ? `${item.driver.vehicle_make ?? ""} ${item.driver.vehicle_model ?? ""}`.trim() : null,
    vehicle_plate: item.driver?.plate_number ?? null,
  })) : [];
}

export const ridesApi = {
  getFareEstimates,
  requestRide,
  getRideStatus,
  cancelRide,
  getRideDetail,
  rateRide,
  getRides,
};
