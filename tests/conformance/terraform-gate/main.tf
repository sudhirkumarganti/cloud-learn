# Terraform round-trip gate: real hashicorp/google provider against the
# CloudLearn simulator (custom endpoints + a fake OAuth token). `apply` then
# `plan` should report no changes — proving the sim's API responses are stable
# enough for Terraform to manage resources without drift.
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.40"
    }
  }
}

variable "endpoint" {
  type    = string
  default = "http://127.0.0.1:9000"
}

provider "google" {
  project = "gcp-dev"
  region  = "us-central1"
  zone    = "us-central1-a"

  # Route every used service at the simulator.
  storage_custom_endpoint = "${var.endpoint}/storage/v1/"
  pubsub_custom_endpoint  = "${var.endpoint}/v1/"
}

resource "google_storage_bucket" "gate" {
  name          = "tf-gate-bucket-001"
  location      = "US"
  storage_class = "STANDARD"
  force_destroy = true
}

resource "google_pubsub_topic" "gate" {
  name = "tf-gate-topic-001"
}
