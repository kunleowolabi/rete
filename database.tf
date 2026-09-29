# =============================================================================
# Aurora Serverless v2 — PostgreSQL 16, scale-to-zero
# =============================================================================

# Subnet group: tells Aurora which subnets it can use.
resource "aws_db_subnet_group" "aurora" {
  name       = "${var.project}-aurora-subnets"
  subnet_ids = [aws_subnet.public_a.id, aws_subnet.public_b.id]

  tags = { Name = "${var.project}-aurora-subnets" }
}

# The cluster (the "logical database" — connection endpoint, storage, config).
resource "aws_rds_cluster" "main" {
  cluster_identifier     = "${var.project}-cluster"
  engine                 = "aurora-postgresql"
  engine_mode            = "provisioned"      # Serverless v2 uses "provisioned" mode
  engine_version         = "16.14"
  database_name          = "rete"
  master_username        = var.db_master_username
  master_password        = var.db_master_password
  port                   = 5432

  db_subnet_group_name   = aws_db_subnet_group.aurora.name
  vpc_security_group_ids = [aws_security_group.aurora.id]

  # Scale-to-zero: min 0 ACU, max 2 ACU (cost ceiling).
  serverlessv2_scaling_configuration {
    min_capacity = 0
    max_capacity = 2
  }

  # Dev settings — revisit for production.
  storage_encrypted       = true
  skip_final_snapshot     = true              # No snapshot on destroy (dev convenience)
  final_snapshot_identifier = "${var.project}-final"
  backup_retention_period = 1                 # 1 day (minimum; saves cost)
  deletion_protection     = false             # Allow terraform destroy

  # Enable the Data API (ADR-2: SQL over HTTPS, no VPC needed for Lambda).
  enable_http_endpoint    = true

  tags = { Name = "${var.project}-cluster" }
}

# The instance (the actual compute that runs queries).
# Serverless v2 instances scale between the cluster's min/max ACU.
resource "aws_rds_cluster_instance" "main" {
  identifier           = "${var.project}-instance"
  cluster_identifier   = aws_rds_cluster.main.id
  instance_class       = "db.serverless"      # This is the Serverless v2 instance class
  engine               = aws_rds_cluster.main.engine
  engine_version       = aws_rds_cluster.main.engine_version
  publicly_accessible  = true                 # For pgAdmin access during dev

  tags = { Name = "${var.project}-instance" }
}


resource "aws_secretsmanager_secret" "aurora_credentials" {
  name        = "${var.project}-aurora-credentials"
  description = "Aurora master credentials for Data API access"
}

resource "aws_secretsmanager_secret_version" "aurora_credentials" {
  secret_id = aws_secretsmanager_secret.aurora_credentials.id
  secret_string = jsonencode({
    username = var.db_master_username  # confirm this variable name matches yours — likely "rete_admin" hardcoded, check variables.tf
    password = var.db_master_password
    engine   = "postgres"
    host     = aws_rds_cluster.main.endpoint
    port     = 5432
    dbname   = aws_rds_cluster.main.database_name
  })
}

output "aurora_secret_arn" {
  description = "Secrets Manager ARN for Data API authentication"
  value       = aws_secretsmanager_secret.aurora_credentials.arn
}