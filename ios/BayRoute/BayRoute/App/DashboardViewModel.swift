import Foundation

@MainActor
final class DashboardViewModel: ObservableObject {
    @Published private(set) var payload: DashboardPayload?
    @Published private(set) var prediction: PredictionResponse?
    @Published private(set) var isLoading = false
    @Published private(set) var isPredicting = false
    @Published private(set) var notice: String?

    private let client: APIClient

    init(client: APIClient = APIClient()) {
        self.client = client
    }

    func load(baseURL: String) async {
        isLoading = true
        defer { isLoading = false }
        let configuredURL = baseURL.trimmingCharacters(in: .whitespacesAndNewlines)

        if !configuredURL.isEmpty {
            do {
                payload = try await client.loadLive(baseURL: configuredURL)
                notice = nil
                return
            } catch {
                notice = "Live API unavailable. Showing the offline demo snapshot."
            }
        } else {
            notice = "Demo mode - add a BayRoute API URL in Settings for live data."
        }

        do {
            payload = try client.loadDemo()
        } catch {
            notice = error.localizedDescription
        }
    }

    func predict(
        baseURL: String,
        routeId: String,
        stopId: String,
        currentDelaySeconds: Int,
        predictionDate: Date = Date()
    ) async {
        isPredicting = true
        defer { isPredicting = false }
        let previousDelay = max(0, currentDelaySeconds - 45)
        let configuredURL = baseURL.trimmingCharacters(in: .whitespacesAndNewlines)

        if !configuredURL.isEmpty {
            let request = PredictionRequest(
                routeId: routeId,
                stopId: stopId,
                predictionTime: predictionDate.ISO8601Format(),
                currentDelaySeconds: currentDelaySeconds,
                previousStopDelaySeconds: previousDelay,
                headwayMinutes: routeId == "522" ? 12 : 15
            )
            do {
                prediction = try await client.predict(baseURL: configuredURL, request: request)
                return
            } catch {
                notice = "Live prediction failed. The on-device demo estimator was used."
            }
        }

        prediction = DemoPredictor.predict(
            routeId: routeId,
            currentDelaySeconds: currentDelaySeconds,
            previousStopDelaySeconds: previousDelay,
            predictionDate: predictionDate
        )
    }
}
