#!/bin/bash

set -euo pipefail
. "$(cd "$(dirname "$0")" && pwd -P)/common-macos.sh"

IMAGE=""
BRAND_IMAGE=""
BRAND_LABEL=""
THEME_NAME=""
TAGLINE=""
QUOTE=""
ACCENT="#B85235"
SECONDARY="#1B365D"
HIGHLIGHT="#1B365D"
APPLY_NOW="true"
RESET_DEMO="false"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --image) IMAGE="${2:-}"; shift 2 ;;
    --brand-image) BRAND_IMAGE="${2:-}"; shift 2 ;;
    --brand-label) BRAND_LABEL="${2:-}"; shift 2 ;;
    --name) THEME_NAME="${2:-}"; shift 2 ;;
    --tagline) TAGLINE="${2:-}"; shift 2 ;;
    --quote) QUOTE="${2:-}"; shift 2 ;;
    --accent) ACCENT="${2:-}"; shift 2 ;;
    --secondary) SECONDARY="${2:-}"; shift 2 ;;
    --highlight) HIGHLIGHT="${2:-}"; shift 2 ;;
    --no-apply) APPLY_NOW="false"; shift ;;
    --reset-demo) RESET_DEMO="true"; shift ;;
    *) fail "Unknown customize argument: $1" ;;
  esac
done

discover_codex_app
require_macos_runtime
ensure_state_root

if [ "$RESET_DEMO" = "true" ]; then
  /bin/rm -rf "$THEME_DIR"
  /bin/mkdir -p "$THEME_DIR"
  /bin/cp "$PROJECT_ROOT/assets/theme.json" "$PROJECT_ROOT/assets/default-banner.png" "$THEME_DIR/"
  /bin/chmod 700 "$THEME_DIR"
  /bin/chmod 600 "$THEME_DIR/theme.json" "$THEME_DIR/default-banner.png"
else
  if [ -z "$IMAGE" ]; then
    IMAGE="$(/usr/bin/osascript -e 'POSIX path of (choose file with prompt "选择一张主题图片（建议横向、宽度 2000px 以上）" of type {"public.image"})')" \
      || fail "Image selection was cancelled."
  fi
  [ -f "$IMAGE" ] || fail "Selected image does not exist: $IMAGE"
  SOURCE_BYTES="$(/usr/bin/stat -f '%z' "$IMAGE")"
  [ "$SOURCE_BYTES" -le 52428800 ] || fail "Selected image is larger than 50 MB. Choose a smaller file."

  if [ -z "$THEME_NAME" ]; then
    THEME_NAME="$(/usr/bin/osascript -e 'text returned of (display dialog "给这套主题起个名字" default answer "Warm Paper Studio" buttons {"取消", "继续"} default button "继续")')" \
      || fail "Theme setup was cancelled."
  fi
  if [ -z "$BRAND_LABEL" ]; then BRAND_LABEL="$THEME_NAME"; fi
  if [ -z "$TAGLINE" ]; then TAGLINE="Design quietly. Build clearly."; fi
  if [ -z "$QUOTE" ]; then QUOTE="DESIGN · APPLY · VERIFY · RESTORE"; fi

  /bin/mkdir -p "$THEME_DIR"
  /bin/chmod 700 "$THEME_DIR"
  image_name="background-$(/bin/date '+%Y%m%d-%H%M%S')-$$.jpg"
  temporary="$THEME_DIR/.${image_name}.tmp.jpg"
  prepared="$THEME_DIR/$image_name"
  brand_temporary=""
  cleanup_temporary() {
    /bin/rm -f "$temporary"
    [ -z "$brand_temporary" ] || /bin/rm -f "$brand_temporary"
  }
  trap cleanup_temporary EXIT
  /usr/bin/sips -s format jpeg -s formatOptions 84 -Z 3200 "$IMAGE" --out "$temporary" >/dev/null \
    || fail "macOS could not convert the selected image. Use PNG, JPEG, HEIC, TIFF, or WebP."
  [ -s "$temporary" ] || fail "The converted image is empty."
  PREPARED_BYTES="$(/usr/bin/stat -f '%z' "$temporary")"
  [ "$PREPARED_BYTES" -le 16777216 ] || fail "The prepared image is larger than 16 MB. Choose a simpler or smaller image."
  /bin/mv -f "$temporary" "$prepared"
  /bin/chmod 600 "$prepared"

  write_args=(custom --output-dir "$THEME_DIR" --image "$image_name"
    --name "$THEME_NAME" --brand-label "$BRAND_LABEL"
    --tagline "$TAGLINE" --quote "$QUOTE"
    --accent "$ACCENT" --secondary "$SECONDARY" --highlight "$HIGHLIGHT")
  if [ -n "$BRAND_IMAGE" ]; then
    [ -f "$BRAND_IMAGE" ] || fail "Brand image does not exist: $BRAND_IMAGE"
    brand_name="brand-$(/bin/date '+%Y%m%d-%H%M%S')-$$.png"
    brand_temporary="$THEME_DIR/.${brand_name}.tmp.png"
    /usr/bin/sips -s format png -Z 600 "$BRAND_IMAGE" --out "$brand_temporary" >/dev/null \
      || fail "macOS could not prepare the brand image."
    [ -s "$brand_temporary" ] || fail "The prepared brand image is empty."
    /bin/mv -f "$brand_temporary" "$THEME_DIR/$brand_name"
    /bin/chmod 600 "$THEME_DIR/$brand_name"
    write_args+=(--brand-image "$brand_name")
  fi

  "$NODE" "$SCRIPT_DIR/write-theme.mjs" "${write_args[@]}"
  /usr/bin/find "$THEME_DIR" -maxdepth 1 -type f -name 'background-*' ! -name "$image_name" -delete
  if [ -n "${brand_name:-}" ]; then
    /usr/bin/find "$THEME_DIR" -maxdepth 1 -type f -name 'brand-*' ! -name "$brand_name" -delete
  fi
  trap - EXIT
fi

if [ "$APPLY_NOW" = "true" ]; then
  "$SCRIPT_DIR/start-dream-skin-macos.sh" --port 9341 --prompt-restart
fi

printf 'Codex Theme Studio theme is ready.\n'
