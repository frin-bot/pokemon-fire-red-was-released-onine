from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from .detector import classify_frame, mean_rgb_for_crop
from .models import Calibration, ColorProfile, CropRect, DetectionResult
from .run_logger import RunLogger
from .serial_link import DryRunControllerLink, SerialControllerLink


def parse_crop(value: str) -> CropRect:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("crop must be formatted as x,y,width,height")
    try:
        x, y, width, height = [int(part) for part in parts]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("crop values must be integers") from exc
    if width <= 0 or height <= 0:
        raise argparse.ArgumentTypeError("crop width and height must be positive")
    return CropRect(x, y, width, height)


def save_calibration(path: Path, calibration: Calibration) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_calibration_to_dict(calibration), indent=2), encoding="utf-8")


def load_calibration(path: Path) -> Calibration:
    data = json.loads(path.read_text(encoding="utf-8"))
    shiny_profile = data.get("shiny_profile")
    return Calibration(
        starter=data["starter"],
        crop=CropRect(**data["crop"]),
        normal_profile=ColorProfile(tuple(data["normal_profile"]["mean_rgb"])),
        shiny_profile=None if shiny_profile is None else ColorProfile(tuple(shiny_profile["mean_rgb"])),
        confidence_threshold=float(data["confidence_threshold"]),
        decision_margin=float(data["decision_margin"]),
        normal_max_distance=float(data["normal_max_distance"]),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Unattended Pokemon FireRed shiny starter hunter.")
    subparsers = parser.add_subparsers(required=True)

    calibrate = subparsers.add_parser("calibrate-image", help="Create calibration JSON from screenshot images.")
    calibrate.add_argument("--starter", required=True, choices=["bulbasaur", "charmander", "squirtle"])
    calibrate.add_argument("--normal-image", required=True, type=Path)
    calibrate.add_argument("--shiny-image", type=Path)
    calibrate.add_argument("--crop", required=True, type=parse_crop)
    calibrate.add_argument("--output", required=True, type=Path)
    calibrate.add_argument("--confidence-threshold", type=float, default=0.25)
    calibrate.add_argument("--decision-margin", type=float, default=18.0)
    calibrate.add_argument("--normal-max-distance", type=float, default=35.0)
    calibrate.set_defaults(func=_cmd_calibrate_image)

    classify = subparsers.add_parser("classify-image", help="Classify one screenshot using calibration JSON.")
    classify.add_argument("--calibration", required=True, type=Path)
    classify.add_argument("--image", required=True, type=Path)
    classify.set_defaults(func=_cmd_classify_image)

    cameras = subparsers.add_parser("list-cameras", help="Print OpenCV camera indices that produce frames.")
    cameras.add_argument("--max-index", type=int, default=8)
    cameras.set_defaults(func=_cmd_list_cameras)

    run = subparsers.add_parser("run", help="Run the hunt loop with capture-card feedback.")
    run.add_argument("--calibration", required=True, type=Path)
    run.add_argument("--camera-index", type=int, default=0)
    run.add_argument("--run-dir", type=Path, default=Path("runs/current"))
    run.add_argument("--serial-port")
    run.add_argument("--baud-rate", type=int, default=57600)
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--max-attempts", type=int)
    run.add_argument("--check-delay", type=float, default=8.0)
    run.add_argument("--reset-delay", type=float, default=12.0)
    run.set_defaults(func=_cmd_run)

    return parser


def _cmd_calibrate_image(args: argparse.Namespace) -> int:
    normal_frame = _read_image_rgb(args.normal_image)
    normal_profile = ColorProfile(mean_rgb_for_crop(normal_frame, args.crop))

    shiny_profile = None
    if args.shiny_image is not None:
        shiny_frame = _read_image_rgb(args.shiny_image)
        shiny_profile = ColorProfile(mean_rgb_for_crop(shiny_frame, args.crop))

    calibration = Calibration(
        starter=args.starter,
        crop=args.crop,
        normal_profile=normal_profile,
        shiny_profile=shiny_profile,
        confidence_threshold=args.confidence_threshold,
        decision_margin=args.decision_margin,
        normal_max_distance=args.normal_max_distance,
    )
    save_calibration(args.output, calibration)
    print(f"Wrote calibration to {args.output}")
    return 0


def _cmd_classify_image(args: argparse.Namespace) -> int:
    calibration = load_calibration(args.calibration)
    frame = _read_image_rgb(args.image)
    result = classify_frame(frame, calibration)
    print(json.dumps(_detection_to_dict(result), indent=2))
    return 0


def _cmd_list_cameras(args: argparse.Namespace) -> int:
    cv2 = _import_cv2()
    found = []
    for index in range(args.max_index + 1):
        capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        ok, _frame = capture.read()
        capture.release()
        if ok:
            found.append(index)
            print(f"{index}: ok")
    if not found:
        print("No OpenCV camera sources produced a frame.", file=sys.stderr)
        return 1
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    cv2 = _import_cv2()
    calibration = load_calibration(args.calibration)
    logger = RunLogger(args.run_dir, starter=calibration.starter)
    link = DryRunControllerLink() if args.dry_run else _serial_link_from_args(args)
    capture = cv2.VideoCapture(args.camera_index, cv2.CAP_DSHOW)

    if not capture.isOpened():
        raise RuntimeError(f"could not open camera index {args.camera_index}")

    try:
        attempt_limit = args.max_attempts
        while attempt_limit is None or logger.attempt_count < attempt_limit:
            link.send_start_attempt(calibration.starter)
            time.sleep(args.check_delay)
            ok, frame_bgr = capture.read()
            if not ok:
                link.send_stop("capture_failed")
                raise RuntimeError("capture card did not produce a frame")

            frame_rgb = _bgr_to_rgb(frame_bgr)
            result = classify_frame(frame_rgb, calibration)
            screenshot_path = None

            if result.label in {"shiny", "uncertain"}:
                screenshot_path = args.run_dir / "screenshots" / f"attempt-{logger.attempt_count + 1:06d}.png"
                screenshot_path.parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(screenshot_path), frame_bgr)

            record = logger.record_attempt(result, screenshot_path)
            print(f"Attempt {record.attempt}: {result.label} confidence={result.confidence:.3f}")

            if result.label == "non_shiny":
                link.send_reset()
                time.sleep(args.reset_delay)
                continue

            link.send_stop(result.label)
            return 0
    finally:
        capture.release()
        close = getattr(link, "close", None)
        if close is not None:
            close()

    return 0


