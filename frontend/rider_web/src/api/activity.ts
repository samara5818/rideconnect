import { downloadRiderReceipt as downloadReceiptFromHistory, getRiderActivity as getRideHistory } from "./riderActivity";
import { getLatestRiderTrip, getRideDetail, getRideStatus } from "./rides";
import type {
  ActivitySectionGroup,
  ActivityStatsSummary,
  ActivityFilterTab,
  RideFareBreakdown,
  RiderActivityDetail,
  RiderActivityItem,
  RiderCurrentRide,
  RiderRideHistory,
  RiderUpcomingRide,
} from "../types/activity";
import { shortAddress, titleizeStatus } from "../utils/formatters";

function toMiles(km: number | null) {
  return km == null ? null : Number((km * 0.621371).toFixed(1));
}

function vehicleLabel(ride: Pick<RiderRideHistory, "vehicle_type" | "vehicle_make" | "vehicle_model">) {
  const makeModel = [ride.vehicle_make, ride.vehicle_model].filter(Boolean).join(" ").trim();
  return makeModel || ride.vehicle_type || "Vehicle pending";
}

function synthesizeFareBreakdown(totalAmount: number | null, currency = "USD"): RideFareBreakdown {
  const total = Number(totalAmount ?? 0);
  return {
    base_fare: total,
    distance_time_fare: 0,
    fees: 0,
    taxes: 0,
    tip: 0,
    total,
    currency,
  };
}

function buildBaseItem(ride: RiderRideHistory) {
  return {
    ride_id: ride.ride_id,
    pickup_address: ride.pickup_address || "—",
    dropoff_address: ride.dropoff_address || "—",
    route_label: `${shortAddress(ride.pickup_address)} → ${shortAddress(ride.dropoff_address)}`,
    driver_name: ride.driver_name || "Driver pending",
    vehicle_label: vehicleLabel(ride),
    plate_number: ride.plate_number || "—",
    amount: ride.fare_amount ?? 0,
    currency: "USD",
    payment_method: ride.payment_method || "No payment method",
    duration_minutes: ride.duration_minutes,
    distance_miles: toMiles(ride.distance_km),
    receipt_available: Boolean(ride.receipt_available),
    rider_comment: ride.rider_comment,
    rider_rating: ride.rider_rating,
    ride_type: ride.vehicle_type || "Economy",
  };
}

function buildPastActivityItems(rides: RiderRideHistory[]): RiderActivityItem[] {
  return rides.flatMap((ride) => {
    const base = buildBaseItem(ride);
    const completedAt = ride.completed_at ?? ride.created_at;

    if (ride.status === "CANCELLED") {
      return [
        {
          id: `ride-cancelled-${ride.ride_id}`,
          type: "RIDE_CANCELLED",
          status: "CANCELLED",
          title: "Ride cancelled",
          timestamp: completedAt,
          event_note: "Your trip was cancelled before pickup.",
          cta_label: "Book again",
          ...base,
        },
      ];
    }

    if (ride.status !== "RIDE_COMPLETED") {
      return [
        {
          id: `ride-active-${ride.ride_id}`,
          type: ride.status === "DRIVER_ARRIVED" ? "DRIVER_ARRIVED" : "DRIVER_ASSIGNED",
          status: ride.status,
          title: currentRideTitle(ride.status),
          timestamp: completedAt,
          event_note: "This ride has not been completed yet.",
          cta_label: "View details",
          ...base,
        },
      ];
    }

    return [
      {
        id: `ride-completed-${ride.ride_id}`,
        type: "RIDE_COMPLETED",
        status: ride.status,
        title: "Ride completed",
        timestamp: completedAt,
        event_note: "Trip completed successfully.",
        cta_label: "View details",
        ...base,
      },
    ];
  });
}

