import Foundation
import Vision
import AppKit
// Usage: ocr <image> ... ; prints "=== path" then recognized lines
for path in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { print("=== \(path)\n<unreadable>"); continue }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = false
    let h = VNImageRequestHandler(cgImage: cg, options: [:])
    try? h.perform([req])
    print("=== \(path)")
    for o in (req.results ?? []) { if let t = o.topCandidates(1).first { print(t.string) } }
}
