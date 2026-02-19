# Cloud Router + NAT for outbound internet access from internal-only VMs
resource "google_compute_router" "default" {
  name    = "default-router"
  region  = var.region
  network = data.google_compute_network.default.id
}

resource "google_compute_router_nat" "default" {
  name                               = "default-nat"
  router                             = google_compute_router.default.name
  region                             = var.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}

# NFS cache VM with local SSD, synced from GCS repo cache bucket

# Dedicated service account for the NFS cache VM
resource "google_service_account" "nfs_cache" {
  account_id   = "nfs-cache"
  display_name = "Service Account for NFS Cache VM"
}

# Grant storage read access on the repo cache bucket for rclone sync
resource "google_storage_bucket_iam_member" "nfs_cache_bucket_reader" {
  bucket = var.repo_cache_bucket_name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.nfs_cache.email}"
}

# NFS cache VM with local NVMe SSD
resource "google_compute_instance" "nfs_cache" {
  name         = "nfs-cache"
  machine_type = "n2d-highcpu-2"
  zone         = "${var.region}-a"

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = 10
      type  = "pd-standard"
    }
  }

  scratch_disk {
    interface = "NVME"
  }

  network_interface {
    network    = data.google_compute_network.default.id
    subnetwork = data.google_compute_subnetwork.default.id
    # No access_config — internal only
  }

  service_account {
    email  = google_service_account.nfs_cache.email
    scopes = ["cloud-platform"]
  }

  tags = ["nfs-server"]

  labels = {
    purpose     = "nfs-cache"
    managed_by  = "terraform"
    environment = var.environment
  }

  metadata_startup_script = <<-EOF
    #!/bin/bash
    set -e

    # Install NFS server and rclone
    apt-get update
    apt-get install -y nfs-kernel-server rclone

    # --- SSD setup systemd service ---
    cat > /etc/systemd/system/setup-ssd-cache.service <<'UNIT'
    [Unit]
    Description=Format and mount local NVMe SSD for NFS cache
    DefaultDependencies=no
    Before=nfs-kernel-server.service gcs-nfs-sync.service
    After=local-fs.target

    [Service]
    Type=oneshot
    RemainAfterExit=yes
    ExecStart=/bin/bash -c '\
      if ! blkid /dev/nvme0n1 | grep -q ext4; then \
        mkfs.ext4 -F /dev/nvme0n1; \
      fi && \
      mkdir -p /mnt/nfs-cache && \
      mount -o defaults,noatime /dev/nvme0n1 /mnt/nfs-cache'

    [Install]
    WantedBy=multi-user.target
    UNIT

    systemctl daemon-reload
    systemctl enable --now setup-ssd-cache.service

    # --- NFS server configuration ---
    echo '/mnt/nfs-cache *(rw,async,no_subtree_check,no_root_squash)' > /etc/exports

    # Set 32 NFS threads
    sed -i 's/^RPCNFSDCOUNT=.*/RPCNFSDCOUNT=32/' /etc/default/nfs-kernel-server
    grep -q '^RPCNFSDCOUNT=' /etc/default/nfs-kernel-server || \
      echo 'RPCNFSDCOUNT=32' >> /etc/default/nfs-kernel-server

    # Sysctl tuning: 1MB socket buffers
    cat > /etc/sysctl.d/99-nfs.conf <<'SYSCTL'
    net.core.rmem_max=1048576
    net.core.wmem_max=1048576
    SYSCTL
    sysctl -p /etc/sysctl.d/99-nfs.conf

    # Start NFS server
    systemctl restart nfs-kernel-server
    systemctl enable nfs-kernel-server

    # --- rclone configuration ---
    mkdir -p /root/.config/rclone
    cat > /root/.config/rclone/rclone.conf <<'RCLONE'
    [gcs]
    type = google cloud storage
    env_auth = true
    location = europe-west2
    RCLONE

    # --- GCS sync systemd service ---
    cat > /etc/systemd/system/gcs-nfs-sync.service <<UNIT
    [Unit]
    Description=Continuous rclone sync from GCS repo cache to local NFS
    After=setup-ssd-cache.service nfs-kernel-server.service
    Requires=setup-ssd-cache.service

    [Service]
    Type=simple
    Restart=always
    RestartSec=2
    ExecStart=/bin/bash -c 'while true; do rclone sync gcs:${var.repo_cache_bucket_name} /mnt/nfs-cache --transfers=16 --checkers=16; sleep 2; done'

    [Install]
    WantedBy=multi-user.target
    UNIT

    systemctl daemon-reload
    systemctl enable --now gcs-nfs-sync.service

    echo "NFS cache VM setup complete"
  EOF
}

# Firewall rule to allow NFS traffic from VPC internal ranges
resource "google_compute_firewall" "allow_nfs_internal" {
  name    = "allow-nfs-internal"
  network = data.google_compute_network.default.name

  allow {
    protocol = "tcp"
    ports    = ["2049", "111", "20048"]
  }

  allow {
    protocol = "udp"
    ports    = ["2049", "111", "20048"]
  }

  source_ranges = ["10.0.0.0/8"]
  target_tags   = ["nfs-server"]
}

# Outputs
output "nfs_cache_instance_name" {
  description = "NFS cache instance name"
  value       = google_compute_instance.nfs_cache.name
}

output "nfs_cache_internal_ip" {
  description = "NFS cache instance internal IP"
  value       = google_compute_instance.nfs_cache.network_interface[0].network_ip
}

output "nfs_mount_command" {
  description = "Command to mount the NFS share from another VM"
  value       = "mount -t nfs ${google_compute_instance.nfs_cache.network_interface[0].network_ip}:/mnt/nfs-cache /mnt/nfs-cache"
}
