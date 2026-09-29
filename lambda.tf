# =============================================================================
# Lambda — niggrid hourly scraper
# =============================================================================

resource "aws_iam_role" "scraper_lambda" {
  name = "${var.project}-scraper-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })

  tags = { Name = "${var.project}-scraper-lambda-role" }
}

resource "aws_iam_role_policy_attachment" "scraper_lambda_logs" {
  role       = aws_iam_role.scraper_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_policy" "scraper_s3_write" {
  name = "${var.project}-scraper-s3-write"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:PutObject"]
      Resource = "${aws_s3_bucket.raw.arn}/niggrid/*"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "scraper_s3" {
  role       = aws_iam_role.scraper_lambda.name
  policy_arn = aws_iam_policy.scraper_s3_write.arn
}

resource "aws_lambda_function" "niggrid_scraper" {
  function_name = "${var.project}-niggrid-scraper"
  role          = aws_iam_role.scraper_lambda.arn
  handler       = "scraper_niggrid_plant_hourly.lambda_handler"
  runtime       = "python3.12"
  timeout       = 60
  memory_size   = 128

  filename         = "lambda/scraper_niggrid.zip"
  source_code_hash = filebase64sha256("lambda/scraper_niggrid.zip")

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.raw.id
    }
  }

  tags = { Name = "${var.project}-niggrid-scraper" }
}

resource "aws_cloudwatch_event_rule" "niggrid_hourly" {
  name                = "${var.project}-niggrid-hourly"
  description         = "Trigger niggrid scraper at :55 every hour"
  schedule_expression = "cron(55 * * * ? *)"

  tags = { Name = "${var.project}-niggrid-hourly" }
}

resource "aws_cloudwatch_event_target" "niggrid_scraper" {
  rule      = aws_cloudwatch_event_rule.niggrid_hourly.name
  target_id = "niggrid-scraper"
  arn       = aws_lambda_function.niggrid_scraper.arn
}

resource "aws_lambda_permission" "eventbridge_invoke" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.niggrid_scraper.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.niggrid_hourly.arn
}

output "scraper_lambda_name" {
  description = "Lambda function name for manual invocation"
  value       = aws_lambda_function.niggrid_scraper.function_name
}

# =============================================================================
# Lambda — niggrid DISCO load allocation scraper
# =============================================================================

resource "aws_lambda_function" "niggrid_disco_load_scraper" {
  function_name = "${var.project}-niggrid-disco-load-scraper"
  role          = aws_iam_role.scraper_lambda.arn
  handler       = "scraper_niggrid_disco_load.lambda_handler"
  runtime       = "python3.12"
  timeout       = 60
  memory_size   = 128

  filename         = "lambda/scraper_niggrid_disco_load.zip"
  source_code_hash = filebase64sha256("lambda/scraper_niggrid_disco_load.zip")

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.raw.id
    }
  }

  tags = { Name = "${var.project}-niggrid-disco-load-scraper" }
}

# Reuses the same EventBridge rule as the plant scraper — both fire at :55
resource "aws_cloudwatch_event_target" "niggrid_disco_load_scraper" {
  rule      = aws_cloudwatch_event_rule.niggrid_hourly.name
  target_id = "niggrid-disco-load-scraper"
  arn       = aws_lambda_function.niggrid_disco_load_scraper.arn
}

resource "aws_lambda_permission" "eventbridge_invoke_disco_load" {
  statement_id  = "AllowEventBridgeInvokeDiscoLoad"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.niggrid_disco_load_scraper.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.niggrid_hourly.arn
}

output "disco_load_scraper_lambda_name" {
  description = "Lambda function name for manual invocation"
  value       = aws_lambda_function.niggrid_disco_load_scraper.function_name
}