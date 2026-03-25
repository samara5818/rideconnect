import { useEffect } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { cancelRide, getRideDetail } from "../api/rides";
import { useRideStatus } from "../hooks/useRideStatus";
import { useRideContext } from "../context/RideContext";
import { MobileNav } from "../components/common/MobileNav";
import { SearchingState } from "../components/tracking/SearchingState";
import { TrackingMap } from "../components/tracking/TrackingMap";
import { DriverStatusPanel } from "../components/tracking/DriverStatusPanel";
import { useToast } from "../components/common/Toast";
import styles from "./RideTrackingPage.module.css";

export function RideTrackingPage() {
  const { rideId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const toast = useToast();
  const rideContext = useRideContext();
  const statusQuery = useRideStatus(rideId ?? null);
  const detailQuery = useQuery({
    queryKey: ["ride-detail", rideId],
    queryFn: () => getRideDetail(rideId as string),
    enabled: Boolean(rideId),
  });

  const status = statusQuery.data?.status ?? "MATCHING";
  const driver = statusQuery.data?.driver ?? detailQuery.data?.driver ?? null;
  const dispatchRetryCount = statusQuery.data?.dispatch_retry_count ?? detailQuery.data?.dispatch_retry_count ?? 0;
  const isRedispatching = (status === "REQUESTED" || status === "MATCHING") && dispatchRetryCount > 0;
  const pickupLabel = rideContext.pickup?.display_name ?? detailQuery.data?.pickup_address ?? "Pickup";
  const dropoffLabel = rideContext.dropoff?.display_name ?? detailQuery.data?.dropoff_address ?? "Drop-off";

  useEffect(() => {
    if (status === "RIDE_COMPLETED" && rideId) {
      rideContext.setActiveRideId(null);
      rideContext.setFareEstimateData(null);
      void Promise.all([
        queryClient.invalidateQueries({ queryKey: ["rider-activity-stats"] }),
        queryClient.invalidateQueries({ queryKey: ["rider-activity-design"] }),
      ]);
      navigate(`/ride/complete/${rideId}`, { replace: true });
    }
    if (status === "CANCELLED") {
      rideContext.clearRide();
      toast.showError("Ride was cancelled");
      navigate("/home", { replace: true });
    }
    if (status === "NO_DRIVERS_FOUND") {
      rideContext.setActiveRideId(null);
    }
  }, [navigate, queryClient, rideContext, rideId, status, toast]);

  async function handleCancel() {
    if (!rideId) return;
    await cancelRide(rideId);
    rideContext.clearRide();
    navigate("/");
  }

  function handleRetrySearch() {
    rideContext.setActiveRideId(null);
    rideContext.setFareEstimateData(null);
    rideContext.setSelectedFare(null);
    navigate("/home", { replace: true });
  }

  function handleViewActivity() {
    rideContext.setActiveRideId(null);
    navigate("/activity", { replace: true });
  }

  if (status === "REQUESTED" || status === "MATCHING" || status === "NO_DRIVERS_FOUND") {
    return (
      <div className={styles.page}>
        <MobileNav />
        <SearchingState
          pickup={pickupLabel}
          dropoff={dropoffLabel}
          vehicle={rideContext.selectedVehicleType ?? detailQuery.data?.vehicle_type ?? "ECONOMY"}
          fare={rideContext.selectedFare ?? detailQuery.data?.estimated_fare ?? 0}
          payment={rideContext.paymentMethod ?? detailQuery.data?.payment_method ?? "CASH"}
          onCancel={() => void handleCancel()}
          mode={status === "NO_DRIVERS_FOUND" ? "no_drivers_found" : isRedispatching ? "redispatching" : "matching"}
          onRetry={handleRetrySearch}
          onViewActivity={handleViewActivity}
        />
      </div>
    );
  }

  if (!driver) {
    if (detailQuery.isLoading) {
      return (
        <div className={styles.page}>
          <MobileNav />
          <SearchingState
            pickup={pickupLabel}
            dropoff={dropoffLabel}
            vehicle={rideContext.selectedVehicleType ?? "ECONOMY"}
            fare={rideContext.selectedFare ?? detailQuery.data?.estimated_fare ?? 0}
            payment={rideContext.paymentMethod ?? detailQuery.data?.payment_method ?? "CASH"}
            onCancel={() => void handleCancel()}
          />
        </div>
      );
    }
    return <Navigate replace to="/" />;
  }

  if (!rideContext.pickup || !rideContext.dropoff) {
    return (
      <div className={styles.page}>
        <MobileNav />
        <div className={styles.mobileLayout}>
          <DriverStatusPanel
            status={status}
            driver={driver}
            etaMinutes={statusQuery.data?.eta_minutes ?? driver.eta_minutes}
            distanceLabel="—"
            paymentMethod={rideContext.paymentMethod ?? detailQuery.data?.payment_method ?? "CASH"}
            onCancel={() => void handleCancel()}
          />
        </div>
      </div>
    );
  }

  const geometry: [number, number][] = [
    [rideContext.pickup.latitude, rideContext.pickup.longitude],
    [rideContext.dropoff.latitude, rideContext.dropoff.longitude],
  ];

  return (
    <div className={styles.page}>
      <MobileNav />
      <div className={styles.mobileLayout}>
        <div className={styles.mobileMap}>
          <TrackingMap pickup={rideContext.pickup} dropoff={rideContext.dropoff} driver={driver} geometry={geometry} status={status} />
        </div>
        <DriverStatusPanel
          status={status}
          driver={driver}
          etaMinutes={statusQuery.data?.eta_minutes ?? driver.eta_minutes}
          distanceLabel={`${(rideContext.fareEstimateData?.route_distance_km ?? 0).toFixed(1)} mi`}
          paymentMethod={rideContext.paymentMethod}
          onCancel={() => void handleCancel()}
        />
      </div>
    </div>
  );
}
