import Foundation

public enum BayRouteAPIError: LocalizedError, Sendable {
    case invalidBaseURL
    case invalidResponse
    case requestFailed(Int)
    case missingDemoData

    public var errorDescription: String? {
        switch self {
        case .invalidBaseURL: "Enter a complete API URL, including https://."
        case .invalidResponse: "The server returned an unreadable response."
        case let .requestFailed(status): "The server returned HTTP \(status)."
        case .missingDemoData: "The bundled demo snapshot could not be loaded."
        }
    }
}

public struct APIClient: Sendable {
    private let session: URLSession

    public init(session: URLSession = .shared) {
        self.session = session
    }

    public func loadDemo() throws -> DashboardPayload {
        #if SWIFT_PACKAGE
        let bundle = Bundle.module
        #else
        let bundle = Bundle.main
        #endif
        guard let url = bundle.url(forResource: "DemoData", withExtension: "json") else {
            throw BayRouteAPIError.missingDemoData
        }
        return try JSONDecoder.bayRoute.decode(DashboardPayload.self, from: Data(contentsOf: url))
    }

    public func loadLive(baseURL: String) async throws -> DashboardPayload {
        let root = try normalizedURL(baseURL)
        async let overview: Overview = get(root, path: "api/overview")
        async let routes: [TransitRoute] = get(root, path: "api/routes")
        async let stops: [TransitStop] = get(root, path: "api/stops")
        async let vehicles: [LiveVehicle] = get(root, path: "api/live")
        async let reliability: [ReliabilityPoint] = get(root, path: "api/reliability")
        async let metrics: ModelMetrics = get(root, path: "api/model/metrics")
        return try await DashboardPayload(
            overview: overview,
            routes: routes,
            stops: stops,
            vehicles: vehicles,
            reliability: reliability,
            metrics: metrics
        )
    }

    public func predict(
        baseURL: String,
        request: PredictionRequest
    ) async throws -> PredictionResponse {
        let root = try normalizedURL(baseURL)
        let url = root.appending(path: "api/predict")
        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        urlRequest.httpBody = try JSONEncoder.bayRoute.encode(request)
        return try await send(urlRequest)
    }

    private func normalizedURL(_ value: String) throws -> URL {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard
            let url = URL(string: trimmed),
            let scheme = url.scheme?.lowercased(),
            ["http", "https"].contains(scheme),
            url.host != nil
        else {
            throw BayRouteAPIError.invalidBaseURL
        }
        return url
    }

    private func get<T: Decodable & Sendable>(_ root: URL, path: String) async throws -> T {
        try await send(URLRequest(url: root.appending(path: path)))
    }

    private func send<T: Decodable & Sendable>(_ request: URLRequest) async throws -> T {
        let (data, response) = try await session.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse else {
            throw BayRouteAPIError.invalidResponse
        }
        guard (200..<300).contains(httpResponse.statusCode) else {
            throw BayRouteAPIError.requestFailed(httpResponse.statusCode)
        }
        return try JSONDecoder.bayRoute.decode(T.self, from: data)
    }
}
