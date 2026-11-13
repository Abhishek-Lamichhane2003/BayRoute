import SwiftUI

@main
struct BayRouteApp: App {
    @AppStorage("bayroute.apiBaseURL") private var apiBaseURL = ""
    @StateObject private var viewModel = DashboardViewModel()

    var body: some Scene {
        WindowGroup {
            RootView(viewModel: viewModel, apiBaseURL: $apiBaseURL)
                .task { await viewModel.load(baseURL: apiBaseURL) }
                .onChange(of: apiBaseURL) { _, newValue in
                    Task { await viewModel.load(baseURL: newValue) }
                }
        }
    }
}
