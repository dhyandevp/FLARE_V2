## Description
Briefly explain the changes introduced in this pull request and why they are necessary.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Documentation update
- [ ] UI / Styling refinement
- [ ] Hardware / Pinout change

## Quality & Verification Checklist
- [ ] Zero cloud dependencies introduced (system remains 100% operational offline)
- [ ] If UI was modified in `4_Design/dashboard.html`, `python3 4_Design/update_design.py` was executed to synchronize outputs
- [ ] Tested on physical ESP32 or verified in emulator/browser
- [ ] No hardcoded secrets, Wi-Fi credentials, or tokens committed
- [ ] Analog pins remain on ADC1 (GPIO 32–39) to prevent Wi-Fi interference
