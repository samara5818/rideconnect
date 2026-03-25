import { getBaseUrl } from "./client";
import type { RiderActivityResponse, RiderRideHistory } from "../types/activity";


type ActivityParams = {
  status?: "RIDE_COMPLETED" | "CANCELLED" | "ALL";
  period?: "this_month" | "last_3_months" | "this_year" | "all_time";
  page?: number;
  limit?: number;
};

type ApiEnvelope<T> = { data?: T } & T;

type RideDetailApi = {
  id: string;
  status: string;
  pickup_address: string;
  dropoff_address: string;
  payment_method?: string | null;
  feedback_status?: "PENDING" | "SUBMITTED" | "SKIPPED" | string | null;
  receipt_available?: boolean | null;
  can_rate_driver?: boolean | null;
  rider_rating?: number | string | null;
  rider_comment?: string | null;
  driver?: {
    first_name?: string | null;
    last_name?: string | null;
  } | null;
  vehicle?: {
    vehicle_type?: string | null;
    make?: string | null;
    model?: string | null;
    plate_number?: string | null;
  } | null;
  requested_at?: string | null;
  completed_at?: string | null;
  estimated_duration_minutes?: number | null;
  actual_duration_minutes?: number | null;
  estimated_distance_miles?: number | string | null;
  actual_distance_miles?: number | string | null;
  final_fare_amount?: number | string | null;
  fare_breakdown?: {
    base_fare?: number | string | null;
    distance_fare?: number | string | null;
    time_fare?: number | string | null;
    booking_fee?: number | string | null;
    platform_fee?: number | string | null;
    total?: number | string | null;
  } | null;
};

type RiderHistoryListItem = {
  ride_id: string;
  pickup_address: string;
  dropoff_address: string;
  status: string;
  completed_at?: string | null;
  final_fare_amount?: number | string | null;
};

type RiderHistoryListResponse = {
  items: RiderHistoryListItem[];
  pagination?: {
    total_items?: number;
  };
};

function getHeaders(extra?: HeadersInit) {
  const token = window.localStorage.getItem("rc_rider_token");
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(extra ?? {}),
  };
}

function unwrap<T>(payload: ApiEnvelope<T>): T {
  if (payload && typeof payload === "object" && "data" in payload && payload.data !== undefined) {
    return payload.data as T;
  }
  return payload as T;
}

function fullName(first?: string | null, last?: string | null, fallback = "Driver pending") {
  const value = [first, last].filter(Boolean).join(" ").trim();
  return value || fallback;
}

function normalizeStatus(value: unknown): RiderRideHistory["status"] {
  const normalized = String(value ?? "MATCHING").toUpperCase();
  if (
    normalized === "MATCHING" ||
    normalized === "NO_DRIVERS_FOUND" ||
    normalized === "DRIVER_ASSIGNED" ||
    normalized === "DRIVER_EN_ROUTE" ||
    normalized === "DRIVER_ARRIVED" ||
    normalized === "RIDE_STARTED" ||
    normalized === "RIDE_COMPLETED" ||
    normalized === "CANCELLED"
  ) {
    return normalized;
  }
  return "MATCHING";
}

