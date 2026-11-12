# Contributing to FLARE V2

Thank you for your interest in contributing to FLARE V2! We welcome contributions from IoT developers, firmware engineers, mobile app developers, UI/UX designers, and field emergency responders.

## Code of Conduct

Please maintain a supportive, respectful, and collaborative environment. Our goal is to build accessible, life-saving open-source disaster technology.

## How to Contribute

### 1. Reporting Bugs
- Search existing issues to ensure the bug has not already been reported.
- Open a new issue using the **Bug Report** template.
- Include:
  - ESP32 hardware revision and Arduino core version.
  - Android device model and OS version (if app-related).
  - Serial monitor output logs at 115200 baud.
  - Steps to reproduce the issue.

### 2. Proposing Features & Improvements
- Open an issue using the **Feature Request** template.
- Explain the real-world operational problem and proposed solution.
- For sensor additions (e.g., barometric pressure, turbidity), include voltage and pin compatibility with ESP32 ADC1.

### 3. Submitting Pull Requests
1. Fork the repository and create your branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes:
   - For UI changes: edit `4_Design/dashboard.html` and run `python3 4_Design/update_design.py` to synchronize all target outputs.
   - For ESP32 changes: test using Arduino IDE or PlatformIO on actual ESP32 hardware.
   - For Android changes: verify `./gradlew test` passes.
3. Follow conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`).
4. Push to your fork and submit a Pull Request against `main`.

## Development Guidelines

- **Zero Cloud Invariant:** Do not introduce cloud, telemetry, or external API dependencies into the core firmware. FLARE V2 must always remain 100% operational on local Wi-Fi / offline hotspots.
- **Single Source of Truth:** Never edit `1_ESP32_Code/.../dashboard_html.h` or `2_Website/FLARE_Dashboard.html` directly. Always edit `4_Design/dashboard.html` and compile with `update_design.py`.
- **ADC Safety:** Ensure analog sensor pins remain on ADC1 (GPIO 32–39) so Wi-Fi does not interfere with readings.

## License

By contributing to FLARE V2, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).
