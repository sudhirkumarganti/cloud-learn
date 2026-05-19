# Homebrew packaging

This directory contains the Homebrew formula scaffold for CloudLearn.

## Intended flow

1. Publish a release tarball for CloudLearn.
2. Run `bash ./scripts/build-release.sh`.
3. Run `bash ./scripts/update-homebrew-formula.sh <sha256>`.
4. Update `Formula/cloud-learn.rb` with the release `url` and `sha256`.
5. Add the formula to a Homebrew tap.
6. Install with:

```bash
brew install cloud-learn
```

## What the formula installs

- `cloud-learn` launcher in `bin`
- the Compose bundle
- the CloudSim sidecar source
- the simulator backend
- docs and scripts

## Runtime expectations

The installed launcher expects:

- Docker
- Docker Compose

For local testing, the compose stack builds the images on the local machine.
EC2 launch requires a working LXD runtime and will remain disabled until LXD is available.

## Local development

For source checkout usage, run:

```bash
bash ./scripts/cloud-learn dev up
```

That uses the same launcher logic as the package install path.
