import styles from "./SearchingState.module.css";

function paymentLabel(value: string) {
  if (value === "DIGITAL_WALLET") return "Wallet";
  if (value === "CARD") return "Card";
  return "Cash";
}

export function SearchingState({
  pickup,
  dropoff,
  vehicle,
  fare,
  payment,
  onCancel,
  mode = "matching",
  title,
  subtitle,
  onRetry,
  onViewActivity,
}: {
  pickup: string;
  dropoff: string;
  vehicle: string;
  fare: number;
  payment: string;
  onCancel: () => void;
  mode?: "matching" | "redispatching" | "no_drivers_found";
  title?: string;
  subtitle?: string;
  onRetry?: () => void;
  onViewActivity?: () => void;
}) {
  const noDriversFound = mode === "no_drivers_found";
  const redispatching = mode === "redispatching";
  const resolvedTitle = title ?? (noDriversFound ? "No drivers available right now" : redispatching ? "Finding another driver" : "Finding your driver");
  const resolvedSubtitle =
    subtitle ??
    (noDriversFound
      ? "All nearby drivers missed the request. You can try again or check your activity."
      : redispatching
        ? "Your previous driver could not reach pickup in time. We are searching for another nearby driver now."
        : `Looking for nearby ${vehicle} drivers...`);

  return (
    <div className={styles.wrapper}>
      {!noDriversFound ? <div className={styles.spinner} /> : <div className={styles.resultIcon}>!</div>}
      <h1 className={styles.title}>{resolvedTitle}</h1>
      <p className={styles.subtitle}>{resolvedSubtitle}</p>
      <div className={styles.pill}>
        {!noDriversFound ? (
          <>
            <span className={styles.dot} />
            <span className={styles.dot} />
            <span className={styles.dot} />
          </>
        ) : null}
        <span>{noDriversFound ? "No drivers found" : redispatching ? "Re-matching" : "Matching"}</span>
      </div>
      <div className={styles.tripCard}>
        <div className={styles.stop}><span className={styles.pickupDot} />{pickup}</div>
        <div className={styles.connector} />
        <div className={styles.stop}><span className={styles.dropoffDot} />{dropoff}</div>
      </div>
      <p className={styles.summary}>
        <span>{vehicle}</span>
        <span>${fare.toFixed(2)}</span>
        <span>{paymentLabel(payment)}</span>
      </p>
      {noDriversFound ? (
        <div className={styles.actionRow}>
          <button type="button" className={styles.primaryAction} onClick={onRetry}>
            Search again
          </button>
          <button type="button" className={styles.cancel} onClick={onViewActivity}>
            View activity
          </button>
        </div>
      ) : (
        <button type="button" className={styles.cancel} onClick={onCancel}>
          Cancel ride request
        </button>
      )}
    </div>
  );
}
