# Dishwasher Scheduler (Home Assistant custom integration)

A Home Assistant custom integration that arms, plans, and automatically starts your dishwasher on the cheapest electricity hour when the machine is ready.

## Features
- Config flow: select the cheapest-hour sensor, dishwasher status entity, and start button entity.
- "Armed" switch to indicate user intent before automatic starts are allowed.
- Planned start sensor that calculates the next run based on the cheapest hour and allowed time window.
- Last attempt/result sensors for debugging and visibility.
- Minute-level checks to start your dishwasher by pressing the configured button entity once the window matches.

## Installation (HACS custom repository)
1. In HACS, open **Integrations → ⋮ → Custom repositories**.
2. Add this repository URL with category **Integration**.
3. Install **Dishwasher Scheduler** and restart Home Assistant.
4. Go to **Settings → Devices & Services → Add integration** and pick **Dishwasher Scheduler**.

## Configuration
During setup, you will be asked to provide:
- **Cheapest hour entity**: numeric sensor (0–23) indicating the cheapest hour to run.
- **Dishwasher status entity**: entity whose state contains `Ready` when the dishwasher can start.
- **Start button entity**: `button.*` entity that triggers the dishwasher program.
- Optional: ready substring (default `Ready`) and allowed time window (start/end hours).

After configuration the integration exposes:
- `switch.dishwasher_scheduler_armed` – enable when you have loaded the dishwasher and allow auto-start.
- `sensor.dishwasher_scheduler_planned_start` – next planned start (local time).
- `sensor.dishwasher_scheduler_last_attempt` – last time a start was attempted.
- `sensor.dishwasher_scheduler_last_result` – result of the last attempt (`never`, `not_ready`, `started`, `start_failed`).

## Lovelace example (Mushroom)
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
```

## Lovelace overview card (all inputs and outputs)
Use this card to see both the integration entities and the external inputs it relies on. Replace the example entities with your own cheapest-hour sensor, dishwasher status entity, and start button.

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
  - type: entities
    title: Inputkilder
    entities:
      - entity: sensor.your_cheapest_hour
        name: Billigste time (0-23)
      - entity: sensor.dishwasher_status
        name: Opvasker-status
      - entity: button.dishwasher_start
        name: Startknap
```

## Notes
- The integration auto-disarms after a successful start to avoid repeated runs.
- If the cheapest hour falls outside the allowed window, the planned start will be `unknown` until a valid hour appears.
- Update the ready substring or time window anytime via the integration options.
