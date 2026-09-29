# =============================================================================
# S3 — raw + structured data lake
# =============================================================================

# Raw: untouched scrape output, PDFs, rasters exactly as downloaded.
# The provenance anchor — never modified after write.
resource "aws_s3_bucket" "raw" {
  bucket = "${var.project}-raw-${data.aws_caller_identity.current.account_id}"

  tags = { Name = "${var.project}-raw" }
}

# Structured: parsed/validated outputs ready for loading into Aurora.
resource "aws_s3_bucket" "structured" {
  bucket = "${var.project}-structured-${data.aws_caller_identity.current.account_id}"

  tags = { Name = "${var.project}-structured" }
}

# Block all public access on both buckets.
resource "aws_s3_bucket_public_access_block" "raw" {
  bucket                  = aws_s3_bucket.raw.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_public_access_block" "structured" {
  bucket                  = aws_s3_bucket.structured.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Needed to reference the AWS account ID in bucket names (ensures uniqueness).
data "aws_caller_identity" "current" {}
