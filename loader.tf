# =============================================================================
# Loader Lambda — raw niggrid files in S3 → Aurora via the Data API
# =============================================================================

resource "aws_iam_role" "loader_lambda" {
  name = "${var.project}-loader-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })

  tags = { Name = "${var.project}-loader-lambda-role" }
}

resource "aws_iam_role_policy_attachment" "loader_logs" {
  role       = aws_iam_role.loader_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Reuses the Data API + secret policy already built for the API Lambda.
resource "aws_iam_role_policy_attachment" "loader_data_api" {
  role       = aws_iam_role.loader_lambda.name
  policy_arn = aws_iam_policy.api_lambda_data_api.arn
}

resource "aws_iam_policy" "loader_s3_read" {
  name = "${var.project}-loader-s3-read"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "${aws_s3_bucket.raw.arn}/niggrid/*"
      },
      {
        Effect    = "Allow"
        Action    = ["s3:ListBucket"]
        Resource  = aws_s3_bucket.raw.arn
        Condition = { StringLike = { "s3:prefix" = ["niggrid/*"] } }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "loader_s3_read" {
  role       = aws_iam_role.loader_lambda.name
  policy_arn = aws_iam_policy.loader_s3_read.arn
}

resource "aws_lambda_function" "niggrid_loader" {
  function_name = "${var.project}-niggrid-loader"
  role          = aws_iam_role.loader_lambda.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.12"
  timeout       = 300
  memory_size   = 256

  filename         = "lambda/niggrid_loader.zip"
  source_code_hash = filebase64sha256("lambda/niggrid_loader.zip")

  environment {
    variables = {
      CLUSTER_ARN          = aws_rds_cluster.main.arn
      SECRET_ARN           = aws_secretsmanager_secret.aurora_credentials.arn
      DATABASE             = aws_rds_cluster.main.database_name
      S3_BUCKET            = aws_s3_bucket.raw.id
      DATA_API_MAX_RETRIES = "6" # waits up to ~60s for Aurora to resume
    }
  }

  tags = { Name = "${var.project}-niggrid-loader" }
}

resource "aws_lambda_permission" "s3_invoke_loader" {
  statement_id  = "AllowS3InvokeLoader"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.niggrid_loader.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.raw.arn
}

resource "aws_s3_bucket_notification" "raw_niggrid" {
  bucket = aws_s3_bucket.raw.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.niggrid_loader.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "niggrid/hourly/"
    filter_suffix       = ".json"
  }

  lambda_function {
    lambda_function_arn = aws_lambda_function.niggrid_loader.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "niggrid/disco_load/"
    filter_suffix       = ".json"
  }

  depends_on = [aws_lambda_permission.s3_invoke_loader]
}

output "loader_lambda_name" {
  description = "Loader Lambda, for logs and manual backfills"
  value       = aws_lambda_function.niggrid_loader.function_name
}