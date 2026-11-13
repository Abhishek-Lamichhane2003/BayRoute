import Foundation

public enum DemoPredictor {
    public static func predict(
        routeId: String,
        currentDelaySeconds: Int,
        previousStopDelaySeconds: Int,
        predictionDate: Date
    ) -> PredictionResponse {
        let hour = Calendar.current.component(.hour, from: predictionDate)
        let isPeak = (7..<10).contains(hour) || (16..<19).contains(hour)
        let peakPenalty = isPeak ? 105 : 15
        let routePenalty: Int
        switch routeId {
        case "22": routePenalty = 70
        case "66": routePenalty = 40
        default: routePenalty = 5
        }

        let predicted = Int(
            (Double(currentDelaySeconds) * 0.58
                + Double(previousStopDelaySeconds) * 0.22
                + Double(peakPenalty + routePenalty)).rounded()
        )
        let status: String
        if predicted < -60 {
            status = "early"
        } else if predicted <= 120 {
            status = "on_time"
        } else if predicted <= 300 {
            status = "minor_delay"
        } else {
            status = "major_delay"
        }

        return PredictionResponse(
            predictedDelaySeconds: predicted,
            predictedDelayMinutes: (Double(predicted) / 60 * 10).rounded() / 10,
            status: status,
            intervalLowSeconds: predicted - 128,
            intervalHighSeconds: predicted + 128,
            modelVersion: "bayroute-hgbt-v1-demo"
        )
    }
}
