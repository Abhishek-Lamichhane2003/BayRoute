import Foundation

public struct TransitRoute: Codable, Identifiable, Hashable, Sendable {
    public let id: String
    public let shortName: String
    public let longName: String
    public let color: String
}

public struct TransitStop: Codable, Identifiable, Hashable, Sendable {
    public let id: String
    public let code: String?
    public let name: String
    public let latitude: Double
    public let longitude: Double
}

public struct LiveVehicle: Codable, Identifiable, Hashable, Sendable {
    public let vehicleId: String
    public let routeId: String
    public let routeName: String
    public let routeColor: String
    public let stopId: String
    public let stopName: String
    public let latitude: Double
    public let longitude: Double
    public let delaySeconds: Int
    public let capturedAt: String

    public var id: String { vehicleId }
}

public struct ReliabilityPoint: Codable, Identifiable, Hashable, Sendable {
    public let routeId: String
    public let routeName: String
    public let color: String
    public let samples: Int
    public let averageDelaySeconds: Double
    public let onTimePercent: Double
    public let reliabilityScore: Double

    public var id: String { routeId }
}

public struct ModelMetrics: Codable, Hashable, Sendable {
    public let trainedRecords: Int
    public let testRecords: Int
    public let maeSeconds: Double
    public let baselineMaeSeconds: Double
    public let improvementPercent: Double
    public let withinTwoMinutesPercent: Double
    public let residualP90Seconds: Double
    public let trainedAt: String
    public let modelVersion: String
}

public struct NetworkAlert: Codable, Identifiable, Hashable, Sendable {
    public let severity: String
    public let title: String
    public let detail: String

    public var id: String { "\(severity):\(title)" }
}

public struct Overview: Codable, Hashable, Sendable {
    public let activeRoutes: Int
    public let trackedVehicles: Int
    public let averageDelaySeconds: Double
    public let onTimePercent: Double
    public let dataMode: String
    public let lastUpdated: String
    public let alerts: [NetworkAlert]
}

public struct DashboardPayload: Codable, Hashable, Sendable {
    public let overview: Overview
    public let routes: [TransitRoute]
    public let stops: [TransitStop]
    public let vehicles: [LiveVehicle]
    public let reliability: [ReliabilityPoint]
    public let metrics: ModelMetrics
}

public struct PredictionRequest: Codable, Hashable, Sendable {
    public let routeId: String
    public let stopId: String
    public let predictionTime: String
    public let currentDelaySeconds: Int
    public let previousStopDelaySeconds: Int
    public let headwayMinutes: Double

    public init(
        routeId: String,
        stopId: String,
        predictionTime: String,
        currentDelaySeconds: Int,
        previousStopDelaySeconds: Int,
        headwayMinutes: Double
    ) {
        self.routeId = routeId
        self.stopId = stopId
        self.predictionTime = predictionTime
        self.currentDelaySeconds = currentDelaySeconds
        self.previousStopDelaySeconds = previousStopDelaySeconds
        self.headwayMinutes = headwayMinutes
    }
}

public struct PredictionResponse: Codable, Hashable, Sendable {
    public let predictedDelaySeconds: Int
    public let predictedDelayMinutes: Double
    public let status: String
    public let intervalLowSeconds: Int
    public let intervalHighSeconds: Int
    public let modelVersion: String

    public init(
        predictedDelaySeconds: Int,
        predictedDelayMinutes: Double,
        status: String,
        intervalLowSeconds: Int,
        intervalHighSeconds: Int,
        modelVersion: String
    ) {
        self.predictedDelaySeconds = predictedDelaySeconds
        self.predictedDelayMinutes = predictedDelayMinutes
        self.status = status
        self.intervalLowSeconds = intervalLowSeconds
        self.intervalHighSeconds = intervalHighSeconds
        self.modelVersion = modelVersion
    }
}

extension JSONDecoder {
    static var bayRoute: JSONDecoder {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return decoder
    }
}

extension JSONEncoder {
    static var bayRoute: JSONEncoder {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        return encoder
    }
}
