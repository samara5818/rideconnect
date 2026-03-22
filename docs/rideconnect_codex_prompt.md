# RideConnect Codex Prompt — UX Blueprint Implementation

Use this prompt in Codex to implement the RideConnect rider-facing booking and ride lifecycle UI exactly as specified.

---

## Prompt

You are implementing the RideConnect frontend UX in React.

Build a production-quality rider experience for a ride-hailing platform using the UX blueprint below.

## Tech stack
- React
- TypeScript
- Vite
- Tailwind CSS
- React Router
- Zustand or Context for UI state
- React Query for API state
- Leaflet for maps
- OpenStreetMap tiles
- OSRM or equivalent routing integration

## Design direction
The UI should feel like a modern ride-hailing product shell:
- search-first
- warm white surfaces
- living green accents
- compact and clear
- map-led, not form-led
- soft shadows
- rounded cards
- clean sans-heavy UI

Do not build a long editorial landing page.
This is an operational booking product.

## Core UX flow
Implement these rider screens:
1. Booking / Search
2. Ride options / vehicle selection
3. Searching for driver
4. Driver assigned
5. Driver arriving
6. Ride in progress
7. Ride completed
8. Activity / ride history
9. Profile

---

## Global app shell

### Header
Sticky white header.

Left:
- RideConnect wordmark

Center nav:
- Trips
- Reserve
- Courier
- Hourly
- Activity
- Profile

Right:
- avatar circle
- optional utility icon(s)
- Logout button

Header should remain minimal and clean.

---

## Screen 1 — Booking / Search page

### Layout
Desktop:
- left compact search panel
- right large map panel

Tablet:
- left search stack
- right map

Mobile:
- map on top, bottom sheet for route entry

### Left search panel requirements
Replace horizontal Ride / Reserve / Courier / Hourly tabs with a single dropdown.

#### Ride type dropdown
Label:
- Ride type

Options:
- Ride
- Reserve
- Courier
- Hourly

#### Pickup input
Use inline icon inside the input:
- round pickup marker icon

#### Destination input
Use inline icon inside the input:
- square destination marker icon

#### Swap button
Compact secondary button.

#### Schedule dropdown
Use dropdown with:
- Leave now
- Schedule

If Schedule selected:
- reveal date picker
- reveal time picker

#### Saved place chips
Show chips such as:
- Home
- Work
- LAX
- Downtown LA

#### Utility row
- Use current location
- Add stop

#### Primary action
- Search

### Map behavior on booking page
- show pickup marker when pickup exists
- show destination marker when destination exists
- show route polyline when both exist
- fit map to route
- show zoom controls

### API integration
On Search:
- call fare estimate endpoint
- store route metrics and estimate
- open ride options column

---

## Screen 2 — Ride options / vehicle selection

### Layout
Desktop becomes 3-column:
- left: search panel
- center: ride options panel
- right: map

### Ride options panel
Show a vertical list of ride option cards.

Each card must include:
- product name
- short descriptor
- ETA to pickup
- price
- capacity
- optional luggage detail

Example products:
- Economy
- Comfort
- XL

### Card states
- default
- hover
- selected
- unavailable

### Sticky bottom request bar
When a ride option is selected, show a sticky summary bar containing:
- selected fare
- route duration
- route distance
- selected product name
- Request Ride button

Example:
- $58.68 | 34 min | 23.6 mi | Economy
- Request Ride

### API integration
On Request Ride:
- call request ride endpoint
- transition UI to Matching screen/state

---

## Screen 3 — Searching for driver

### Goal
Show that the system is matching a rider to a driver.

### UI
- map remains visible
- route still visible
- animated pulse or search indicator
- selected product summary
- estimate summary
- cancel ride action

### Copy
Examples:
- Finding a nearby driver...
- Matching you with the best available driver...

### State
Map should not disappear.
This is still a map-first experience.

---

## Screen 4 — Driver assigned

### Goal
Show accepted driver and trust-critical details.

### Driver card contents
- driver avatar or initials
- driver name
- rating
- car make/model
- color
- license plate
- ETA to pickup

### Actions
- Call
- Message
- Cancel Ride

### Map state
- driver live marker
- pickup marker
- route from driver to pickup

### Notification support
Prepare UI to reflect assigned notification state.

