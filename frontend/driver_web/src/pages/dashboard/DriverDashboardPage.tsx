import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import {
  getActiveRide,
  getDriverProfile,
  getDriverStats,
  setAvailability,
} from "../../api/driverDashboard";
import { getOffers } from "../../api/driverOffers";
import { DriverAvailabilityCard } from "../../components/dashboard/DriverAvailabilityCard";
import { DriverGreetingHeader } from "../../components/dashboard/DriverGreetingHeader";
import { DriverStatsGrid } from "../../components/dashboard/DriverStatsGrid";
import { DriverStatusPanel } from "../../components/dashboard/DriverStatusPanel";
import { DriverLayout } from "../../components/layout/DriverLayout";
import type { DriverAvailability } from "../../types/driverOperations";

function getGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

function formatSubtext() {
  const dateText = new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
  return `${dateText} · Long Beach, CA`;
}

function toDashboardMode(availability: DriverAvailability) {
  if (availability === "BUSY") return "busy";
  if (availability === "ONLINE") return "online";
  return "offline";
}

export default function DriverDashboardPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const profileQuery = useQuery({
    queryKey: ["driver-profile"],
    queryFn: getDriverProfile,
  });
  const statsQuery = useQuery({
    queryKey: ["driver-stats"],
    queryFn: getDriverStats,
  });
  const activeRideQuery = useQuery({
    queryKey: ["active-ride"],
    queryFn: getActiveRide,
    refetchInterval: 5000,
  });
  const offersQuery = useQuery({
    queryKey: ["offers"],
    queryFn: getOffers,
    refetchInterval: 5000,
  });

  const availabilityMutation = useMutation({
    mutationFn: setAvailability,
    onSuccess: (result) => {
      queryClient.setQueryData(["driver-profile"], (current: Awaited<ReturnType<typeof getDriverProfile>> | undefined) =>
        current ? { ...current, availability: result.availability } : current,
      );
      void queryClient.invalidateQueries({ queryKey: ["driver-profile"] });
    },
    onError: () => {
      window.alert("Failed to update status");
    },
  });

  const profile = profileQuery.data;
  const activeRide = activeRideQuery.data;
  const pendingOffers = useMemo(
    () => (offersQuery.data ?? []).filter((offer) => offer.status === "PENDING"),
    [offersQuery.data],
  );
  const stats = statsQuery.data ?? {
    rides_today: 0,
    earned_today: 0,
    rating_avg: profile?.rating_avg ?? 0,
    total_rides: profile?.total_rides_completed ?? 0,
    currency: "USD",
  };

  const firstName = profile?.full_name?.split(/\s+/).filter(Boolean)[0] ?? "Driver";
  const greeting = `${getGreeting()}, ${firstName}`;
  const availabilityMode = toDashboardMode(profile?.availability ?? "OFFLINE");

  const handleToggleAvailability = () => {
    if (!profile || availabilityMutation.isPending || profile.availability === "BUSY") {
      return;
    }
    const nextStatus = profile.availability === "ONLINE" ? "OFFLINE" : "ONLINE";
    availabilityMutation.mutate(nextStatus);
  };

  const isLoading = profileQuery.isLoading && !profile;
  const isError = profileQuery.isError || !profile;

  return (
    <DriverLayout>
      <div className="min-h-full bg-white px-6 py-8 md:px-8">
        <div className="mx-auto max-w-6xl space-y-6">
          <DriverGreetingHeader
            greeting={greeting}
            subtext={formatSubtext()}
          />

          {isLoading ? (
            <div className="rounded-[22px] border border-[#E2E5DE] bg-white px-5 py-6 text-sm text-[#5A6B56]">
              Loading dashboard...
            </div>
          ) : isError ? (
            <div className="rounded-[22px] border border-[#E2E5DE] bg-white px-5 py-6 text-sm text-[#5A6B56]">
              <p>Unable to load the dashboard right now.</p>
              <button
                type="button"
                className="mt-4 rounded-xl border border-[#D7E9DD] px-4 py-2 text-sm font-medium text-[#1A6B45]"
                onClick={() => {
                  void profileQuery.refetch();
                }}
              >
                Retry
              </button>
            </div>
          ) : (
            <>
              <DriverAvailabilityCard
                mode={availabilityMode}
                onToggle={handleToggleAvailability}
                disabled={availabilityMutation.isPending || availabilityMode === "busy"}
              />

              <DriverStatsGrid
                ridesToday={stats.rides_today}
                earnedToday={stats.earned_today}
                rating={stats.rating_avg}
                totalRides={stats.total_rides}
              />

              <div className="grid gap-5 lg:grid-cols-2">
                {pendingOffers.length > 0 ? (
                  <DriverStatusPanel
                    variant="offer"
                    title={`${pendingOffers.length} new ride offer${pendingOffers.length > 1 ? "s" : ""} waiting`}
                    subtitle={`${pendingOffers[0].vehicle_type} · ${pendingOffers[0].estimated_distance_km.toFixed(1)} mi · $${pendingOffers[0].estimated_fare.toFixed(2)} estimated fare`}
                    ctaLabel="View offer"
                    onCtaClick={() => navigate("/offers")}
                  />
                ) : profile.availability === "ONLINE" ? (
                  <DriverStatusPanel
                    variant="waiting"
                    title="Waiting for requests"
                    subtitle="You'll be notified here and on your phone when a rider requests nearby"
                  />
                ) : (
                  <DriverStatusPanel
                    variant="offline"
                    title="You're offline"
                    subtitle="Toggle online above to start receiving requests"
                  />
                )}

                {activeRide ? (
                  <DriverStatusPanel
                    variant="active_ride"
                    title="Active ride - heading to pickup"
                    subtitle={activeRide.rider_name}
                    extraText={`${activeRide.dropoff_address} · $${activeRide.fare_amount.toFixed(2)}`}
                    ctaLabel="Continue ride"
                    onCtaClick={() => navigate("/rides/active")}
                  />
                ) : profile.availability === "ONLINE" ? (
                  <DriverStatusPanel
                    variant="waiting_more"
                    title="Still waiting for more"
                    subtitle="More requests may come in"
                  />
                ) : profile.reassignment_notice ? (
                  <DriverStatusPanel
                    variant="offline"
                    title="Ride reassigned"
                    subtitle={profile.reassignment_notice}
                    extraText={profile.reassigned_ride_id ? `Ride ${profile.reassigned_ride_id.slice(-8)} is no longer assigned to you.` : undefined}
                  />
                ) : (
                  <DriverStatusPanel
                    variant="offline"
                    title="No active ride"
                    subtitle="Go online to start receiving ride requests"
                  />
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </DriverLayout>
  );
}
