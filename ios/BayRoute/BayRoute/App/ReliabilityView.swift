import SwiftUI

struct ReliabilityView: View {
    @ObservedObject var viewModel: DashboardViewModel

    var body: some View {
        Group {
            if let data = viewModel.payload {
                List {
                    Section {
                        ForEach(Array(data.reliability.enumerated()), id: \.element.id) { index, route in
                            VStack(alignment: .leading, spacing: 10) {
                                HStack {
                                    Text("\(index + 1)")
                                        .font(.caption.bold())
                                        .foregroundStyle(.secondary)
                                        .frame(width: 22)
                                    Circle().fill(Color(hex: route.color)).frame(width: 12, height: 12)
                                    Text("Route \(route.routeName)").font(.headline)
                                    Spacer()
                                    Text(route.reliabilityScore.formatted(.number.precision(.fractionLength(1))) + "%")
                                        .font(.headline.monospacedDigit())
                                }
                                ProgressView(value: route.reliabilityScore, total: 100)
                                    .tint(Color(hex: route.color))
                                HStack {
                                    Text("\(route.samples.formatted()) observations")
                                    Spacer()
                                    Text("Avg \(delayText(Int(route.averageDelaySeconds)))")
                                }
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            }
                            .padding(.vertical, 6)
                        }
                    } header: {
                        Text("28-day route performance")
                    } footer: {
                        Text("Reliability is the share of arrivals within five minutes of schedule.")
                    }

                    Section("Model validation") {
                        LabeledContent("Chronological split", value: "80 / 20")
                        LabeledContent("Mean absolute error", value: "\(data.metrics.maeSeconds.formatted()) sec")
                        LabeledContent("Median baseline", value: "\(data.metrics.baselineMaeSeconds.formatted()) sec")
                        LabeledContent("Improvement", value: "\(data.metrics.improvementPercent.formatted())%")
                        LabeledContent("Within two minutes", value: "\(data.metrics.withinTwoMinutesPercent.formatted())%")
                    }
                }
            } else {
                ProgressView("Calculating reliability...")
            }
        }
        .navigationTitle("Reliability")
    }
}
