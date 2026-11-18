#!/usr/bin/env bash
set -euo pipefail

: "${REEL_S3_BUCKET:?Configure REEL_S3_BUCKET}"
: "${AWS_DEFAULT_REGION:?Configure REEL_S3_REGION}"
: "${AWS_ACCESS_KEY_ID:?Configure REEL_S3_ACCESS_KEY_ID}"
: "${AWS_SECRET_ACCESS_KEY:?Configure REEL_S3_SECRET_ACCESS_KEY}"
[[ "$REEL_S3_BUCKET" =~ ^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$ ]]
[[ "$AWS_DEFAULT_REGION" =~ ^[a-z0-9-]+$ ]]

case "$1" in
  upload)
    key="previsaopr/$(python -c 'import uuid; print(uuid.uuid4().hex)').mp4"
    url="https://${REEL_S3_BUCKET}.s3.${AWS_DEFAULT_REGION}.amazonaws.com/$key"
    aws s3 cp output/REEL.mp4 "s3://$REEL_S3_BUCKET/$key" \
      --no-progress --only-show-errors --content-type video/mp4 --content-disposition inline
    mime=$(curl --head --fail --silent --show-error --retry 3 --max-time 30 \
      --output /dev/null --write-out '%{content_type}' "$url")
    test "$mime" = "video/mp4"
    curl --fail --silent --show-error --max-time 30 --range 0-31 --output /dev/null "$url"
    printf 'url=%s\nkey=%s\n' "$url" "$key" >> "$GITHUB_OUTPUT"
    ;;
  confirm)
    [[ "$REEL_S3_KEY" =~ ^previsaopr/[0-9a-f]{32}\.mp4$ ]]
    aws s3api put-object-tagging --bucket "$REEL_S3_BUCKET" --key "$REEL_S3_KEY" \
      --tagging 'TagSet=[{Key=publication,Value=confirmed}]'
    ;;
  *) exit 2 ;;
esac