function toNumber(value: unknown): number | null {
  if (value == null || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function buildSummary(rides: RiderRideHistory[]) {
  const completed = rides.filter((ride) => ride.status === "RIDE_COMPLETED");
  const ratings = completed.map((ride) => ride.rider_rating).filter((value): value is number => value != null);
  const distances = completed.map((ride) => ride.distance_km).filter((value): value is number => value != null);
  return {
    total_rides: rides.length,
    total_spent: completed.reduce((sum, ride) => sum + (ride.fare_amount ?? 0), 0),
    average_distance_km: distances.length ? distances.reduce((sum, value) => sum + value, 0) / distances.length : 0,
    average_rating_given: ratings.length ? ratings.reduce((sum, value) => sum + value, 0) / ratings.length : 0,
    currency: "USD",
  };
}

function filterRides(rides: RiderRideHistory[], params?: ActivityParams) {
  let filtered = [...rides];
  if (params?.status && params.status !== "ALL") {
    filtered = filtered.filter((ride) => ride.status === params.status);
  }
  const now = Date.now();
  if (params?.period && params.period !== "all_time") {
    filtered = filtered.filter((ride) => {
      const createdAt = new Date(ride.created_at).getTime();
      const diffDays = (now - createdAt) / 86400000;
      if (params.period === "this_month") return diffDays <= 31;
      if (params.period === "last_3_months") return diffDays <= 92;
      if (params.period === "this_year") return diffDays <= 365;
      return true;
    });
  }
  return filtered;
}

function mapApiRide(item: Record<string, unknown>): RiderRideHistory {
  return {
    ride_id: String(item.ride_id ?? item.id ?? ""),
    status: normalizeStatus(item.status),
    pickup_address: String(item.pickup_address ?? item.pickup_label ?? ""),
    dropoff_address: String(item.dropoff_address ?? item.destination_label ?? ""),
    vehicle_type: String(item.vehicle_type ?? item.vehicle?.vehicle_type ?? "Economy"),
    vehicle_make: String(item.vehicle_make ?? item.vehicle?.make ?? ""),
    vehicle_model: String(item.vehicle_model ?? item.vehicle?.model ?? ""),
    driver_name: String(item.driver_name ?? item.driver?.full_name ?? "Driver pending"),
    fare_amount: toNumber(item.fare_amount ?? item.final_fare_amount ?? item.estimated_fare),
    payment_method: String(item.payment_method ?? "Card"),
    duration_minutes: toNumber(item.duration_minutes ?? item.actual_duration_minutes),
    distance_km: toNumber(item.distance_km ?? item.actual_distance_km),
    rider_rating: toNumber(item.rider_rating),
    rider_comment: typeof item.rider_comment === "string" ? item.rider_comment : null,
    receipt_available: Boolean(item.receipt_available),
    can_rate_driver: Boolean(item.can_rate_driver),
    feedback_status:
      String(item.feedback_status ?? "PENDING").toUpperCase() === "SUBMITTED"
        ? "SUBMITTED"
        : String(item.feedback_status ?? "PENDING").toUpperCase() === "SKIPPED"
          ? "SKIPPED"
          : "PENDING",
    created_at: String(item.created_at ?? item.requested_at ?? new Date().toISOString()),
    completed_at: typeof item.completed_at === "string" ? item.completed_at : null,
  };
}

function milesToKm(value: unknown): number | null {
  const miles = toNumber(value);
  return miles == null ? null : miles / 0.621371;
}

async function getRideDetailApi(rideId: string): Promise<RideDetailApi> {
  const response = await fetch(`${getBaseUrl()}/api/v1/rides/${rideId}`, {
    headers: getHeaders(),
  });
  if (!response.ok) {
    throw new Error("Could not load ride details");
  }
  return unwrap(await response.json() as ApiEnvelope<RideDetailApi>);
}

async function normalizeRideFromHistory(item: RiderHistoryListItem): Promise<RiderRideHistory> {
  const detail = await getRideDetailApi(item.ride_id);
  return {
    ride_id: item.ride_id,
    status: normalizeStatus(item.status),
    pickup_address: item.pickup_address,
    dropoff_address: item.dropoff_address,
    vehicle_type: String(detail.vehicle?.vehicle_type ?? "Economy"),
    vehicle_make: String(detail.vehicle?.make ?? ""),
    vehicle_model: String(detail.vehicle?.model ?? ""),
    plate_number: String(detail.vehicle?.plate_number ?? ""),
    driver_name: fullName(detail.driver?.first_name, detail.driver?.last_name),
    fare_amount: toNumber(item.final_fare_amount ?? detail.final_fare_amount),
    payment_method: String(detail.payment_method ?? "Card"),
    duration_minutes: detail.actual_duration_minutes ?? detail.estimated_duration_minutes ?? null,
    distance_km: milesToKm(detail.actual_distance_miles ?? detail.estimated_distance_miles),
    rider_rating: toNumber(detail.rider_rating),
    rider_comment: typeof detail.rider_comment === "string" ? detail.rider_comment : null,
    receipt_available: Boolean(detail.receipt_available),
    can_rate_driver: Boolean(detail.can_rate_driver),
    feedback_status:
      String(detail.feedback_status ?? "PENDING").toUpperCase() === "SUBMITTED"
        ? "SUBMITTED"
        : String(detail.feedback_status ?? "PENDING").toUpperCase() === "SKIPPED"
          ? "SKIPPED"
          : "PENDING",
    fare_breakdown: detail.fare_breakdown
      ? {
          base_fare: toNumber(detail.fare_breakdown.base_fare) ?? 0,
          distance_time_fare: (toNumber(detail.fare_breakdown.distance_fare) ?? 0) + (toNumber(detail.fare_breakdown.time_fare) ?? 0),
          fees: (toNumber(detail.fare_breakdown.booking_fee) ?? 0) + (toNumber(detail.fare_breakdown.platform_fee) ?? 0),
          taxes: 0,
          tip: 0,
          total: toNumber(detail.fare_breakdown.total ?? item.final_fare_amount ?? detail.final_fare_amount) ?? 0,
          currency: "USD",
        }
      : null,
    created_at: detail.requested_at ?? item.completed_at ?? new Date().toISOString(),
    completed_at: detail.completed_at ?? item.completed_at ?? null,
  };
}

export async function getRiderActivity(params?: ActivityParams): Promise<RiderActivityResponse> {
  const query = new URLSearchParams();
  if (params?.status && params.status !== "ALL") query.set("status", params.status);
  if (params?.period) query.set("period", params.period);
  if (params?.page) query.set("page", String(params.page));
  if (params?.limit) query.set("page_size", String(params.limit));

  const response = await fetch(`${getBaseUrl()}/api/v1/rides/me/history${query.toString() ? `?${query}` : ""}`, {
    headers: getHeaders(),
  });

  if (!response.ok) {
    throw new Error("Could not load rider activity");
  }
  const data = unwrap(await response.json() as ApiEnvelope<RiderHistoryListResponse>);
  const items = Array.isArray(data?.items) ? data.items : [];
  const rides = await Promise.all(items.map(normalizeRideFromHistory));
  const filtered = filterRides(rides, params);
  return {
    rides: filtered,
    summary: buildSummary(filtered),
    total_count: Number(data?.pagination?.total_items ?? filtered.length),
  };
}

export async function getRiderRideDetail(rideId: string): Promise<RiderRideHistory> {
  const payload = await getRideDetailApi(rideId);
  return {
    ride_id: payload.id,
    status: normalizeStatus(payload.status),
    pickup_address: payload.pickup_address,
    dropoff_address: payload.dropoff_address,
    vehicle_type: String(payload.vehicle?.vehicle_type ?? "Economy"),
    vehicle_make: String(payload.vehicle?.make ?? ""),
    vehicle_model: String(payload.vehicle?.model ?? ""),
    plate_number: String(payload.vehicle?.plate_number ?? ""),
    driver_name: fullName(payload.driver?.first_name, payload.driver?.last_name),
    fare_amount: toNumber(payload.final_fare_amount),
    payment_method: String(payload.payment_method ?? "Card"),
    duration_minutes: payload.actual_duration_minutes ?? payload.estimated_duration_minutes ?? null,
    distance_km: (() => {
      const miles = toNumber(payload.actual_distance_miles ?? payload.estimated_distance_miles);
      return miles == null ? null : miles / 0.621371;
    })(),
    rider_rating: toNumber(payload.rider_rating),
    rider_comment: typeof payload.rider_comment === "string" ? payload.rider_comment : null,
    receipt_available: Boolean(payload.receipt_available),
    can_rate_driver: Boolean(payload.can_rate_driver),
    feedback_status:
      String(payload.feedback_status ?? "PENDING").toUpperCase() === "SUBMITTED"
        ? "SUBMITTED"
        : String(payload.feedback_status ?? "PENDING").toUpperCase() === "SKIPPED"
          ? "SKIPPED"
          : "PENDING",
    fare_breakdown: payload.fare_breakdown
      ? {
          base_fare: toNumber(payload.fare_breakdown.base_fare) ?? 0,
          distance_time_fare: (toNumber(payload.fare_breakdown.distance_fare) ?? 0) + (toNumber(payload.fare_breakdown.time_fare) ?? 0),
          fees: (toNumber(payload.fare_breakdown.booking_fee) ?? 0) + (toNumber(payload.fare_breakdown.platform_fee) ?? 0),
          taxes: 0,
          tip: 0,
          total: toNumber(payload.fare_breakdown.total ?? payload.final_fare_amount) ?? 0,
          currency: "USD",
        }
      : null,
    created_at: payload.requested_at ?? new Date().toISOString(),
    completed_at: payload.completed_at ?? null,
  };
}

export async function submitRiderRating(rideId: string, payload: { rating: number; comment?: string }): Promise<void> {
  const response = await fetch(`${getBaseUrl()}/api/v1/rider/rides/${rideId}/rate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getHeaders(),
    },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error("Could not submit rating");
  }
}

export async function downloadRiderReceipt(rideId: string): Promise<Blob> {
  const response = await fetch(`${getBaseUrl()}/api/v1/rider/rides/${rideId}/receipt`, {
    headers: getHeaders(),
  });
  if (!response.ok) {
    throw new Error("Could not download receipt");
  }
  return response.blob();
}
