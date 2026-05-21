# CloudLearn installation

## Source checkout

From the repository root:

```bash
bash ./scripts/cloud-learn dev up
```

This starts the simulator stack locally with Docker Compose and builds the
images on your machine. No Docker Hub images are required for development.
If Docker Compose is missing, the launcher will try to install it on supported
hosts before starting the stack.

On macOS, you can use the preflight wrapper to fail fast if Multipass is
missing or not yet ready:

```bash
bash ./scripts/cloud-learn-dev-up.sh
```

## Homebrew

The repository now includes a Homebrew formula scaffold under:

`packaging/homebrew/Formula/cloud-learn.rb`

The intended release flow is:

1. Build a release tarball.
2. Publish the tarball.
3. Update the formula `url` and `sha256`.
4. Add the formula to a tap.
5. Install with:

```bash
brew install cloud-learn
```

The installed `cloud-learn` command wraps the same Compose-based launcher.

## Release tooling

To build a versioned tarball and print the sha256:

```bash
bash ./scripts/build-release.sh
```

To update the Homebrew formula with that sha256:

```bash
bash ./scripts/update-homebrew-formula.sh <sha256>
```

The release version is read from `VERSION`.

## Runtime notes

- Docker is required for local development.
- Docker Compose is required, but the launcher will try to install it
  automatically on supported hosts.
- On macOS, EC2 instances require Multipass and launch is disabled until
  Multipass reports ready.
- On Linux, EC2 instances can use Multipass or LXD depending on the runtime.
- Images are downloaded on demand and cached on first use by the runtime service.
- The `cloud-learn dev ...` commands are the preferred local-development entrypoint.
