#!/bin/bash

set -euo pipefail
. "$(cd "$(dirname "$0")" && pwd -P)/common-macos.sh"

IMAGE=""
THEME_NAME=""
TAGLINE=""
QUOTE=""
ACCENT="#536272"
SECONDARY="#273746"
HIGHLIGHT="#536272"
FONT_UI="ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif"
FONT_CODE="SF Mono, ui-monospace, monospace"
BODY_WEIGHT="500"
EMPHASIS_WEIGHT="600"
CODE_WEIGHT="400"
CONTROL_RADIUS="6"
CARD_RADIUS="8"
HERO_RADIUS="16"
COMPOSER_RADIUS="14"
HOME_GAP="24"
SUGGESTION_MIN_HEIGHT="112"
APPLY_NOW="true"
RESET_DEMO="false"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --image) IMAGE="${2:-}"; shift 2 ;;
    --name) THEME_NAME="${2:-}"; shift 2 ;;
    --tagline) TAGLINE="${2:-}"; shift 2 ;;
    --quote) QUOTE="${2:-}"; shift 2 ;;
    --accent) ACCENT="${2:-}"; shift 2 ;;
    --secondary) SECONDARY="${2:-}"; shift 2 ;;
    --highlight) HIGHLIGHT="${2:-}"; shift 2 ;;
    --font-ui) FONT_UI="${2:-}"; shift 2 ;;
    --font-code) FONT_CODE="${2:-}"; shift 2 ;;
    --body-weight) BODY_WEIGHT="${2:-}"; shift 2 ;;
    --emphasis-weight) EMPHASIS_WEIGHT="${2:-}"; shift 2 ;;
    --code-weight) CODE_WEIGHT="${2:-}"; shift 2 ;;
    --control-radius) CONTROL_RADIUS="${2:-}"; shift 2 ;;
    --card-radius) CARD_RADIUS="${2:-}"; shift 2 ;;
    --hero-radius) HERO_RADIUS="${2:-}"; shift 2 ;;
    --composer-radius) COMPOSER_RADIUS="${2:-}"; shift 2 ;;
    --home-gap) HOME_GAP="${2:-}"; shift 2 ;;
    --suggestion-min-height) SUGGESTION_MIN_HEIGHT="${2:-}"; shift 2 ;;
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
  BUNDLED_THEME_IMAGE="$("$NODE" -e 'const t=JSON.parse(require("fs").readFileSync(process.argv[1],"utf8"));process.stdout.write(t.image)' "$PROJECT_ROOT/assets/theme.json")"
  /bin/cp "$PROJECT_ROOT/assets/theme.json" "$PROJECT_ROOT/assets/$BUNDLED_THEME_IMAGE" "$THEME_DIR/"
  /bin/chmod 700 "$THEME_DIR"
  /bin/chmod 600 "$THEME_DIR/theme.json" "$THEME_DIR/$BUNDLED_THEME_IMAGE"
else
  if [ -z "$IMAGE" ]; then
    IMAGE="$(/usr/bin/osascript -e 'POSIX path of (choose file with prompt "选择一张主题图片（建议横向、宽度 2000px 以上）" of type {"public.image"})')" \
      || fail "Image selection was cancelled."
  fi
  [ -f "$IMAGE" ] || fail "Selected image does not exist: $IMAGE"
  SOURCE_BYTES="$(/usr/bin/stat -f '%z' "$IMAGE")"
  [ "$SOURCE_BYTES" -le 52428800 ] || fail "Selected image is larger than 50 MB. Choose a smaller file."

  if [ -z "$THEME_NAME" ]; then
    THEME_NAME="$(/usr/bin/osascript -e 'text returned of (display dialog "给这套主题起个名字" default answer "My Codex Workspace" buttons {"取消", "继续"} default button "继续")')" \
      || fail "Theme setup was cancelled."
  fi
  if [ -z "$TAGLINE" ]; then TAGLINE="A focused workspace for serious work."; fi
  if [ -z "$QUOTE" ]; then QUOTE="MAKE SOMETHING USEFUL"; fi

  /bin/mkdir -p "$THEME_DIR"
  /bin/chmod 700 "$THEME_DIR"
  image_name="background-$(/bin/date '+%Y%m%d-%H%M%S')-$$.jpg"
  temporary="$THEME_DIR/.${image_name}.tmp.jpg"
  prepared="$THEME_DIR/$image_name"
  cleanup_temporary() { /bin/rm -f "$temporary"; }
  trap cleanup_temporary EXIT
  /usr/bin/sips -s format jpeg -s formatOptions 84 -Z 3200 "$IMAGE" --out "$temporary" >/dev/null \
    || fail "macOS could not convert the selected image. Use PNG, JPEG, HEIC, TIFF, or WebP."
  [ -s "$temporary" ] || fail "The converted image is empty."
  PREPARED_BYTES="$(/usr/bin/stat -f '%z' "$temporary")"
  [ "$PREPARED_BYTES" -le 16777216 ] || fail "The prepared image is larger than 16 MB. Choose a simpler or smaller image."
  /bin/mv -f "$temporary" "$prepared"
  /bin/chmod 600 "$prepared"

  "$NODE" "$SCRIPT_DIR/write-theme.mjs" custom \
    --output-dir "$THEME_DIR" --image "$image_name" \
    --name "$THEME_NAME" --tagline "$TAGLINE" --quote "$QUOTE" \
    --accent "$ACCENT" --secondary "$SECONDARY" --highlight "$HIGHLIGHT" \
    --font-ui "$FONT_UI" --font-code "$FONT_CODE" \
    --body-weight "$BODY_WEIGHT" --emphasis-weight "$EMPHASIS_WEIGHT" --code-weight "$CODE_WEIGHT" \
    --control-radius "$CONTROL_RADIUS" --card-radius "$CARD_RADIUS" \
    --hero-radius "$HERO_RADIUS" --composer-radius "$COMPOSER_RADIUS" \
    --home-gap "$HOME_GAP" --suggestion-min-height "$SUGGESTION_MIN_HEIGHT"
  /usr/bin/find "$THEME_DIR" -maxdepth 1 -type f -name 'background-*' ! -name "$image_name" -delete
  trap - EXIT
fi

if [ "$APPLY_NOW" = "true" ]; then
  "$SCRIPT_DIR/start-dream-skin-macos.sh" --port 9341 --prompt-restart
fi

printf 'Codex Dream Skin Studio theme is ready.\n'
