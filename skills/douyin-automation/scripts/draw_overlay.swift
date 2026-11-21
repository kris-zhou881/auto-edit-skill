import AppKit
import Foundation

struct Spec: Decodable {
    let mode: String
    let headline: String
    let lines: [String]
    let accent: String
    let output: String
    let style: String?
    let keyword: String?
    let backdrop: String?
}
let input = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[1]))
let specs = try JSONDecoder().decode([Spec].self, from: input)
let ink = NSColor(srgbRed: 0.036, green: 0.055, blue: 0.10, alpha: 1)
let mint = NSColor(srgbRed: 0.38, green: 1, blue: 0.76, alpha: 1)
let amber = NSColor(srgbRed: 1, green: 0.77, blue: 0.32, alpha: 1)
let slate = NSColor(srgbRed: 0.65, green: 0.73, blue: 0.84, alpha: 1)

func rect(_ x: CGFloat, _ top: CGFloat, _ w: CGFloat, _ h: CGFloat) -> CGRect {
    CGRect(x: x, y: 1920 - top - h, width: w, height: h)
}
func fill(_ box: CGRect, _ color: NSColor, _ radius: CGFloat = 0) {
    color.setFill()
    NSBezierPath(roundedRect: box, xRadius: radius, yRadius: radius).fill()
}
func label(_ value: String, x: CGFloat, top: CGFloat, width: CGFloat,
           size: CGFloat, color: NSColor, weight: NSFont.Weight = .semibold) throws {
    let attributes: [NSAttributedString.Key: Any] = [
        .font: NSFont.systemFont(ofSize: size, weight: weight), .foregroundColor: color
    ]
    let text = NSAttributedString(string: value, attributes: attributes)
    guard text.size().width <= width else {
        throw NSError(domain: "Text exceeds layout width: \(value)", code: 2)
    }
    text.draw(at: NSPoint(x: x, y: 1920 - top - text.size().height))
}

for spec in specs {
    let bitmap = NSBitmapImageRep(bitmapDataPlanes: nil, pixelsWide: 1080, pixelsHigh: 1920,
        bitsPerSample: 8, samplesPerPixel: 4, hasAlpha: true, isPlanar: false, colorSpaceName: .deviceRGB,
        bytesPerRow: 0, bitsPerPixel: 0)!
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: bitmap)
    NSGraphicsContext.current?.cgContext.clear(CGRect(x: 0, y: 0, width: 1080, height: 1920))
    let keyColor = spec.accent == "warn" ? amber : mint
    if spec.mode == "cursor" {
        let path = NSBezierPath()
        for (i, point) in [(3,3),(5,34),(12,26),(20,40),(27,37),(20,24),(32,24)].enumerated() {
            let p = NSPoint(x: point.0, y: 1920 - point.1)
            if i == 0 { path.move(to: p) } else { path.line(to: p) }
        }
        path.close(); ink.setFill(); path.fill(); NSColor.white.setStroke(); path.lineWidth = 2; path.stroke()
    } else if spec.mode == "caption", spec.style == "capsule" {
        let string = spec.lines.joined(separator: " ")
        let options: [NSAttributedString.Key: Any] = [
            .font: NSFont.systemFont(ofSize: 43, weight: .heavy), .foregroundColor: NSColor.white
        ]
        let text = NSMutableAttributedString(string: string, attributes: options)
        if let keyword = spec.keyword, !keyword.isEmpty {
            let range = (string as NSString).range(of: keyword)
            if range.location != NSNotFound {
                text.addAttribute(.foregroundColor, value: NSColor(srgbRed: 0.78, green: 0.80, blue: 1, alpha: 1), range: range)
            }
        }
        let size = text.size()
        guard size.width <= 746 else { throw NSError(domain: "字幕超出安全宽度", code: 2) }
        fill(rect(478-(size.width+52)/2, 1390, size.width+52, 78), ink, 38)
        text.draw(at: NSPoint(x: 478-size.width/2, y: 1920-1390-(78+size.height)/2))
    } else if spec.mode == "caption" {
        fill(rect(76, 1380, 804, 230), ink, 24)
        fill(rect(76, 1406, 7, 178), keyColor, 3)
        try label(spec.headline, x: 112, top: 1402, width: 716, size: 30, color: keyColor)
        for (i, line) in spec.lines.enumerated() {
            try label(line, x: 112, top: 1460 + CGFloat(i) * 62, width: 724, size: 47, color: .white)
        }
    } else if spec.backdrop == "editorial_light" {
        let white = NSColor(srgbRed: 0.997, green: 0.997, blue: 1, alpha: 1)
        let pale = NSColor(srgbRed: 0.86, green: 0.89, blue: 0.96, alpha: 1)
        let blue = NSColor(srgbRed: 0.27, green: 0.32, blue: 0.59, alpha: 1)
        NSGradient(starting: white, ending: pale)?.draw(in: rect(0,0,1080,1920), angle: -53)
        for (cx, cy) in [(1000,110),(55,1210),(1010,1510)] {
            for dx in stride(from:-70, through:70, by:12) {
                for dy in stride(from:-70, through:70, by:12) where dx*dx+dy*dy < 4900 {
                    fill(rect(CGFloat(cx+dx),CGFloat(cy+dy), 3, 3), blue.withAlphaComponent(0.19), 1.5)
                }
            }
        }
        for offset in [0,12] {
            let guide = NSBezierPath()
            guide.move(to: NSPoint(x: 1045+offset, y: 1830))
            guide.curve(to: NSPoint(x: 899+offset, y: 1450), controlPoint1: NSPoint(x: 875+offset,y:1660), controlPoint2: NSPoint(x: 1042+offset,y:1570))
            blue.withAlphaComponent(0.16).setStroke(); guide.lineWidth = 1.5; guide.stroke()
        }
        NSGraphicsContext.saveGraphicsState()
        let shadow = NSShadow(); shadow.shadowOffset = NSSize(width:0,height:-10); shadow.shadowBlurRadius = 27
        shadow.shadowColor = blue.withAlphaComponent(0.25); shadow.set()
        fill(rect(63,311,830,1018),white,22)
        NSGraphicsContext.restoreGraphicsState()
        NSGraphicsContext.current?.cgContext.clear(rect(76,325,804,990))
        try label(spec.lines.first ?? "", x: 76, top: 122, width: 800, size: 32, color: blue)
        fill(rect(76,168,804,2), blue.withAlphaComponent(0.34))
        try label(spec.headline, x: 76, top: 185, width: 800, size: 63, color: ink, weight: .bold)
    } else {
        fill(rect(76, 140, 804, 152), ink, 22)
        fill(rect(76, 148, 7, 136), keyColor, 3)
        try label(spec.lines.first ?? "", x: 106, top: 154, width: 744, size: 31, color: keyColor)
        try label(spec.headline, x: 106, top: 200, width: 744, size: 63, color: .white, weight: .bold)
    }
    NSGraphicsContext.restoreGraphicsState()
    guard let png = bitmap.representation(using: .png, properties: [:]) else {
        throw NSError(domain: "Overlay export", code: 1)
    }
    try png.write(to: URL(fileURLWithPath: spec.output))
}
