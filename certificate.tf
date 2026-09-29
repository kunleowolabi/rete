# ACM certificates for CloudFront must be requested in us-east-1,
# regardless of where the rest of the infrastructure lives.
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

resource "aws_acm_certificate" "frontend" {
  provider          = aws.us_east_1
  domain_name       = "explorerete.com"
  validation_method = "DNS"

  subject_alternative_names = ["www.explorerete.com"]

  lifecycle {
    create_before_destroy = true
  }

  tags = { Name = "${var.project}-frontend-cert" }
}

output "certificate_validation_records" {
  description = "DNS records to add in Namecheap to validate the certificate"
  value = {
    for dvo in aws_acm_certificate.frontend.domain_validation_options : dvo.domain_name => {
      name  = dvo.resource_record_name
      type  = dvo.resource_record_type
      value = dvo.resource_record_value
    }
  }
}