def _serial_link_from_args(args: argparse.Namespace) -> SerialControllerLink:
    if not args.serial_port:
        raise ValueError("--serial-port is required unless --dry-run is set")
    return SerialControllerLink(args.serial_port, baud_rate=args.baud_rate)


def _read_image_rgb(path: Path):
    cv2 = _import_cv2()
    image_bgr = cv2.imread(str(path))
    if image_bgr is None:
        raise RuntimeError(f"could not read image: {path}")
    return _bgr_to_rgb(image_bgr)


def _bgr_to_rgb(frame_bgr):
    cv2 = _import_cv2()
    return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)


def _import_cv2():
    try:
        import cv2
    except ImportError as exc:
        raise RuntimeError("opencv-python is required for image/capture commands") from exc
    return cv2


def _calibration_to_dict(calibration: Calibration) -> dict[str, object]:
    return {
        "starter": calibration.starter,
        "crop": asdict(calibration.crop),
        "normal_profile": asdict(calibration.normal_profile),
        "shiny_profile": None if calibration.shiny_profile is None else asdict(calibration.shiny_profile),
        "confidence_threshold": calibration.confidence_threshold,
        "decision_margin": calibration.decision_margin,
        "normal_max_distance": calibration.normal_max_distance,
    }


def _detection_to_dict(result: DetectionResult) -> dict[str, object]:
    return {
        "label": result.label,
        "confidence": result.confidence,
        "mean_rgb": result.mean_rgb,
        "normal_distance": result.normal_distance,
        "shiny_distance": result.shiny_distance,
    }


if __name__ == "__main__":
    raise SystemExit(main())
