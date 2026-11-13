import MapKit
import SwiftUI

struct NetworkView: View {
    @ObservedObject var viewModel: DashboardViewModel
    @State private var camera: MapCameraPosition = .region(
        MKCoordinateRegion(
            center: CLLocationCoordinate2D(latitude: 37.35, longitude: -121.89),
            span: MKCoordinateSpan(latitudeDelta: 0.16, longitudeDelta: 0.16)
        )
    )

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                if let notice = viewModel.notice {
                    NoticeBanner(text: notice)
                }

                if let data = viewModel.payload {
                    summaryGrid(data)
                    vehicleMap(data.vehicles)
                    alerts(data.overview.alerts)
                    vehicleList(data.vehicles)
                } else if viewModel.isLoading {
                    ProgressView("Loading the network snapshot...")
                        .frame(maxWidth: .infinity, minHeight: 300)
                } else {
                    ContentUnavailableView(
                        "Network unavailable",
                        systemImage: "wifi.exclamationmark",
                        description: Text("Check Settings, then reload the dashboard.")
                    )
                }
            }
            .padding()
        }
        .background(Color(.systemGroupedBackground))
        .navigationTitle("BayRoute")
        .refreshable { await viewModel.load(baseURL: UserDefaults.standard.string(forKey: "bayroute.apiBaseURL") ?? "") }
    }

    private func summaryGrid(_ data: DashboardPayload) -> some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 12) {
            MetricCard(title: "Routes", value: "\(data.overview.activeRoutes)", note: "Monitored")
            MetricCard(
                title: "On time",
                value: data.overview.onTimePercent.formatted(.number.precision(.fractionLength(1))) + "%",
                note: "Within 5 min"
            )
            MetricCard(
                title: "Avg delay",
                value: delayText(Int(data.overview.averageDelaySeconds)),
                note: "Network"
            )
            MetricCard(
                title: "Model MAE",
                value: "\(Int(data.metrics.maeSeconds.rounded()))s",
                note: "Temporal holdout",
                highlighted: true
            )
        }
    }

    private func vehicleMap(_ vehicles: [LiveVehicle]) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Label("Vehicles across San Jose", systemImage: "location.fill")
                .font(.headline)
            Map(position: $camera) {
                ForEach(vehicles) { vehicle in
                    Annotation(
                        vehicle.routeName,
                        coordinate: CLLocationCoordinate2D(
                            latitude: vehicle.latitude,
                            longitude: vehicle.longitude
                        )
                    ) {
                        Text(vehicle.routeName)
                            .font(.caption.bold())
                            .foregroundStyle(.white)
                            .padding(8)
                            .background(Color(hex: vehicle.routeColor), in: Circle())
                            .shadow(radius: 3)
                            .accessibilityLabel("Route \(vehicle.routeName), \(delayText(vehicle.delaySeconds))")
                    }
                }
            }
            .mapStyle(.standard(elevation: .realistic))
            .frame(height: 320)
            .clipShape(RoundedRectangle(cornerRadius: 18))
        }
        .cardStyle()
    }

    private func alerts(_ alerts: [NetworkAlert]) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Operations pulse", systemImage: "bolt.horizontal.circle.fill")
                .font(.headline)
            ForEach(alerts) { alert in
                HStack(alignment: .top, spacing: 12) {
                    Circle()
                        .fill(alert.severity == "warning" ? Color.orange : Color.bayRouteTeal)
                        .frame(width: 10, height: 10)
                        .padding(.top, 5)
                    VStack(alignment: .leading, spacing: 3) {
                        Text(alert.title).font(.subheadline.bold())
                        Text(alert.detail).font(.caption).foregroundStyle(.secondary)
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .cardStyle()
    }

    private func vehicleList(_ vehicles: [LiveVehicle]) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            Text("Latest vehicles").font(.headline).padding(.bottom, 8)
            ForEach(vehicles.prefix(8)) { vehicle in
                HStack {
                    Text(vehicle.routeName)
                        .font(.caption.bold())
                        .foregroundStyle(.white)
                        .padding(.horizontal, 9)
                        .padding(.vertical, 5)
                        .background(Color(hex: vehicle.routeColor), in: Capsule())
                    VStack(alignment: .leading) {
                        Text(vehicle.stopName).font(.subheadline)
                        Text(vehicle.vehicleId).font(.caption2).foregroundStyle(.secondary)
                    }
                    Spacer()
                    Text(delayText(vehicle.delaySeconds)).font(.subheadline.bold())
                }
                .padding(.vertical, 9)
                if vehicle.id != vehicles.prefix(8).last?.id { Divider() }
            }
        }
        .cardStyle()
    }
}

struct MetricCard: View {
    let title: String
    let value: String
    let note: String
    var highlighted = false

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            Text(title).font(.caption).foregroundStyle(highlighted ? .white.opacity(0.8) : .secondary)
            Text(value).font(.title2.bold())
            Text(note).font(.caption2).foregroundStyle(highlighted ? .white.opacity(0.8) : .secondary)
        }
        .foregroundStyle(highlighted ? .white : .primary)
        .frame(maxWidth: .infinity, minHeight: 82, alignment: .leading)
        .padding()
        .background(highlighted ? Color.bayRouteNavy : Color(.secondarySystemGroupedBackground))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }
}

struct NoticeBanner: View {
    let text: String

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "info.circle.fill")
            Text(text).font(.footnote)
            Spacer(minLength: 0)
        }
        .foregroundStyle(Color.bayRouteNavy)
        .padding(12)
        .background(Color.bayRouteTeal.opacity(0.13), in: RoundedRectangle(cornerRadius: 14))
        .accessibilityElement(children: .combine)
    }
}

func delayText(_ seconds: Int) -> String {
    if seconds < -30 { return String(format: "%.1fm early", Double(abs(seconds)) / 60) }
    if seconds <= 30 { return "On time" }
    return String(format: "+%.1fm", Double(seconds) / 60)
}

extension View {
    func cardStyle() -> some View {
        padding()
            .background(Color(.secondarySystemGroupedBackground))
            .clipShape(RoundedRectangle(cornerRadius: 18))
    }
}

extension Color {
    static let bayRouteTeal = Color(red: 0.08, green: 0.49, blue: 0.42)
    static let bayRouteNavy = Color(red: 0.07, green: 0.18, blue: 0.27)

    init(hex: String) {
        let value = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var number: UInt64 = 0
        Scanner(string: value).scanHexInt64(&number)
        let red = Double((number >> 16) & 0xFF) / 255
        let green = Double((number >> 8) & 0xFF) / 255
        let blue = Double(number & 0xFF) / 255
        self.init(red: red, green: green, blue: blue)
    }
}
