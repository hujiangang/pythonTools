#!/usr/bin/env python3
"""Pick a rectangular video region with OpenCV.

Usage:
  python pick_region.py input.mp4 --time 1 --start 0 --end 4 --name right_bottom

Controls:
  left click + drag, or click two corners: select region
  r: reset selection
  enter/space: print selected region and exit
  s: save an annotated preview image
  esc/q: quit
"""

import argparse
import json
import sys
import webbrowser
from pathlib import Path
from typing import Optional, Tuple

import cv2


Point = Tuple[int, int]


class RegionPicker:
    def __init__(self, frame, display_scale: float):
        self.frame = frame
        self.display_scale = display_scale
        self.display_frame = self._resize_for_display(frame)
        self.start: Optional[Point] = None
        self.end: Optional[Point] = None
        self.dragging = False
        self.done = False

    def _resize_for_display(self, frame):
        if self.display_scale == 1:
            return frame.copy()

        height, width = frame.shape[:2]
        return cv2.resize(
            frame,
            (int(width * self.display_scale), int(height * self.display_scale)),
            interpolation=cv2.INTER_AREA,
        )

    def _to_original(self, x: int, y: int) -> Point:
        return (
            int(round(x / self.display_scale)),
            int(round(y / self.display_scale)),
        )

    def _clamp_point(self, point: Point) -> Point:
        height, width = self.frame.shape[:2]
        x = max(0, min(point[0], width - 1))
        y = max(0, min(point[1], height - 1))
        return x, y

    def mouse_callback(self, event, x, y, flags, param):
        point = self._clamp_point(self._to_original(x, y))

        if event == cv2.EVENT_LBUTTONDOWN:
            if self.start is None or self.end is not None:
                self.start = point
                self.end = None
                self.dragging = True
            else:
                self.end = point
                self.dragging = False
                self.done = True

        elif event == cv2.EVENT_MOUSEMOVE and self.dragging:
            self.end = point

        elif event == cv2.EVENT_LBUTTONUP and self.dragging:
            self.end = point
            self.dragging = False
            self.done = True

    def selected_region(self):
        if self.start is None or self.end is None:
            return None

        x1, y1 = self.start
        x2, y2 = self.end
        x = min(x1, x2)
        y = min(y1, y2)
        w = abs(x2 - x1)
        h = abs(y2 - y1)

        if w <= 0 or h <= 0:
            return None

        return x, y, w, h

    def render(self):
        image = self.display_frame.copy()
        region = self.selected_region()

        if region:
            x, y, w, h = region
            sx = int(x * self.display_scale)
            sy = int(y * self.display_scale)
            sw = int(w * self.display_scale)
            sh = int(h * self.display_scale)
            cv2.rectangle(image, (sx, sy), (sx + sw, sy + sh), (0, 255, 0), 2)
            cv2.putText(
                image,
                f"x={x}, y={y}, w={w}, h={h}",
                (sx, max(20, sy - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

        help_lines = [
            "Drag or click two corners. Enter/Space: print. R: reset. S: save. Q/Esc: quit.",
        ]
        for index, text in enumerate(help_lines):
            cv2.putText(
                image,
                text,
                (12, 28 + index * 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 0, 0),
                4,
                cv2.LINE_AA,
            )
            cv2.putText(
                image,
                text,
                (12, 28 + index * 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )

        return image


def read_frame(video_path: Path, time_sec: float):
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = frame_count / fps if fps else 0

    if time_sec < 0:
        time_sec = 0
    if duration and time_sec > duration:
        time_sec = max(0, duration - 0.01)

    cap.set(cv2.CAP_PROP_POS_MSEC, time_sec * 1000)
    ok, frame = cap.read()
    cap.release()

    if not ok or frame is None:
        raise RuntimeError(f"Cannot read frame at {time_sec:.2f}s")

    return frame, fps, frame_count, duration


def fit_scale(width: int, height: int, max_width: int, max_height: int) -> float:
    if max_width <= 0 or max_height <= 0:
        return 1.0

    scale = min(max_width / width, max_height / height, 1.0)
    return max(scale, 0.1)


def print_region(region, start_sec: float, end_sec: float, name: str):
    x, y, w, h = region
    print()
    print("Paste this into watermark_regions:")
    print(
        f'{{"start_sec": {start_sec:g}, "end_sec": {end_sec:g}, '
        f'"x": {x}, "y": {y}, "w": {w}, "h": {h}, "name": "{name}"}}'
    )


def write_browser_picker(video_path: Path, frame, args, reason: str) -> Path:
    """Create an HTML picker that works even when OpenCV HighGUI is unavailable."""
    timestamp_ms = int(max(args.time, 0) * 1000)
    image_path = video_path.with_name(f"{video_path.stem}_pick_frame_{timestamp_ms}ms.jpg")
    html_path = video_path.with_name(f"{video_path.stem}_pick_region.html")

    if not cv2.imwrite(str(image_path), frame):
        raise RuntimeError(f"Cannot write frame image: {image_path}")

    height, width = frame.shape[:2]
    config = {
        "start": args.start,
        "end": args.end,
        "name": args.name,
        "width": width,
        "height": height,
        "image": image_path.name,
    }

    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pick watermark region</title>
  <style>
    body {{
      margin: 24px;
      font-family: Consolas, "Microsoft YaHei", sans-serif;
      background: #111;
      color: #eee;
    }}
    .wrap {{
      position: relative;
      display: inline-block;
      max-width: 100%;
      border: 1px solid #555;
    }}
    img {{
      display: block;
      max-width: min(100%, 1280px);
      height: auto;
      user-select: none;
      -webkit-user-drag: none;
    }}
    canvas {{
      position: absolute;
      inset: 0;
      cursor: crosshair;
    }}
    textarea {{
      width: min(100%, 1280px);
      height: 90px;
      margin-top: 12px;
      font-family: Consolas, monospace;
      font-size: 14px;
    }}
    button {{
      margin: 10px 8px 10px 0;
      padding: 8px 12px;
      cursor: pointer;
    }}
    .muted {{ color: #aaa; }}
  </style>
</head>
<body>
  <h2>Pick watermark region</h2>
  <p class="muted">Video: {video_path.name} | Resolution: {width}x{height}</p>
  <p class="muted">OpenCV GUI fallback: {reason}</p>
  <p>Drag on the image to select the watermark area. The output uses original video coordinates.</p>
  <div class="wrap">
    <img id="frame" src="{image_path.name}" draggable="false">
    <canvas id="overlay"></canvas>
  </div>
  <div>
    <button id="copy">Copy config</button>
    <button id="reset">Reset</button>
  </div>
  <textarea id="output" readonly></textarea>
  <script>
    const config = {json.dumps(config, ensure_ascii=False)};
    const img = document.getElementById("frame");
    const canvas = document.getElementById("overlay");
    const ctx = canvas.getContext("2d");
    const output = document.getElementById("output");
    let start = null;
    let current = null;
    let dragging = false;

    function syncCanvas() {{
      const rect = img.getBoundingClientRect();
      canvas.width = Math.round(rect.width);
      canvas.height = Math.round(rect.height);
      draw();
    }}

    function pointFromEvent(event) {{
      const rect = img.getBoundingClientRect();
      const x = Math.round((event.clientX - rect.left) * img.naturalWidth / rect.width);
      const y = Math.round((event.clientY - rect.top) * img.naturalHeight / rect.height);
      return {{
        x: Math.max(0, Math.min(x, img.naturalWidth - 1)),
        y: Math.max(0, Math.min(y, img.naturalHeight - 1))
      }};
    }}

    function selectedRegion() {{
      if (!start || !current) return null;
      const x = Math.min(start.x, current.x);
      const y = Math.min(start.y, current.y);
      const w = Math.abs(current.x - start.x);
      const h = Math.abs(current.y - start.y);
      if (w <= 0 || h <= 0) return null;
      return {{x, y, w, h}};
    }}

    function configLine(region) {{
      return `{{"start_sec": ${{config.start}}, "end_sec": ${{config.end}}, "x": ${{region.x}}, "y": ${{region.y}}, "w": ${{region.w}}, "h": ${{region.h}}, "name": "${{config.name}}"}}`;
    }}

    function draw() {{
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const region = selectedRegion();
      if (!region) {{
        output.value = "";
        return;
      }}
      const sx = region.x * canvas.width / img.naturalWidth;
      const sy = region.y * canvas.height / img.naturalHeight;
      const sw = region.w * canvas.width / img.naturalWidth;
      const sh = region.h * canvas.height / img.naturalHeight;
      ctx.strokeStyle = "#00ff66";
      ctx.lineWidth = 2;
      ctx.strokeRect(sx, sy, sw, sh);
      ctx.fillStyle = "rgba(0, 0, 0, 0.65)";
      ctx.fillRect(sx, Math.max(0, sy - 28), 260, 24);
      ctx.fillStyle = "#00ff66";
      ctx.font = "16px Consolas, monospace";
      ctx.fillText(`x=${{region.x}}, y=${{region.y}}, w=${{region.w}}, h=${{region.h}}`, sx + 6, Math.max(18, sy - 10));
      output.value = configLine(region);
    }}

    canvas.addEventListener("mousedown", (event) => {{
      start = pointFromEvent(event);
      current = start;
      dragging = true;
      draw();
    }});
    canvas.addEventListener("mousemove", (event) => {{
      if (!dragging) return;
      current = pointFromEvent(event);
      draw();
    }});
    window.addEventListener("mouseup", (event) => {{
      if (!dragging) return;
      current = pointFromEvent(event);
      dragging = false;
      draw();
    }});
    document.getElementById("reset").addEventListener("click", () => {{
      start = null;
      current = null;
      draw();
    }});
    document.getElementById("copy").addEventListener("click", async () => {{
      if (!output.value) return;
      await navigator.clipboard.writeText(output.value);
    }});
    img.addEventListener("load", syncCanvas);
    window.addEventListener("resize", syncCanvas);
  </script>
</body>
</html>
"""
    html_path.write_text(html, encoding="utf-8")
    return html_path


def main():
    parser = argparse.ArgumentParser(description="Pick video watermark region coordinates.")
    parser.add_argument("input", help="Input video file")
    parser.add_argument("--time", type=float, default=1.0, help="Frame time in seconds")
    parser.add_argument("--start", type=float, default=0.0, help="Region start time")
    parser.add_argument("--end", type=float, default=4.0, help="Region end time")
    parser.add_argument("--name", default="watermark", help="Region name")
    parser.add_argument("--scale", type=float, default=0.0, help="Display scale, auto if omitted")
    parser.add_argument("--max-width", type=int, default=1280, help="Auto display max width")
    parser.add_argument("--max-height", type=int, default=800, help="Auto display max height")
    args = parser.parse_args()

    video_path = Path(args.input).resolve()
    if not video_path.exists():
        print(f"Video not found: {video_path}", file=sys.stderr)
        return 1

    frame, fps, frame_count, duration = read_frame(video_path, args.time)
    height, width = frame.shape[:2]
    display_scale = args.scale if args.scale > 0 else fit_scale(width, height, args.max_width, args.max_height)

    print(f"Video: {video_path}")
    print(f"Resolution: {width}x{height}")
    print(f"FPS: {fps:.3f}, frames: {frame_count}, duration: {duration:.2f}s")
    print(f"Showing frame at {args.time:.2f}s, display scale: {display_scale:.3f}")

    picker = RegionPicker(frame, display_scale)
    window_name = "Pick watermark region"

    try:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(window_name, picker.mouse_callback)
    except cv2.error as exc:
        html_path = write_browser_picker(video_path, frame, args, str(exc).splitlines()[-1])
        print("OpenCV GUI is not available; generated browser picker instead.")
        print(f"Open this file in a browser: {html_path}")
        try:
            webbrowser.open(html_path.as_uri())
        except Exception:
            pass
        return 0

    while True:
        cv2.imshow(window_name, picker.render())
        key = cv2.waitKey(20) & 0xFF

        if key in (13, 32):
            region = picker.selected_region()
            if region:
                print_region(region, args.start, args.end, args.name)
                break
            print("No valid region selected yet.")

        elif key in (ord("r"), ord("R")):
            picker.start = None
            picker.end = None
            picker.dragging = False
            picker.done = False

        elif key in (ord("s"), ord("S")):
            preview_path = video_path.with_name(f"{video_path.stem}_region_preview.jpg")
            cv2.imwrite(str(preview_path), picker.render())
            print(f"Saved preview: {preview_path}")

        elif key in (ord("q"), ord("Q"), 27):
            break

    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
