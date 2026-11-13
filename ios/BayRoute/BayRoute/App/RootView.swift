import SwiftUI

struct RootView: View {
    @ObservedObject var viewModel: DashboardViewModel
    @Binding var apiBaseURL: String

    var body: some View {
        TabView {
            NavigationStack {
                NetworkView(viewModel: viewModel)
            }
            .tabItem { Label("Network", systemImage: "map.fill") }

            NavigationStack {
                ReliabilityView(viewModel: viewModel)
            }
            .tabItem { Label("Reliability", systemImage: "chart.bar.fill") }

            NavigationStack {
                PredictionView(viewModel: viewModel, apiBaseURL: apiBaseURL)
            }
            .tabItem { Label("Predict", systemImage: "waveform.path.ecg.rectangle") }

            NavigationStack {
                SettingsView(
                    apiBaseURL: $apiBaseURL,
                    isLoading: viewModel.isLoading,
                    reload: { await viewModel.load(baseURL: apiBaseURL) }
                )
            }
            .tabItem { Label("Settings", systemImage: "gearshape.fill") }
        }
        .tint(.bayRouteTeal)
    }
}
