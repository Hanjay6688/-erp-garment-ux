import UIKit
import WebKit

@main
final class SimulatorHost: UIResponder, UIApplicationDelegate {
    var window: UIWindow?
    func application(_ application: UIApplication, didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        let identifier = ProcessInfo.processInfo.arguments.first { $0.hasPrefix("http://127.0.0.1:") }
        guard let target=identifier, let url=URL(string:target), url.host=="127.0.0.1" else { return false }
        let configuration=WKWebViewConfiguration()
        let web=WKWebView(frame:.zero,configuration:configuration)
        let view=UIViewController()
        view.view=web
        let screen=UIWindow(frame:UIScreen.main.bounds)
        screen.rootViewController=view
        screen.makeKeyAndVisible()
        window=screen
        web.load(URLRequest(url:url))
        return true
    }
}
