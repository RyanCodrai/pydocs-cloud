# Compute Engine instances for PyDocs
# Small gateway instance for debugging and Tailscale access

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
}

variable "environment" {
  description = "Environment (prod, staging)"
  type        = string
}

# Reference the default VPC network
data "google_compute_network" "default" {
  name = "default"
}

# Get the subnet for the region
data "google_compute_subnetwork" "default" {
  name   = "default"
  region = var.region
}

# Service account for the gateway instance
resource "google_service_account" "gateway" {
  account_id   = "pydocs-gateway"
  display_name = "Service Account for PyDocs Gateway Instance"
}

# Grant Cloud SQL Client role for database access
resource "google_project_iam_member" "gateway_cloudsql" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.gateway.email}"
}

# Small e2-micro instance (cheapest option)
resource "google_compute_instance" "gateway" {
  name         = "pydocs-gateway"
  machine_type = "e2-micro"  # ~$7/month, 2 vCPUs, 1GB RAM
  zone         = "${var.region}-a"

  # Enable IP forwarding for Tailscale subnet routing
  can_ip_forward = true

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = 10  # GB
      type  = "pd-standard"  # Cheapest disk type
    }
  }

  network_interface {
    network    = data.google_compute_network.default.id
    subnetwork = data.google_compute_subnetwork.default.id

    # Give it a public IP so we can SSH in and install Tailscale
    access_config {
      # Ephemeral public IP
    }
  }

  service_account {
    email  = google_service_account.gateway.email
    scopes = ["cloud-platform"]
  }

  # Startup script to install Tailscale and configure subnet routing
  metadata_startup_script = <<-EOF
    #!/bin/bash
    set -e

    # Install basic tools
    apt-get update
    apt-get install -y curl postgresql-client jq

    # Install Tailscale
    curl -fsSL https://tailscale.com/install.sh | sh

    # Enable IP forwarding in the kernel
    echo 'net.ipv4.ip_forward = 1' | tee -a /etc/sysctl.d/99-tailscale.conf
    echo 'net.ipv6.conf.all.forwarding = 1' | tee -a /etc/sysctl.d/99-tailscale.conf
    sysctl -p /etc/sysctl.d/99-tailscale.conf

    echo "============================================"
    echo "Gateway instance ready!"
    echo "============================================"
    echo ""
    echo "To set up Tailscale subnet routing:"
    echo "1. SSH into this instance:"
    echo "   gcloud compute ssh pydocs-gateway --zone=${var.region}-a --project=${var.project_id}"
    echo ""
    echo "2. Authenticate with Tailscale and advertise all VPC routes:"
    echo "   sudo tailscale up --advertise-routes=10.0.0.0/8,10.128.0.0/9 --accept-routes"
    echo ""
    echo "   This will advertise:"
    echo "   - 10.0.0.0/8    (Private IP range for Cloud SQL and other managed services)"
    echo "   - 10.128.0.0/9  (GCP default VPC subnet range)"
    echo ""
    echo "3. Go to Tailscale admin console (https://login.tailscale.com/admin/machines)"
    echo "   and enable the advertised routes for this machine"
    echo ""
    echo "4. You'll then be able to access ALL VPC resources from your local machine:"
    echo "   - Cloud SQL: 10.0.0.5:5432"
    echo "   - Cloud Run (if using VPC): Check Cloud Run internal IP"
    echo "   - Any other VPC resources"
    echo "============================================"
  EOF

  # Allow SSH via IAP and Tailscale traffic
  tags = ["allow-ssh", "tailscale-subnet-router"]

  labels = {
    purpose     = "gateway"
    managed_by  = "terraform"
    environment = var.environment
  }
}

# Firewall rule to allow SSH from IAP (Identity-Aware Proxy)
resource "google_compute_firewall" "allow_iap_ssh" {
  name    = "allow-iap-ssh"
  network = data.google_compute_network.default.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  # IAP's IP range
  source_ranges = ["35.235.240.0/20"]
  target_tags   = ["allow-ssh"]
}

# Firewall rule to allow Tailscale UDP traffic
resource "google_compute_firewall" "allow_tailscale" {
  name    = "allow-tailscale"
  network = data.google_compute_network.default.name

  allow {
    protocol = "udp"
    ports    = ["41641"]
  }

  # Allow from anywhere (Tailscale handles authentication)
  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["tailscale-subnet-router"]
}

# Output the instance details
output "gateway_instance_name" {
  description = "Gateway instance name"
  value       = google_compute_instance.gateway.name
}

output "gateway_zone" {
  description = "Gateway instance zone"
  value       = google_compute_instance.gateway.zone
}

output "gateway_internal_ip" {
  description = "Gateway instance internal IP"
  value       = google_compute_instance.gateway.network_interface[0].network_ip
}

output "gateway_external_ip" {
  description = "Gateway instance external IP"
  value       = google_compute_instance.gateway.network_interface[0].access_config[0].nat_ip
}

output "ssh_command" {
  description = "SSH command to connect to gateway"
  value       = "gcloud compute ssh ${google_compute_instance.gateway.name} --zone=${google_compute_instance.gateway.zone} --project=${var.project_id}"
}
