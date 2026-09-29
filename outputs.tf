# =============================================================================
# Outputs — printed after terraform apply
# =============================================================================

# What you need for pgAdmin:
output "aurora_endpoint" {
  description = "Aurora cluster endpoint — use as Host in pgAdmin"
  value       = aws_rds_cluster.main.endpoint
}

output "aurora_port" {
  description = "Aurora port"
  value       = aws_rds_cluster.main.port
}

output "aurora_database" {
  description = "Database name"
  value       = aws_rds_cluster.main.database_name
}

output "aurora_username" {
  description = "Master username"
  value       = aws_rds_cluster.main.master_username
}

# S3 bucket names:
output "s3_raw_bucket" {
  description = "S3 bucket for raw data"
  value       = aws_s3_bucket.raw.id
}

output "s3_structured_bucket" {
  description = "S3 bucket for structured data"
  value       = aws_s3_bucket.structured.id
}
