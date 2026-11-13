import SwiftUI

struct SettingsView: View {
    @Binding var apiBaseURL: String
    let isLoading: Bool
    let reload: () async -> Void

    var body: some View {
        Form {
            Section {
                TextField("https://api.example.com", text: $apiBaseURL)
                    .textInputAutocapitalization(.never)
                    .keyboardType(.URL)
                    .autocorrectionDisabled()
                Button {
                    Task { await reload() }
                } label: {
                    HStack {
                        Text(isLoading ? "Connecting..." : "Test and reload")
                        Spacer()
                        if isLoading { ProgressView().controlSize(.small) }
                    }
                }
                .disabled(isLoading)
            } header: {
                Text("BayRoute API")
            } footer: {
                Text("Leave this blank for the bundled offline demo. Use http://localhost:8000 in the Simulator, your Mac's LAN address on a phone, or a hosted HTTPS FastAPI URL for other users.")
            }

            Section("About") {
                LabeledContent("App", value: "BayRoute iOS")
                LabeledContent("Version", value: "1.0")
                LabeledContent("Minimum iOS", value: "17.0")
                Link("511 Transit data documentation", destination: URL(string: "https://511.org/open-data/transit")!)
            }

            Section {
                Label("The demo metrics are synthetic and are clearly labeled. Connect a live collector before presenting operational claims as real VTA performance.", systemImage: "checkmark.shield.fill")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
        .navigationTitle("Settings")
    }
}
