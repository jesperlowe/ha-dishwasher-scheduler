# Dishwasher Scheduler (Home Assistant custom integration)

A Home Assistant custom integration that arms, plans, and automatically starts your dishwasher on the cheapest electricity hour when the machine is ready. You can also force a "start now" plan for immediate autostart.

## Features
- Config flow: select the cheapest-hour sensor, dishwasher status entity, optional program selector, and start button entity.
- "Armed" switch to indicate user intent before automatic starts are allowed.
- Planned start sensor that calculates the next run based on the cheapest hour and allowed time window (defaults to the full day
  window of `00:00`–`00:00`).
- Choose planning mode: start immediately or use the cheapest hour in the next 24 hours.
- Last attempt/result sensors for debugging and visibility.
- Minute-level checks to start your dishwasher by pressing the configured button entity once the window matches.
- Service to pick the cheapest window directly from price data (Nordpool-style `raw_today/raw_tomorrow` arrays) using a 30-minute resolution and optional program-specific runtimes.
- Service to set the allowed time window (`dishwasher_scheduler.set_window`) directly from Lovelace or automations.
- Helper entities created automatically during installation so you can adjust the window, planning mode, and default runtime without
  building input helpers yourself.

## Installation (HACS custom repository)
1. In HACS, open **Integrations → ⋮ → Custom repositories**.
2. Add this repository URL with category **Integration**.
3. Install **Dishwasher Scheduler** and restart Home Assistant.
4. Go to **Settings → Devices & Services → Add integration** and pick **Dishwasher Scheduler**.

## Configuration
During setup, you will be asked to provide:
- **Planning mode**: either start immediately or schedule the cheapest hour in the next 24 hours.
- **Cheapest hour entity**: numeric sensor (0–23) indicating the cheapest hour to run (used when planning mode is "cheapest").
- **Dishwasher status entity**: entity whose state contains `Ready` when the dishwasher can start.
- **Program select entity (optional)**: select entity that exposes dishwasher programs so the service can pick a program runtime mapping.
- **Start button entity**: `button.*` entity that triggers the dishwasher program.
- Optional: ready substring (default `Ready`) and allowed time window (HH:MM start/end, default is a full day when both are `00:00`).

After configuration the integration exposes:
- `switch.dishwasher_scheduler_armed` – enable when you have loaded the dishwasher and allow auto-start.
- `sensor.dishwasher_scheduler_planned_start` – next planned start (local time).
- `sensor.dishwasher_scheduler_last_attempt` – last time a start was attempted.
- `sensor.dishwasher_scheduler_last_result` – result of the last attempt (`never`, `not_ready`, `started`, `start_failed`).
- `time.dishwasher_scheduler_window_start` / `time.dishwasher_scheduler_window_end` – allowed start/end time window for runs.
- `select.dishwasher_scheduler_planning_mode` – toggle between cheapest-hour planning and immediate start.
- `number.dishwasher_scheduler_default_runtime` – default runtime (minutes) used when scheduling in the window.
- Service `dishwasher_scheduler.schedule_from_prices` – calculate the cheapest start based on `raw_today/raw_tomorrow` prices and a runtime in half-hour blocks, optionally based on the current program selection; sets the planned start and can automatically arm the scheduler.
- Service `dishwasher_scheduler.set_window` – update the allowed start/end times (HH:MM) without opening the integration options.

### Example: Button to find the cheapest start from Nordpool

Create a helper button that calls the service and uses your program select entity for runtime mapping:

```yaml
alias: Plan dishwasher from prices
sequence:
  - service: dishwasher_scheduler.schedule_from_prices
    data:
      price_entity: sensor.nordpool_kwh_dk2
      duration_half_hours: 2  # fallback if no program match
      program_durations:
        Dishcare.Dishwasher.Program.Eco50: 6
        Dishcare.Dishwasher.Program.Quick45: 4
        Dishcare.Dishwasher.Program.Auto2: 8
        Dishcare.Dishwasher.Program.Intensiv70: 10
      arm: true
mode: single
```

## Lovelace examples

