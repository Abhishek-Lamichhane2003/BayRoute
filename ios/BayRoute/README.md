# BayRoute iOS

BayRoute iOS is a native SwiftUI companion for the BayRoute transit-intelligence
platform. Riders can inspect vehicle positions, compare 28-day route reliability, and
estimate arrival delay from current operating conditions.

## Run the app

1. Open `BayRoute.xcodeproj` in Xcode 16 or newer.
2. Select an iPhone running iOS 17 or newer.
3. Press Run.

The app starts in offline demo mode, so no credentials or backend are required. In the
Settings tab, enter one of the following to use the real FastAPI service:

- Simulator: `http://localhost:8000`
- Physical iPhone: `http://<your-mac-lan-address>:8000`
- Other users: a hosted HTTPS URL for the BayRoute API

The client attempts all six dashboard endpoints concurrently. If the API cannot be
reached, it shows a clear notice and falls back to the bundled snapshot. Predictions use
the trained API model in live mode and a transparent deterministic estimator in demo
mode.

## Verify

```bash
swift test --package-path ios/BayRoute
xcodebuild \
  -project ios/BayRoute/BayRoute.xcodeproj \
  -target BayRoute \
  -sdk iphonesimulator \
  CODE_SIGNING_ALLOWED=NO \
  SUPPORTED_PLATFORMS=iphonesimulator \
  build
```

The Swift package tests the shared decoding and prediction core on macOS. The Xcode
build compiles the complete iPhone interface, including SwiftUI and MapKit.
