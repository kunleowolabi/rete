variable "aws_region" {
  description = "AWS region"
  default     = "eu-west-1"
}

variable "project" {
  description = "Project name — used as prefix for all resources"
  default     = "rete"
}

# ──────────────────────────────────────────────
# FILL THESE IN before running terraform apply
# ──────────────────────────────────────────────

variable "my_ip" {
  description = "Your public IP for pgAdmin access (run: curl -s ifconfig.me)"
  type        = string
  # Example: "203.0.113.42"
}

variable "db_master_username" {
  description = "Aurora master username"
  type        = string
  default     = "rete_admin"
}

variable "db_master_password" {
  description = "Aurora master password (min 8 chars, no quotes)"
  type        = string
  sensitive   = true
}