function filterItems(items: RiderActivityItem[], filter: ActivityFilterTab) {
  switch (filter) {
    case "ONGOING":
      return items.filter((item) => item.status === "DRIVER_ASSIGNED" || item.status === "DRIVER_EN_ROUTE" || item.status === "DRIVER_ARRIVED" || item.status === "RIDE_STARTED");
    case "UPCOMING":
      return items.filter((item) => item.type === "SCHEDULED_RIDE");
    case "PAST":
      return items.filter((item) => item.type === "RIDE_COMPLETED" || item.type === "RIDE_CANCELLED");
    case "PAYMENTS":
      return [];
    default:
      return items;
  }
}

function currentRideTitle(status: string) {
  if (status === "RIDE_STARTED") return "Ride in progress";
  if (status === "DRIVER_ARRIVED") return "Driver has arrived";
  if (status === "DRIVER_EN_ROUTE" || status === "DRIVER_ASSIGNED") return "Driver arriving";
  return titleizeStatus(status);
}

export async function getRiderCurrentRide(): Promise<RiderCurrentRide | null> {
  const latestRide = await getLatestRiderTrip();
  if (!latestRide) {
    return null;
  }
  if (!["DRIVER_ASSIGNED", "DRIVER_EN_ROUTE", "DRIVER_ARRIVED", "RIDE_STARTED", "MATCHING"].includes(latestRide.ride_status)) {
    return null;
  }

  const rideId = latestRide.ride_id;

  try {
    const [status, detail] = await Promise.all([getRideStatus(rideId), getRideDetail(rideId)]);
    if (status.status === "RIDE_COMPLETED" || status.status === "CANCELLED") {
      return null;
    }

    return {
      id: `current-${rideId}`,
      ride_id: rideId,
      status: status.status,
      pickup_address: detail.pickup_address || "—",
      dropoff_address: detail.dropoff_address || "—",
      short_route: `${shortAddress(detail.pickup_address)} → ${shortAddress(detail.dropoff_address)}`,
      driver_name: detail.driver?.full_name || "Driver pending",
      vehicle_label: [detail.driver?.vehicle_make, detail.driver?.vehicle_model].filter(Boolean).join(" ").trim() || detail.vehicle_type || "Vehicle pending",
      plate_number: detail.driver?.plate_number || "—",
      eta_minutes: status.eta_minutes ?? detail.driver?.eta_minutes ?? null,
      amount: detail.final_fare_amount ?? detail.estimated_fare ?? null,
      currency: "USD",
      payment_method: detail.payment_method || "No payment method",
    };
  } catch {
    return null;
  }
}

export async function getRiderUpcomingRides(): Promise<RiderUpcomingRide[]> {
  return [];
}

export async function getRiderActivity(params?: { filter?: ActivityFilterTab }): Promise<RiderActivityItem[]> {
  const filter = params?.filter ?? "ALL";
  const history = await getRideHistory({ status: "ALL", period: "all_time" });
  const items = buildPastActivityItems(history.rides).sort((a, b) => +new Date(b.timestamp) - +new Date(a.timestamp));
  return filterItems(items, filter);
}

export async function getRiderActivityStats(): Promise<ActivityStatsSummary> {
  const history = await getRideHistory({ status: "ALL", period: "all_time" });

  return {
    totalTrips: history.summary.total_rides,
    totalSpent: history.summary.total_spent,
    averageTripCost: history.summary.total_rides ? history.summary.total_spent / history.summary.total_rides : 0,
    averageTripDistanceMiles: Number((history.summary.average_distance_km * 0.621371).toFixed(1)),
  };
}

export function groupActivitySections(items: RiderActivityItem[]): ActivitySectionGroup[] {
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const startOfYesterday = startOfToday - 86400000;

  const today = items.filter((item) => new Date(item.timestamp).getTime() >= startOfToday);
  const yesterday = items.filter((item) => {
    const value = new Date(item.timestamp).getTime();
    return value >= startOfYesterday && value < startOfToday;
  });

  const earlier = items.filter((item) => new Date(item.timestamp).getTime() < startOfYesterday);

  return [
    ...(today.length ? [{ label: "Today", items: today }] : []),
    ...(yesterday.length ? [{ label: "Yesterday", items: yesterday }] : []),
    ...(earlier.length ? [{ label: "Earlier", items: earlier }] : []),
  ];
}

