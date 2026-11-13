import XCTest
@testable import BayRouteCore

final class BayRouteCoreTests: XCTestCase {
    func testBundledDemoSnapshotDecodes() throws {
        let payload = try APIClient().loadDemo()

        XCTAssertEqual(payload.routes.count, 4)
        XCTAssertEqual(payload.stops.count, 8)
        XCTAssertEqual(payload.vehicles.count, 4)
        XCTAssertEqual(payload.overview.dataMode, "demo")
        XCTAssertLessThan(payload.metrics.maeSeconds, payload.metrics.baselineMaeSeconds)
    }

    func testDemoPredictionIsDeterministic() throws {
        let date = try XCTUnwrap(
            ISO8601DateFormatter().date(from: "2026-11-12T17:30:00Z")
        )

        let prediction = DemoPredictor.predict(
            routeId: "22",
            currentDelaySeconds: 240,
            previousStopDelaySeconds: 195,
            predictionDate: date
        )

        XCTAssertEqual(prediction.predictedDelaySeconds, 357)
        XCTAssertEqual(prediction.status, "major_delay")
        XCTAssertEqual(prediction.modelVersion, "bayroute-hgbt-v1-demo")
    }

    func testPredictionRequestUsesSnakeCaseKeys() throws {
        let request = PredictionRequest(
            routeId: "22",
            stopId: "DIRIDON",
            predictionTime: "2026-11-12T17:30:00Z",
            currentDelaySeconds: 180,
            previousStopDelaySeconds: 135,
            headwayMinutes: 15
        )

        let object = try XCTUnwrap(
            JSONSerialization.jsonObject(with: JSONEncoder.bayRoute.encode(request))
                as? [String: Any]
        )
        XCTAssertEqual(object["route_id"] as? String, "22")
        XCTAssertEqual(object["current_delay_seconds"] as? Int, 180)
    }
}