---

## Screen 5 — Driver arriving

### Goal
Support pickup readiness.

### UI
- prominent ETA chip
- label: Driver is on the way
- pickup address or pickup point label
- driver card retained

### Actions
- Call
- Message
- optional share trip

### Map state
- driver marker updates live
- route to pickup updates

### Arrival substate
If driver has arrived:
- replace ETA copy with Driver has arrived
- make pickup point highly visible

---

## Screen 6 — Ride in progress

### Goal
Support trip visibility and safety.

### UI
- Trip in progress label
- ETA to destination
- remaining distance/time
- current route map
- destination label

### Actions
- Share trip
- Emergency
- Message driver

### Map state
- moving car marker
- route progress visible
- destination pinned

---

## Screen 7 — Ride completed

### Goal
Close the trip clearly and support receipt + rating.

### UI
Show:
- Trip complete heading
- receipt summary card
- rating module
- optional tip action
- Done button

### Receipt line items
- Trip fare
- Booking / platform fee
- Tolls if any
- Discounts if any
- Total charged

### Actions
- Rate driver
- Add tip
- View receipt
- Done

---

## Screen 8 — Activity / ride history

### Goal
Show upcoming, ongoing, and past rides.

### Layout
List-first page.

### Sections
- Upcoming
- Ongoing
- Past

### Ride history item contents
- route
- date/time
- status
- price
- receipt shortcut
- driver name if completed

### Filters
- All
- Upcoming
- Completed
- Cancelled

### Actions
- View details
- View receipt
- Rebook route placeholder

---

## Screen 9 — Profile

### Goal
Manage identity and saved preferences.

### Sections
- account summary
- saved places
- payment methods placeholder
- ride preferences
- notifications
- help & support
- logout

### Saved places block
- Home
- Work
- Add a place

### Preferences examples
- quiet ride
- luggage needs
- accessibility preferences

---

## Responsive behavior

### Desktop
- booking: 2 columns before search, 3 columns after search
- map large and always visible

### Tablet
- 2 columns
- search and options can stack in left column
- map remains dominant

### Mobile
- map on top
- bottom sheet for search
- ride options slide up after search
- matching/tracking use persistent bottom sheets over map

---

## Component architecture
Create reusable components:
- AppHeader
- RideTypeDropdown
- RouteInput
- ScheduleSelector
- SavedPlaceChips
- RideOptionCard
- StickyRequestBar
- DriverCard
- TrackingMap
- ReceiptCard
- ActivityHistoryList
- ProfileSections

---

## State model
Use a clear UI state machine.

Route booking states:
- idle
- route_ready
- estimate_ready
- ride_selected
- requesting
- matching
- driver_assigned
- driver_arriving
- ride_started
- ride_completed

Persist route + ride state cleanly across screens.

---

## API contract assumptions
Use these frontend integrations:
- POST /api/v1/fares/estimate
- POST /api/v1/rides/request
- GET /api/v1/rides/{ride_id}
- GET /api/v1/rides/{ride_id}/tracking
- POST /api/v1/rides/{ride_id}/cancel
- GET /api/v1/users/me/notifications

Handle polling for tracking and ride status.
No websocket requirement yet.

---

## Visual rules
- warm white page background
- clean white cards
- green accent for primary actions
- soft neutral borders
- soft shadow depth
- large comfortable map
- rounded corners
- no cluttered dashboards
- avoid over-explaining in the first step

---

## Important booking-page change requirements
Apply these exactly:

1. Remove Ride / Reserve / Courier / Hourly tabs from the left pane.
2. Replace them with a dropdown.
3. Move pickup and destination icons inside the text fields.
4. Do not show “For me / Someone else” in the first stage. That can come later in deeper ride details if needed.
5. Use a Leave now / Schedule dropdown.
6. If Schedule is selected, reveal date/time controls.
7. After clicking Search, open a new center column with ride types.
8. In that new column, show car type, fare, and arrival ETA.
9. Bottom request bar should reflect the selected ride type.

---

## Output expectation
Implement the UI as a working React app structure with:
- page components
- reusable components
- mocked API integration layer if needed
- responsive layout
- Leaflet map integration
- realistic placeholder data for ride options, driver assignment, tracking, and history

Build it in a way that can be connected directly to the backend later.
