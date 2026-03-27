import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { getRegions, type RegionRecord } from '../api/admin';
import { createDriver, getOnboardingQueue, type CreateDriverPayload } from '../api/onboarding';
import { PageTitle } from '../components/common/PageTitle';
import { OnboardingFilters } from '../components/onboarding/OnboardingFilters';
import { OnboardingTable } from '../components/onboarding/OnboardingTable';
import type { OnboardingQueueItem } from '../types/onboarding';

const emptyDriverForm: CreateDriverPayload = {
  name: '',
  email: '',
  phone: '',
  password: '',
  region_id: '',
  vehicle_make: '',
  vehicle_model: '',
  vehicle_year: '',
  vehicle_color: '',
  vehicle_class: '',
  vehicle_license_plate: '',
  vehicle_mpg: '',
};

export function OnboardingPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const initialStatusFilter = searchParams.get('status') ?? '';
  const initialRegionFilter = searchParams.get('region') ?? '';
  const initialSearch = searchParams.get('search') ?? '';

  const [items, setItems] = useState<OnboardingQueueItem[]>([]);
  const [regions, setRegions] = useState<RegionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creatingDriver, setCreatingDriver] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [driverForm, setDriverForm] = useState<CreateDriverPayload>(emptyDriverForm);

  const [statusFilter, setStatusFilter] = useState(initialStatusFilter);
  const [regionFilter, setRegionFilter] = useState(initialRegionFilter);
  const [search, setSearch] = useState(initialSearch);

  useEffect(() => {
    getRegions().then(setRegions).catch(() => setRegions([]));
  }, []);

  useEffect(() => {
    const nextStatus = searchParams.get('status') ?? '';
    const nextRegion = searchParams.get('region') ?? '';
    const nextSearch = searchParams.get('search') ?? '';

    setStatusFilter((current) => (current === nextStatus ? current : nextStatus));
    setRegionFilter((current) => (current === nextRegion ? current : nextRegion));
    setSearch((current) => (current === nextSearch ? current : nextSearch));
  }, [searchParams]);

  useEffect(() => {
    const nextParams = new URLSearchParams();
    if (statusFilter) nextParams.set('status', statusFilter);
    if (regionFilter) nextParams.set('region', regionFilter);
    if (search) nextParams.set('search', search);

    const currentParams = searchParams.toString();
    const updatedParams = nextParams.toString();
    if (currentParams !== updatedParams) {
      setSearchParams(nextParams, { replace: true });
    }
  }, [regionFilter, search, searchParams, setSearchParams, statusFilter]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const response = await getOnboardingQueue({
          status: statusFilter || undefined,
          search: search || undefined,
        });
        if (!cancelled) {
          setItems(response.items);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : 'Unknown error');
          setItems([]);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [search, statusFilter]);

  function updateDriverForm<K extends keyof CreateDriverPayload>(key: K, value: CreateDriverPayload[K]) {
    setDriverForm((current) => ({ ...current, [key]: value }));
  }

  async function handleCreateDriver(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreatingDriver(true);
    setCreateError(null);
    try {
      await createDriver({
        ...driverForm,
        vehicle_mpg: driverForm.vehicle_mpg || undefined,
      });
      setIsCreateModalOpen(false);
      setDriverForm(emptyDriverForm);
      setSearch(driverForm.name);
      const response = await getOnboardingQueue({
        status: statusFilter || undefined,
        search: driverForm.name || undefined,
      });
      setItems(response.items);
    } catch (loadError) {
      setCreateError(loadError instanceof Error ? loadError.message : 'Unable to create driver');
    } finally {
      setCreatingDriver(false);
    }
  }

  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      if (regionFilter) {
        const region = regions.find((entry) => entry.id === regionFilter);
        if (!region || item.region_name !== region.name) {
          return false;
        }
      }
      return true;
    });
  }, [items, regionFilter, regions]);

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <PageTitle title="Onboarding" subtitle="Review and manage driver applications across active regions." />
        <button
          type="button"
          onClick={() => setIsCreateModalOpen(true)}
          className="inline-flex h-11 items-center justify-center rounded-2xl bg-accent px-5 text-sm font-semibold text-white transition hover:bg-accentDark"
        >
          Onboard Driver
        </button>
      </div>

      <OnboardingFilters
        statusFilter={statusFilter}
        regionFilter={regionFilter}
        search={search}
        onStatusChange={setStatusFilter}
        onRegionChange={setRegionFilter}
        onSearchChange={setSearch}
        regions={regions}
      />

      <OnboardingTable
        items={filteredItems}
        loading={loading}
        error={error}
        totalItems={filteredItems.length}
        onReview={(driverId) => navigate(`/onboarding/${driverId}`)}
      />

      {isCreateModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#17211b]/35 px-4 py-8">
          <div className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-[28px] border border-line bg-white p-6 shadow-[0_24px_80px_rgba(20,20,20,0.18)]">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-2xl font-semibold text-ink">Onboard Driver</h2>
                <p className="mt-1 text-sm text-muted">Create the driver account, vehicle record, and onboarding profile from the admin queue.</p>
              </div>
              <button
                type="button"
                onClick={() => {
                  setIsCreateModalOpen(false);
                  setCreateError(null);
                }}
                className="rounded-xl border border-line px-3 py-2 text-sm text-muted transition hover:bg-[#f7f5ef]"
              >
                Close
              </button>
            </div>

            <form className="mt-6 space-y-6" onSubmit={handleCreateDriver}>
              <div className="grid gap-4 md:grid-cols-2">
                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-ink">Driver Name</span>
                  <input
                    className="h-12 w-full rounded-2xl border border-line px-4 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/15"
                    value={driverForm.name}
                    onChange={(event) => updateDriverForm('name', event.target.value)}
                    placeholder="Ram Teja"
                    required
                  />
                </label>

                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-ink">Region</span>
                  <select
                    className="h-12 w-full rounded-2xl border border-line bg-white px-4 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/15"
                    value={driverForm.region_id}
                    onChange={(event) => updateDriverForm('region_id', event.target.value)}
                    required
                  >
                    <option value="">Select a region</option>
                    {regions.map((region) => (
                      <option key={region.id} value={region.id}>
                        {region.name}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-ink">Email</span>
                  <input
                    className="h-12 w-full rounded-2xl border border-line px-4 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/15"
                    type="email"
                    value={driverForm.email}
                    onChange={(event) => updateDriverForm('email', event.target.value)}
                    placeholder="driver@example.com"
                    required
                  />
                </label>

                <label className="block">
                  <span className="mb-2 block text-sm font-medium text-ink">Phone</span>
                  <input
                    className="h-12 w-full rounded-2xl border border-line px-4 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/15"
                    value={driverForm.phone}
                    onChange={(event) => updateDriverForm('phone', event.target.value)}
                    placeholder="+1 555 780 2235"
                    required
                  />
                </label>

                <label className="block md:col-span-2">
                  <span className="mb-2 block text-sm font-medium text-ink">Temporary Password</span>
                  <input
                    className="h-12 w-full rounded-2xl border border-line px-4 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/15"
                    type="password"
                    value={driverForm.password}
                    onChange={(event) => updateDriverForm('password', event.target.value)}
                    placeholder="RideConnect123!"
                    required
                  />
                </label>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-ink">Vehicle</h3>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-ink">Make</span>
                    <input className="h-12 w-full rounded-2xl border border-line px-4 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/15" value={driverForm.vehicle_make} onChange={(event) => updateDriverForm('vehicle_make', event.target.value)} placeholder="Toyota" required />
                  </label>
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-ink">Model</span>
                    <input className="h-12 w-full rounded-2xl border border-line px-4 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/15" value={driverForm.vehicle_model} onChange={(event) => updateDriverForm('vehicle_model', event.target.value)} placeholder="Camry" required />
                  </label>
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-ink">Year</span>
                    <input className="h-12 w-full rounded-2xl border border-line px-4 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/15" type="number" min="2000" max="2100" value={driverForm.vehicle_year} onChange={(event) => updateDriverForm('vehicle_year', event.target.value === '' ? '' : Number(event.target.value))} placeholder="2023" required />
                  </label>
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-ink">Color</span>
                    <input className="h-12 w-full rounded-2xl border border-line px-4 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/15" value={driverForm.vehicle_color} onChange={(event) => updateDriverForm('vehicle_color', event.target.value)} placeholder="Silver" required />
                  </label>
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-ink">Vehicle Class</span>
                    <input className="h-12 w-full rounded-2xl border border-line px-4 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/15" value={driverForm.vehicle_class} onChange={(event) => updateDriverForm('vehicle_class', event.target.value)} placeholder="STANDARD" required />
                  </label>
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-ink">License Plate</span>
                    <input className="h-12 w-full rounded-2xl border border-line px-4 text-sm uppercase outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/15" value={driverForm.vehicle_license_plate} onChange={(event) => updateDriverForm('vehicle_license_plate', event.target.value.toUpperCase())} placeholder="8ABC123" required />
                  </label>
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium text-ink">MPG</span>
                    <input className="h-12 w-full rounded-2xl border border-line px-4 text-sm outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/15" value={driverForm.vehicle_mpg ?? ''} onChange={(event) => updateDriverForm('vehicle_mpg', event.target.value)} placeholder="32" />
                  </label>
                </div>
              </div>

              {createError ? <div className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{createError}</div> : null}

              <div className="flex flex-col-reverse gap-3 border-t border-line pt-5 sm:flex-row sm:justify-end">
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="h-11 rounded-2xl border border-line px-5 text-sm font-medium text-ink transition hover:bg-[#f7f5ef]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingDriver}
                  className="h-11 rounded-2xl bg-accent px-5 text-sm font-semibold text-white transition hover:bg-accentDark disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {creatingDriver ? 'Creating driver...' : 'Create Driver'}
                </button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
    </div>
  );
}
