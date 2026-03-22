# RideConnect UX Blueprint

## Purpose
This document defines the complete rider-facing UX blueprint for RideConnect, covering the end-to-end booking and trip journey from route entry to trip completion, plus activity and profile surfaces.

## Product direction
RideConnect should feel:
- search-first
- fast to understand
- low-friction for repeat riders
- map-led, not form-heavy
- warm and modern, but operationally clear

The booking shell should prioritize:
1. route entry
2. fast estimate preview
3. ride-type comparison
4. request confirmation
5. real-time trip tracking
6. post-trip visibility and trust

---

# 1. Experience principles

## 1.1 Search first
The primary booking page should open in route-entry mode, not a long booking form.

## 1.2 Progressive disclosure
Do not ask for everything upfront. Show deeper details only when the rider advances.

## 1.3 Map as a decision surface
The map should help the rider understand:
- pickup point
- destination point
- route shape
- distance context
- driver movement later in the lifecycle

## 1.4 One primary action per step
Each screen should make the next action obvious:
- Search
- Select ride
- Request ride
- Track driver
- Rate ride

## 1.5 Rider fare vs driver payout separation
The rider journey should show rider-facing fare components only. Driver payout logic is backend-only unless specifically exposed in driver surfaces.

---

# 2. End-to-end rider journey

## Core screen sequence
1. Booking / Search
2. Ride options / vehicle selection
3. Matching / searching for driver
4. Driver assigned
5. Driver arriving
6. Ride in progress
7. Ride completed / receipt
8. Activity / ride history
9. Profile / saved places / preferences

---

# 3. Booking / Search screen

## Goal
Allow the rider to enter route information quickly and preview the route on the map.

## Desktop layout
Three-part shell after search, but initial state is two-part:
- left: compact search panel
- right: map workspace

## Header
- RideConnect wordmark
- primary nav: Trips, Reserve, Courier, Hourly, Activity, Profile
- right-side utilities: avatar, search/help icon if needed, logout

## Left panel content
### Ride mode selector
Use a single dropdown instead of horizontal tabs.

Label:
- Ride type

Options:
- Ride
- Reserve
- Courier
- Hourly

### Pickup input
Use inline icon inside the field:
- pickup icon: round dot

Placeholder examples:
- Enter pickup location
- Use current location

Default behavior:
- if location permission granted, prefill with current location label
- otherwise leave empty with helper CTA

### Destination input
Use inline icon inside the field:
- destination icon: square stop marker

Placeholder:
- Where to?

### Swap button
Compact button aligned near the route inputs.

### Schedule selector
Use a dropdown:
- Leave now
- Schedule

If `Leave now`:
- no extra controls shown

If `Schedule`:
- reveal date picker
- reveal time picker
- optional helper text: pickup window or selected pickup time

### Suggestion chips
Show compact chips for fast re-entry:
- Home
- Work
- LAX
- Downtown LA

### Utility actions
- Use current location
- Add stop

`Add stop` can remain visible but secondary.

## Right panel map state
Map should show:
- pickup marker when pickup exists
- destination marker when destination exists
- route polyline when both exist
- zoom controls
- optional fit-to-route behavior

## Primary CTA
- Search

## UX notes
- Keep labels short
- Use inline icons to save vertical space
- Do not show passenger details or trust/fare breakdown here yet

---

# 4. Ride options / vehicle selection screen

## Trigger
Appears after the rider clicks Search and a valid route estimate is available.

## Layout
Now expand to three columns on desktop:
- left: search panel (still visible)
- center: ride options column
- right: map panel

## Center column purpose
Allow the rider to compare available ride products and choose one.

## Ride option card contents
Each card should include:
- vehicle/service name
- short descriptor
- ETA to pickup
- price
- capacity
- optional luggage indicator

Example products:
- Economy
- Comfort
- XL
- Reserve (if relevant)
- Courier (if relevant to selected mode)

## Card states
- default
- hover
- selected
- unavailable

## Selected ride state
When a card is selected:
- highlight border/background
- update sticky bottom request bar
- update map if different service constraints apply

## Bottom sticky confirmation bar
Contents:
- selected price
- route duration
- route distance
- selected product label
- primary CTA: Request Ride

Example:
- $58.68 | 34 min | 23.6 mi | Economy
- Request Ride

---

# 5. Searching / matching screen

## Goal
Communicate that the platform is actively finding a driver.

## Status
- MATCHING

## Layout
Map remains the main visual anchor.

## UI elements
- animated pulse or subtle search state on map
- route still visible
- bottom sheet or side card with:
  - Finding your driver
  - nearby search animation or progress copy
  - selected product
  - selected fare estimate

## Actions
- Cancel ride

## Copy examples
- Finding a nearby driver...
- Matching you with the best available driver...

## UX notes
- avoid fake progress bars unless tied to real backend stages
- keep cancel action visible but secondary

---

# 6. Driver assigned screen

## Goal
Confirm that a driver accepted the request and present trust-critical trip info.

## Status
- DRIVER_ASSIGNED

## Layout
Map + info card / bottom sheet.

## Driver card contents
- driver name
- driver rating
- vehicle make and model
- color
- license plate
- driver avatar / initials
- ETA to pickup

## Actions
- Call
- Message
- Cancel ride (if allowed by cancellation rules)

