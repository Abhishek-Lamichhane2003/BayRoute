import SwiftUI

struct PredictionView: View {
    @ObservedObject var viewModel: DashboardViewModel
    let apiBaseURL: String
    @State private var selectedRoute = "22"
    @State private var selectedStop = "DIRIDON"
    @State private var currentDelay = 180.0

    var body: some View {
        Form {
            Section {
                Picker("Route", selection: $selectedRoute) {
                    ForEach(viewModel.payload?.routes ?? []) { route in
                        Text("\(route.shortName) - \(route.longName)").tag(route.id)
                    }
                }
                Picker("Stop", selection: $selectedStop) {
                    ForEach(viewModel.payload?.stops ?? []) { stop in
                        Text(stop.name).tag(stop.id)
                    }
                }
            } header: {
                Text("Trip context")
            }

            Section {
                HStack {
                    Text("Current delay")
                    Spacer()
                    Text("\(Int(currentDelay / 60)) min").font(.headline.monospacedDigit())
                }
                Slider(value: $currentDelay, in: 0...900, step: 30)
                    .tint(.bayRouteTeal)
                Button {
                    Task {
                        await viewModel.predict(
                            baseURL: apiBaseURL,
                            routeId: selectedRoute,
                            stopId: selectedStop,
                            currentDelaySeconds: Int(currentDelay)
                        )
                    }
                } label: {
                    HStack {
                        if viewModel.isPredicting { ProgressView().controlSize(.small) }
                        Text(viewModel.isPredicting ? "Forecasting..." : "Run delay forecast")
                        Spacer()
                        Image(systemName: "arrow.up.right")
                    }
                }
                .disabled(viewModel.payload == nil || viewModel.isPredicting)
            } header: {
                Text("Current conditions")
            } footer: {
                Text("Live mode calls the FastAPI model. Demo mode uses a transparent on-device estimator with the same operational inputs.")
            }

            if let prediction = viewModel.prediction {
                Section("Forecast") {
                    LabeledContent("Arrival delay", value: delayText(prediction.predictedDelaySeconds))
                    LabeledContent(
                        "90% error band",
                        value: "\(Int(round(Double(prediction.intervalLowSeconds) / 60))) to \(Int(round(Double(prediction.intervalHighSeconds) / 60))) min"
                    )
                    LabeledContent("Status", value: prediction.status.replacingOccurrences(of: "_", with: " ").capitalized)
                    LabeledContent("Model", value: prediction.modelVersion)
                }
            }
        }
        .navigationTitle("Delay forecast")
        .task { synchronizeSelections(with: viewModel.payload) }
        .onChange(of: viewModel.payload) { _, payload in
            synchronizeSelections(with: payload)
        }
    }

    private func synchronizeSelections(with payload: DashboardPayload?) {
        guard let payload else { return }
        if !payload.routes.contains(where: { $0.id == selectedRoute }),
           let firstRoute = payload.routes.first {
            selectedRoute = firstRoute.id
        }
        if !payload.stops.contains(where: { $0.id == selectedStop }),
           let firstStop = payload.stops.first {
            selectedStop = firstStop.id
        }
    }
}
