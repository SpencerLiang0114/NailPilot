import os
import shutil
import subprocess
import sys
from pathlib import Path

import requests


BASE_DIR = Path(__file__).resolve().parent


class PipelineConfigurationError(RuntimeError):
    pass


def _prepare_model_link(env_name: str, target: Path, should_be_dir: bool) -> None:
    source_value = os.getenv(env_name, "").strip()
    if not source_value:
        raise PipelineConfigurationError(f"{env_name} is not configured.")

    source = Path(source_value).expanduser().resolve()
    if should_be_dir and not source.is_dir():
        raise PipelineConfigurationError(f"{env_name} must point to an existing directory: {source}")
    if not should_be_dir and not source.is_file():
        raise PipelineConfigurationError(f"{env_name} must point to an existing file: {source}")

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        if target.resolve() == source:
            return
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()

    try:
        target.symlink_to(source, target_is_directory=should_be_dir)
    except OSError:
        if should_be_dir:
            shutil.copytree(source, target)
        else:
            shutil.copyfile(source, target)


def _prepare_models() -> None:
    _prepare_model_link(
        "NAIL_TRYON_SAM3_WEIGHTS",
        BASE_DIR / "sys" / "sam3_weights" / "sam3.pt",
        should_be_dir=False,
    )
    _prepare_model_link(
        "NAIL_TRYON_SD_INPAINTING_DIR",
        BASE_DIR / "sys" / "sd_models" / "AI-ModelScope" / "stable-diffusion-inpainting",
        should_be_dir=True,
    )


def _reset_pipeline_workspace() -> None:
    for name in [
        "style",
        "hands",
        "s1_style_output",
        "s2_style_natural",
        "s3_nail_Direction",
        "s5_hands_output",
        "s6_hands_natural",
        "s7_hands_finger_direction",
        "s9_rotNail2MatchFingerDirection_v2",
        "s10_getbottomPint",
        "s11_getFingerNail",
        "s12_getFingerNailBottonTip",
        "s13_tryOn",
    ]:
        path = BASE_DIR / name
        if path.exists():
            shutil.rmtree(path)


def _copy_or_download_image(source_path_or_url: str, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if source_path_or_url.startswith(("http://", "https://")):
        response = requests.get(source_path_or_url, timeout=20)
        response.raise_for_status()
        target_path.write_bytes(response.content)
        return

    shutil.copyfile(source_path_or_url, target_path)


def run_nail_tryon_pipeline(selected_nail_path: str, uploaded_hand_path: str) -> str | None:
    """
    selected_nail_path can be a local path or remote image URL.
    uploaded_hand_path is the temporary local hand image uploaded by the user.
    """
    print("\n==================== AI nail try-on pipeline started ====================")
    _prepare_models()
    _reset_pipeline_workspace()

    _copy_or_download_image(selected_nail_path, BASE_DIR / "style" / "a2.png")
    shutil.copyfile(uploaded_hand_path, BASE_DIR / "hands" / "a13.png")

    scripts = [
        "s1_extractNailBySam3.py",
        "s2_eraseNailArt.py",
        "s3_detectNailDirections.py",
        "s4_visualizeDirections.py",
        "s5_extractNailBySam3forHands.py",
        "s6_eraseNailArt.py",
        "s7_finger_direction_detectorV3.py",
        "s8_visualizeDirections.py",
        "s9_rotNail2MatchFingerDirection_v2.py",
        "s10_getbottomPint.py",
        "s11_extractNailV2.py",
        "s12_getFingerNailBottonTipV2.py",
        "s13_tryOnV2.py",
    ]

    for idx, script in enumerate(scripts, 1):
        script_path = BASE_DIR / script
        if not script_path.exists():
            raise FileNotFoundError(f"Pipeline script not found: {script}")

        print(f"[{idx}/13] Running {script} ...")
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(BASE_DIR),
            capture_output=True,
            text=True,
        )
        if result.stdout:
            print(result.stdout)
        if result.returncode != 0:
            print(result.stderr)
            raise RuntimeError(f"{script} failed with exit code {result.returncode}.")

    final_result_path = BASE_DIR / "s13_tryOn" / "a13_natural" / "a13_natural_tryon.png"
    if final_result_path.exists():
        print(f"Pipeline completed: {final_result_path}")
        return str(final_result_path)

    print("Pipeline completed without expected output image.")
    return None
