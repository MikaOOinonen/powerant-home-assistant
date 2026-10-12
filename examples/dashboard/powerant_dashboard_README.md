# PowerAnt example dashboard

This example is based on a working PowerAnt Home Assistant Lovelace dashboard. It displays today's and tomorrow's calculated schedules, device settings, and hourly tariffs and transmission fees.

## Requirements

Install these frontend custom cards using HACS before importing the dashboard:

- **ApexCharts Card** (`custom:apexcharts-card`) — schedule/price charts.
- **card-mod** — dashboard styling and layout.

The **PowerAnt API** integration must also be installed and configured for your device.

## Configure the example

1. Make a copy of `powerant_dashboard.yaml`.
2. Use your text editor's **Replace All** to replace these placeholders everywhere in the copy:

   | Placeholder | Replace with | Example |
   | --- | --- | --- |
   | `###NAME###` | Friendly device name for the heading | `Water heater` |
   | `###DEVICE###` | Common entity ID stem, **without** domain or final suffix | `waterheater` |

3. In **Settings → Devices & services → Helpers**, create a **Toggle** helper named **Show tomorrow**. Confirm its entity ID is `input_boolean.show_tomorrow`, or replace this ID in the YAML with the actual helper ID. Set the helper to **off** before testing.
4. Confirm entity IDs in **Developer Tools → States**. For example, `sensor.###DEVICE###_calculated_schedule` should become your actual calculated schedule sensor ID. Entity ID stems are installation-specific and may be different from the device's displayed name.
5. Paste the resulting YAML into a dashboard **Raw configuration editor** (it is a full `views:` configuration, not a single card). Alternatively, adapt the view to your existing dashboard.
6. Save and verify that the charts and settings display correctly.

## Show tomorrow toggle and optional automatic visibility

The dashboard includes a **Show tomorrow** toggle above today's chart. The initial state is controlled by the Home Assistant Toggle helper; set it to **off** when configuring the dashboard. When enabled, it displays tomorrow's chart, using the `tomorrow_schedule` attribute of the calculated schedule sensor. The toggle controls visibility only; it does not change the PowerAnt device settings. Exit dashboard edit mode to test conditional visibility. When tomorrow's data is unavailable, the chart has no schedule data to plot.

**Optional: automatically show tomorrow's chart when data is ready.** Instead of the toggle condition, create a Home Assistant **Template sensor** helper that counts tomorrow's schedule entries. Use this template, replacing the example sensor ID with your own:

```jinja2
{{ state_attr('sensor.waterheater_calculated_schedule', 'tomorrow_schedule') | default([], true) | count }}
```

For 15-minute prices, a complete day normally has **96** entries (on daylight-saving transition days, the count can differ). Then replace the tomorrow chart's conditional `conditions` block:

```yaml
conditions:
  - condition: numeric_state
    entity: sensor.powerant_tomorrow_periods
    above: 19
```

Replace `sensor.powerant_tomorrow_periods` with your template sensor's actual entity ID. You may also remove the **Show tomorrow** entities card. The `above: 19` threshold is an example that checks for at least 20 periods, not a guarantee that all tomorrow's prices are available. To require a complete normal 15-minute day, use `above: 95` instead.

## Safety and behavior

The dashboard contains editable PowerAnt settings and controls. Changing them can affect your real connected equipment. Use care when testing, especially if you have multiple Home Assistant installations connected to the same PowerAnt device.

This example keeps the original styling and logic; it is not a plug-and-play auto-configured dashboard. No API keys or credentials belong in the dashboard YAML.