## Map state
- rider pickup marker
- driver live marker
- route from driver to pickup

## Notification event
- Your driver accepted the ride

---

# 7. Driver arriving screen

## Goal
Help the rider get ready for pickup.

## Status
- DRIVER_EN_ROUTE
n- DRIVER_ARRIVED (substate or subsequent step)

## UI elements
- prominent ETA chip
- driver distance / minutes away
- pickup point label
- optional meet-at-point guidance

## Actions
- Call
- Message
- Share trip (optional)

## Map state
- driver moving toward pickup
- live marker updates
- pickup location pinned clearly

## Arrival substate
When driver is at pickup:
- replace ETA with “Driver has arrived”
- highlight pickup instructions
- show countdown only if your product policy requires it

---

# 8. Ride in progress screen

## Goal
Support safety, visibility, and trust while the trip is ongoing.

## Status
- RIDE_STARTED

## UI elements
- trip in progress label
- ETA to destination
- remaining distance or time
- current route map
- destination label

## Actions
- Share trip
- Emergency / safety
- Message driver

## Map state
- car marker moves along route
- route progress visible
- destination remains pinned

## UX notes
- keep the interface calm, not busy
- safety actions should be visible but not alarming

---

# 9. Ride completed / receipt screen

## Goal
Close the trip clearly and make post-trip actions easy.

## Status
- RIDE_COMPLETED

## UI elements
### Completion state
- Trip complete
- destination reached confirmation

### Receipt summary
- Trip fare
- Booking / platform fee
- Tolls if any
- Discounts if any
- Total charged

### Post-trip actions
- Rate driver
- Add tip (if supported)
- View receipt
- Done

## UX notes
- do not overload the first completion view
- keep the receipt expandable if needed

---

# 10. Activity / ride history screen

## Goal
Give riders a clear record of past and upcoming rides.

## Layout
List-first page with optional filters.

## Sections
- Upcoming
- Ongoing
- Past

## Ride history card contents
- route
- date/time
- price
- status
- driver name if completed
- receipt shortcut

## Filters
- All
- Upcoming
- Completed
- Cancelled

## Actions per item
- View details
- View receipt
- Rebook route (future enhancement)

---

# 11. Profile screen

## Goal
Manage rider identity, saved places, preferences, and support access.

## Sections
- Account summary
- Saved places
- Payment methods
- Ride preferences
- Notifications
- Help & support
- Logout

## Saved places block
Show:
- Home
- Work
- Add a place

## Ride preferences examples
- preferred quiet ride
- luggage needs
- accessibility preferences

---

# 12. Responsive blueprint

## Desktop
Use split or three-column layout:
- left search
- center ride options
- right map

## Tablet
Use two-column layout:
- left search + ride options stacked or collapsible
- right map

Recommended behavior:
- search panel fixed width
- ride options appear below search panel
- map remains dominant on right

## Mobile
Use stacked flow:
- top compact map
- bottom sheet for route entry
- ride options as swipeable cards or stacked list
- matching and tracking use bottom sheets over map

### Mobile booking flow
1. enter pickup/destination in sheet
2. search
3. ride options slide up
4. request ride
5. map becomes dominant for tracking

---

# 13. Key interaction rules

## Route entry
- pickup may default to current location if allowed
- destination suggestions appear as typeahead

## Search trigger
- only enabled when both pickup and destination are valid

## Schedule logic
- schedule fields hidden until selected
- validate future date/time

## Ride selection
- one ride product selected at a time
- bottom CTA reflects selected product

## Request ride
- creates ride request and transitions UI into matching state

## Live tracking
- use polling first; websockets can come later
- refresh location and ETA at a stable cadence

---

# 14. Screen-by-screen state mapping

| Screen | Ride status | Primary user action |
|---|---|---|
| Booking | DRAFT | Search |
| Ride Options | ESTIMATE_READY / pre-request | Select ride type |
| Matching | MATCHING | Wait / cancel |
| Driver Assigned | DRIVER_ASSIGNED | Review driver |
| Driver Arriving | DRIVER_EN_ROUTE / DRIVER_ARRIVED | Prepare for pickup |
| Ride In Progress | RIDE_STARTED | Track trip |
| Ride Completed | RIDE_COMPLETED | Rate / receipt |
| Activity | mixed | Inspect ride history |
| Profile | account | Manage account |

---

# 15. Implementation notes for frontend

## Suggested React page structure
- BookRidePage
- RideOptionsPanel
- MatchingPage or MatchingSheet
- DriverAssignedPage
- RideTrackingPage
- RideCompletedPage
- ActivityPage
- ProfilePage

## Shared UI components
- Header
- RouteInput
- RideTypeDropdown
- ScheduleSelector
- LocationChipList
- RideOptionCard
- StickyRequestBar
- DriverCard
- TrackingMap
- ReceiptCard
- HistoryItemCard

## Suggested state groups
- route state
- estimate state
- selected ride product state
- ride request state
- live tracking state
- history state
- profile state

---

# 16. Final product recommendation

For RideConnect, the strongest flow is:

1. compact route entry
2. route preview on map
3. ride options open in a new center column
4. rider selects product
5. sticky request bar confirms selection
6. request transitions into matching
7. live tracking takes over once assigned

That gives the product a strong ride-hailing identity without overwhelming the user in the first screen.
