# Changelog

All notable changes to the PowerAnt API Home Assistant integration are documented here.

## [Unreleased]

## [0.2.0] - TBD

### Added
- Example Home Assistant dashboard with setup instructions.
- Unit test suite covering scheduling, electricity prices, device settings, and coordinator logic.
- Automated Python unit tests in GitHub Actions.

### Changed
- Refactored the coordinator into smaller modules for improved maintainability.
- Extracted scheduling calculations into `schedule.py`.
- Extracted electricity price handling into `prices.py`.
- Extracted device data handling into `device.py`.
- Extracted shared utility functions into `helpers.py`.
- Consolidated coordinator setting update logic.

### Fixed
- Corrected the next-change function import during refactoring.

### Compatibility
- Preserved existing integration configuration and entity behavior.
- Preserved the original 15-minute and 60-minute TIME_SLOTS scheduling logic.
- No configuration migration is required.

## [0.1.0] - 2026-10-12

### Added
- Initial release of the PowerAnt API integration.
- Support for PowerAnt Switch 63A and Switch 32A.
- Device monitoring, electricity prices, and calculated schedules.
- Device operating modes, price triggers, and tariff configuration.
- Support for 15-minute and 60-minute electricity price resolution.
- Multi-device configuration through Home Assistant.

[Unreleased]: https://github.com/MikaOOinonen/powerant-home-assistant/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/MikaOOinonen/powerant-home-assistant/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/MikaOOinonen/powerant-home-assistant/releases/tag/v0.1.0

