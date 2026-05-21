class CloudLearn < Formula
  desc "Local multi-cloud simulator with a CloudSim backbone"
  homepage "https://example.com/cloud-learn/v0.1.0"
  url "https://example.com/releases/cloud-learn-0.1.0.tar.gz"
  sha256 "231bfec720575825fa0b1aee259e2fe8050d95c53579b093dc43eb84804093ab"
  license "MIT"

  def install
    libexec.install "Dockerfile"
    libexec.install "core"
    libexec.install "cloudsim-backbone"
    libexec.install "docker-compose.yml"
    libexec.install "requirements.txt"
    libexec.install "scripts"
    libexec.install "server.py"
    libexec.install "docs"
    libexec.install "static"
    libexec.install "tools"

    (bin/"cloud-learn").write <<~EOS
      #!/usr/bin/env bash
      export CLOUD_LEARN_HOME="#{libexec}"
      exec bash "#{libexec}/scripts/cloud-learn" "$@"
    EOS
    chmod 0555, bin/"cloud-learn"
  end

  def caveats
    <<~EOS
      CloudLearn runs through Docker Compose.
      You still need Docker and Docker Compose available on the host.

      EC2 runtime instances use the bundled runtime service shipped with the
      simulator stack.
    EOS
  end

  test do
    assert_match "cloud-learn", shell_output("#{bin}/cloud-learn help")
  end
end