export async function getRiderActivityById(activityId: string): Promise<RiderActivityDetail | null> {
  const currentRide = await getRiderCurrentRide();
  if (currentRide && currentRide.id === activityId) {
    return {
      id: currentRide.id,
      ride_id: currentRide.ride_id,
      type: "DRIVER_ASSIGNED",
      status: currentRide.status,
      title: currentRideTitle(currentRide.status),
      route_label: currentRide.short_route,
      pickup_address: currentRide.pickup_address,
      dropoff_address: currentRide.dropoff_address,
      driver_name: currentRide.driver_name,
      vehicle_label: currentRide.vehicle_label,
      plate_number: currentRide.plate_number,
      amount: currentRide.amount,
      currency: currentRide.currency,
      timestamp: new Date().toISOString(),
      payment_method: currentRide.payment_method,
      duration_minutes: null,
      distance_miles: null,
      receipt_available: false,
      rider_comment: null,
      rider_rating: null,
      ride_type: "On demand",
      event_note: "Track your active ride in real time.",
      cta_label: "Track ride",
      fare_breakdown: synthesizeFareBreakdown(currentRide.amount, currentRide.currency),
    };
  }

  const upcoming = await getRiderUpcomingRides();
  const upcomingMatch = upcoming.find((ride) => ride.id === activityId);
  if (upcomingMatch) {
    return {
      id: upcomingMatch.id,
      ride_id: upcomingMatch.ride_id,
      type: "SCHEDULED_RIDE",
      status: upcomingMatch.status,
      title: "Upcoming scheduled ride",
      route_label: upcomingMatch.short_route,
      pickup_address: upcomingMatch.pickup_address,
      dropoff_address: upcomingMatch.dropoff_address,
      driver_name: "Driver assigned later",
      vehicle_label: upcomingMatch.ride_type,
      plate_number: "—",
      amount: null,
      currency: "USD",
      timestamp: upcomingMatch.scheduled_for,
      payment_method: upcomingMatch.payment_method,
      duration_minutes: null,
      distance_miles: null,
      receipt_available: false,
      rider_comment: null,
      rider_rating: null,
      ride_type: upcomingMatch.ride_type,
      event_note: "Your scheduled trip is set and ready.",
      cta_label: "View details",
      fare_breakdown: synthesizeFareBreakdown(null),
    };
  }

  const activities = await getRiderActivity({ filter: "ALL" });
  const item = activities.find((entry) => entry.id === activityId);
  if (!item || !item.ride_id) {
    return null;
  }

  const ride = await getRideDetail(item.ride_id);
  return {
    ...item,
    pickup_address: ride.pickup_address || item.pickup_address,
    dropoff_address: ride.dropoff_address || item.dropoff_address,
    driver_name: ride.driver?.full_name || item.driver_name,
    vehicle_label: [ride.driver?.vehicle_make, ride.driver?.vehicle_model].filter(Boolean).join(" ").trim() || item.vehicle_label,
    plate_number: ride.driver?.plate_number || item.plate_number,
    duration_minutes: item.duration_minutes,
    distance_miles: item.distance_miles,
    payment_method: ride.payment_method || item.payment_method,
    rider_comment: ride.rider_comment,
    rider_rating: ride.rider_rating,
    receipt_available: ride.receipt_available,
    fare_breakdown: ride.fare_breakdown
      ? {
          base_fare: ride.fare_breakdown.base_fare,
          distance_time_fare: ride.fare_breakdown.distance_fare + ride.fare_breakdown.time_fare,
          fees: ride.fare_breakdown.booking_fee + ride.fare_breakdown.platform_fee,
          taxes: 0,
          tip: 0,
          total: ride.fare_breakdown.total,
          currency: item.currency,
        }
      : synthesizeFareBreakdown(ride.final_fare_amount ?? ride.estimated_fare ?? item.amount, item.currency),
  };
}

export async function downloadRideReceipt(rideId: string) {
  return downloadReceiptFromHistory(rideId);
}
