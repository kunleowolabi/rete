# =============================================================================
# API Lambda — IAM role and permissions for Data API access
# =============================================================================

resource "aws_iam_role" "api_lambda" {
  name = "${var.project}-api-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })

  tags = { Name = "${var.project}-api-lambda-role" }
}

resource "aws_iam_role_policy_attachment" "api_lambda_logs" {
  role       = aws_iam_role.api_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Data API access — scoped to this cluster only
resource "aws_iam_policy" "api_lambda_data_api" {
  name = "${var.project}-api-lambda-data-api"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "rds-data:ExecuteStatement",
          "rds-data:BatchExecuteStatement",
          "rds-data:BeginTransaction",
          "rds-data:CommitTransaction",
          "rds-data:RollbackTransaction"
        ]
        Resource = aws_rds_cluster.main.arn
      },
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = aws_secretsmanager_secret.aurora_credentials.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "api_lambda_data_api" {
  role       = aws_iam_role.api_lambda.name
  policy_arn = aws_iam_policy.api_lambda_data_api.arn
}

# =============================================================================
# API Lambda function
# =============================================================================

resource "aws_lambda_function" "api" {
  function_name = "${var.project}-api"
  role          = aws_iam_role.api_lambda.arn
  handler       = "router.handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 256

  filename         = "lambda/api.zip"
  source_code_hash = filebase64sha256("lambda/api.zip")

  environment {
    variables = {
      CLUSTER_ARN = aws_rds_cluster.main.arn
      SECRET_ARN  = aws_secretsmanager_secret.aurora_credentials.arn
      DATABASE    = aws_rds_cluster.main.database_name
    }
  }

  tags = { Name = "${var.project}-api" }
}

# =============================================================================
# API Gateway — HTTP API
# =============================================================================

resource "aws_apigatewayv2_api" "main" {
  name          = "${var.project}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET"]
    allow_headers = ["content-type"]
  }

  tags = { Name = "${var.project}-api" }
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.api.invoke_arn
  payload_format_version = "2.0"
}

# One route resource per endpoint — matches ROUTES in router.py exactly.
resource "aws_apigatewayv2_route" "summary" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /summary"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "discos" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /discos"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "disco_detail" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /discos/{disco_id}"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "disco_timeseries" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /discos/{disco_id}/timeseries"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "plants" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /plants"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "substations" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /substations"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "lines" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /lines"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "boundaries_discos" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /boundaries/discos"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "boundaries_states" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /boundaries/states"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "$default"
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = 200
    throttling_rate_limit  = 100
  }

  tags = { Name = "${var.project}-api-stage" }
}

resource "aws_lambda_permission" "apigw_invoke" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# =============================================================================
# Output
# =============================================================================

output "api_endpoint" {
  description = "Base URL for the Rete API"
  value       = aws_apigatewayv2_stage.default.invoke_url
}

resource "aws_apigatewayv2_route" "generation_current" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /generation/current"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "generation_history" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /generation/history"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "disco_live_allocation" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /discos/live-allocation"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "disco_load_history" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /discos/{disco_id}/load-history"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "infrastructure_summary" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /infrastructure/summary"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "disco_nerc_trends" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /discos/{disco_id}/nerc-trends"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "minigrids" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /minigrids"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "boundaries_country" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /boundaries/country"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "disco_allocation_history" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /discos/allocation-history"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "genco_current" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /genco/current"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_route" "genco_utilization" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /genco/utilization"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}