import { useMemo, useState } from 'react';

import { useDashboardSummary } from '../hooks/useDashboard';
import { useActiveRides } from '../hooks/useRides';
import { useDriversList } from '../hooks/useDrivers';
import { useDashboardPresenceStream } from '../hooks/useDashboardPresenceStream';
import { DataTable } from '../components/DataTable';
import { StatusBadge } from '../components/StatusBadge';
import { Avatar } from '../components/Avatar';
import { VehicleTypeBadge } from '@shared/components/vehicle';
import type { VehicleType } from '@shared/types/vehicle';
import { formatDistanceToNow, parseISO } from 'date-fns';
import type { ActiveRide } from '../types/admin';
import styles from './DashboardPage.module.css';

const STAT_CARDS = [
  { key: 'active_rides', label: 'Active Rides', icon: '🚗', sub: 'Live right now' },
  { key: 'online_drivers', label: 'Drivers Online', icon: '👤', sub: 'Currently active' },
  { key: 'matching_rides', label: 'Matching Rides', icon: '🔄', sub: 'Awaiting driver' },
  { key: 'pending_onboarding_reviews', label: 'Pending Onboarding', icon: '📋', sub: 'Need review' },
];

export function DashboardPage() {
  useDashboardPresenceStream(true);
  const { data: summary, isLoading: summaryLoading } = useDashboardSummary();
  const { data: rides, isLoading: ridesLoading } = useActiveRides();
  const { data: driversResponse, isLoading: driversLoading } = useDriversList({ page_size: 100 });
  const [showOnlineDrivers, setShowOnlineDrivers] = useState(false);

  const onlineDrivers = useMemo(
    () => (driversResponse?.items ?? []).filter((driver) => driver.is_online),
    [driversResponse]
  );

  const columns = [
    {
      key: 'ride_id',
      header: 'ID',
      width: '120px',
      render: (r: Record<string, unknown>) => (
        <div className={styles.idCell}>
          <span className={styles.idValue}>{String(r.ride_id ?? '').slice(-8)}</span>
          <span className={styles.idMeta}>{String(r.status ?? '').replaceAll('_', ' ')}</span>
        </div>
      ),
    },
    {
      key: 'rider_name',
      header: 'Rider',
      render: (r: Record<string, unknown>) => {
        const riderName = String(r.rider_name || 'Rider');
        return (
          <div className={styles.personCell}>
            <Avatar name={riderName} size="sm" />
            <div className={styles.personCopy}>
              <span className={styles.primaryText}>{riderName}</span>
              <span className={styles.secondaryText}>{String(r.pickup_address ?? 'Pickup pending')}</span>
            </div>
          </div>
        );
      },
    },
    {
      key: 'driver_name',
      header: 'Driver',
      render: (r: Record<string, unknown>) => {
        const driverName = String(r.driver_name || 'Awaiting match');
        return (
          <div className={styles.personCell}>
            <Avatar name={driverName} size="sm" />
            <div className={styles.personCopy}>
              <span className={styles.primaryText}>{driverName}</span>
              <span className={styles.secondaryText}>{String(r.dropoff_address ?? 'Dropoff pending')}</span>
            </div>
          </div>
        );
      },
    },
    {
      key: 'region',
      header: 'Region',
      render: (r: Record<string, unknown>) => (
        <div className={styles.productCell}>
          {typeof r.product_type === 'string' ? <VehicleTypeBadge type={r.product_type as VehicleType} size="xs" /> : <span className={styles.mutedValue}>Awaiting match</span>}
          <span className={styles.secondaryText}>{String(r.region ?? 'Dispatch region pending')}</span>
        </div>
      ),
    },
    { key: 'status', header: 'Status', render: (r: Record<string, unknown>) => <StatusBadge status={String(r.status ?? '')} size="sm" /> },
    {
      key: 'eta_minutes',
      header: 'ETA',
      render: (r: Record<string, unknown>) => (
        <div className={styles.etaCell}>
          <span className={styles.primaryText}>{r.eta_minutes != null ? `${r.eta_minutes} min` : '—'}</span>
          <span className={styles.secondaryText}>
            {r.requested_at ? new Date(String(r.requested_at)).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }) : 'Requested now'}
          </span>
        </div>
      ),
    },
    {
      key: 'requested_at',
      header: 'Requested',
      render: (r: Record<string, unknown>) => {
        try {
          return <span className={styles.primaryText}>{formatDistanceToNow(parseISO(String(r.requested_at)), { addSuffix: true })}</span>;
        } catch {
          return <span className={styles.mutedValue}>—</span>;
        }
      },
    },
    { key: 'fare', header: 'Fare', render: (r: Record<string, unknown>) => r.fare != null ? `$${Number(r.fare).toFixed(2)}` : '—' },
  ];

  const statsValue = (key: string) => {
    if (!summary) return 0;
    return (summary as Record<string, unknown>)[key] as number ?? 0;
  };

  return (
    <div className={styles.root}>
      <h1 className={styles.title}>Dashboard</h1>

      <div className={styles.cards}>
        {summaryLoading
          ? Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className={styles.cardSkeleton}>
                <div className={`${styles.skLine} ${styles.wide}`} style={{ height: 32, marginBottom: 10 }} />
                <div className={`${styles.skLine} ${styles.narrow}`} />
              </div>
            ))
          : STAT_CARDS.map((card) => (
              <button
                key={card.key}
                type="button"
                className={`${styles.card} ${card.key === 'online_drivers' ? styles.cardButton : ''} ${
                  card.key === 'online_drivers' && showOnlineDrivers ? styles.cardActive : ''
                }`}
                onClick={() => {
                  if (card.key === 'online_drivers') {
                    setShowOnlineDrivers((current) => !current);
                  }
                }}
                disabled={card.key !== 'online_drivers'}
              >
                <div className={styles.cardLeft}>
                  <div className={styles.cardNum}>{statsValue(card.key)}</div>
                  <div className={styles.cardLabel}>{card.label}</div>
                  <div className={styles.cardSub}>{card.sub}</div>
                </div>
                <span className={styles.cardIcon}>{card.icon}</span>
              </button>
            ))}
      </div>

      {showOnlineDrivers ? (
        <div className={styles.onlinePanel}>
          <div className={styles.onlinePanelHeader}>
            <div>
              <h2 className={styles.sectionTitle}>Online Drivers</h2>
              <p className={styles.panelSub}>Live list from the current driver fleet. No page reload.</p>
            </div>
            <button
              type="button"
              className={styles.closeIcon}
              onClick={() => setShowOnlineDrivers(false)}
              aria-label="Close online drivers panel"
            >
              ×
            </button>
          </div>

          {driversLoading ? (
            <div className={styles.onlineList}>
              {Array.from({ length: 4 }).map((_, index) => (
                <div key={index} className={styles.onlineRowSkeleton}>
                  <div className={`${styles.skLine} ${styles.wide}`} />
                  <div className={`${styles.skLine} ${styles.narrow}`} />
                </div>
              ))}
            </div>
          ) : onlineDrivers.length ? (
            <div className={styles.onlineList}>
              {onlineDrivers.map((driver) => {
                const name = [driver.first_name, driver.last_name].filter(Boolean).join(' ').trim() || 'Driver';
                const vehicleLabel = driver.vehicle
                  ? `${driver.vehicle.year} ${driver.vehicle.make} ${driver.vehicle.model}`
                  : 'Vehicle not added';
                const locationLabel =
                  driver.lat != null && driver.lng != null
                    ? `${Number(driver.lat).toFixed(5)}, ${Number(driver.lng).toFixed(5)}`
                    : 'Current location unavailable';

                return (
                  <div key={driver.driver_id} className={styles.onlineRow}>
                    <div className={styles.onlinePerson}>
                      <Avatar name={name} size="sm" />
                      <div className={styles.personCopy}>
                        <span className={styles.primaryText}>{name}</span>
                        <span className={styles.secondaryText}>{driver.region_name ?? 'Region pending'}</span>
                      </div>
                    </div>

                    <div className={styles.onlineMeta}>
                      <span className={styles.primaryText}>{vehicleLabel}</span>
                      <span className={styles.secondaryText}>
                        {driver.is_available ? 'Available for rides' : 'Online but unavailable'}
                      </span>
                    </div>

                    <div className={styles.onlineMeta}>
                      <span className={styles.primaryText}>Current location</span>
                      <span className={styles.secondaryText}>{locationLabel}</span>
                    </div>

                    <div className={styles.onlineMetaRight}>
                      <StatusBadge status={driver.is_available ? 'ONLINE' : 'UNAVAILABLE'} size="sm" />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className={styles.emptyPanel}>No drivers are online right now.</div>
          )}
        </div>
      ) : null}

      <div>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>Rides by Region</h2>
          <div className={styles.sectionActions}>
            <button className={styles.btn}>Wait Rides</button>
            <button className={styles.btn}>Search Rides</button>
          </div>
        </div>
        <div style={{ marginTop: 12 }}>
          <DataTable
            columns={columns}
            rows={(rides ?? []).slice(0, 10) as Record<string, unknown>[]}
            isLoading={ridesLoading}
            emptyMessage="No active rides right now."
          />
        </div>
      </div>
    </div>
  );
}
