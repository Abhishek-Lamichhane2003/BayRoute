// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "BayRouteCore",
    platforms: [
        .iOS(.v17),
        .macOS(.v14),
    ],
    products: [
        .library(name: "BayRouteCore", targets: ["BayRouteCore"]),
    ],
    targets: [
        .target(
            name: "BayRouteCore",
            path: "BayRoute/Core",
            resources: [.copy("Resources/DemoData.json")]
        ),
        .testTarget(
            name: "BayRouteCoreTests",
            dependencies: ["BayRouteCore"],
            path: "BayRouteCoreTests"
        ),
    ]
)