### Quick overview (Mushroom)
```yaml
type: vertical-stack
cards:
  - type: mushroom-entity-card
    entity: switch.dishwasher_scheduler_armed
    name: Opvask klar til start
    tap_action:
      action: toggle
  - type: mushroom-entity-card
    entity: sensor.dishwasher_scheduler_planned_start
    name: Planlagt start
  - type: mushroom-entity-card
    entity: sensor.dishwasher_scheduler_last_result
    name: Seneste resultat
  - type: mushroom-entity-card
    entity: sensor.dishwasher_scheduler_last_attempt
    name: Seneste forsøg
```

### Full setup with inputs and controls
This card exposes every dependency the integration relies on (cheapest-hour sensor, dishwasher status, program selector, start
button) plus the built-in helpers so you can change everything directly from Lovelace.

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Opvasker-planlægning
    entities:
      - entity: switch.dishwasher_scheduler_armed
        name: Klar til autostart
      - entity: sensor.dishwasher_scheduler_planned_start
        name: Planlagt start
      - entity: sensor.dishwasher_scheduler_last_attempt
        name: Seneste forsøg
      - entity: sensor.dishwasher_scheduler_last_result
        name: Seneste resultat
      - entity: select.dishwasher_scheduler_planning_mode
        name: Planlægningstilstand
  - type: entities
    title: Inputkilder
    entities:
      - entity: sensor.your_cheapest_hour
        name: Billigste time (0-23)
      - entity: sensor.dishwasher_status
        name: Opvasker-status
      - entity: select.dishwasher_program
        name: Programvalg
      - entity: button.dishwasher_start
        name: Startknap
  - type: entities
    title: Tidsvindue og handlinger
    entities:
      - entity: time.dishwasher_scheduler_window_start
        name: Vindue start
      - entity: time.dishwasher_scheduler_window_end
        name: Vindue slut
      - entity: number.dishwasher_scheduler_default_runtime
        name: Standard køretid (minutter)
      - type: button
        name: Gem vindue
        icon: mdi:clock-outline
        tap_action:
          action: call-service
          service: dishwasher_scheduler.set_window
          data:
            window_start: "{{ states('time.dishwasher_scheduler_window_start')[0:5] }}"
            window_end: "{{ states('time.dishwasher_scheduler_window_end')[0:5] }}"
      - type: button
        name: Planlæg billigste vindue
        icon: mdi:cash-clock
        tap_action:
          action: call-service
          service: dishwasher_scheduler.schedule_from_prices
          data:
            price_entity: sensor.nordpool_kwh_dk2
            duration_half_hours: 2
            program_durations:
              Dishcare.Dishwasher.Program.Eco50: 6
              Dishcare.Dishwasher.Program.Quick45: 4
              Dishcare.Dishwasher.Program.Auto2: 8
              Dishcare.Dishwasher.Program.Intensiv70: 10
            arm: true
```

The layout above follows the same pattern used by
[`ev_smart_charging`](https://github.com/jonasbkarlsson/ev_smart_charging): helper entities handle user inputs, while service
buttons trigger the actual scheduling logic.


## Notes
- The integration auto-disarms after a successful start to avoid repeated runs.
- If the cheapest hour falls outside the allowed window (default is the full day), the planned start will be `unknown` until a valid hour appears.
- Switch planning mode in the integration options: choose "start now" for immediate autostart or "cheapest" for price-optimized scheduling.
- Update the ready substring or time window anytime via the integration options.

## Release and versioning policy
Follow these steps **for every code update** so HACS users receive consistent updates:

1. Update `custom_components/dishwasher_scheduler/manifest.json` with the new semantic version (for release `v1.2.3`, set `"version": "1.2.3"`).
2. Create a matching git tag (e.g., `v1.2.3`). HACS will detect the GitHub release tied to this tag and offer the update to users.
3. Publish a GitHub Release from the tag. The release zip is what HACS downloads.
4. (Optional) For development/testing without a release, installs from a branch such as `main` are possible, but regular users should rely on tagged releases for reproducible installs.

This flow keeps the manifest version, git tag, and GitHub Release aligned, ensuring HACS shows accurate versions and update prompts.
