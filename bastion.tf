# =============================================================================
# Bastion — tiny EC2 for SSH-tunnelling to Aurora
# =============================================================================
# Solves: Nigerian ISPs rotate public IPs frequently, breaking the
# security-group rule that gates direct Aurora access. The bastion lives
# inside the VPC, so Aurora sees a stable private-network peer.
#
# Usage:
#   ssh -i ~/.ssh/rete_bastion -L 5432:<aurora_endpoint>:5432 ec2-user@<bastion_ip> -N
#   Then connect to localhost:5432 as usual.
# =============================================================================

# Look up latest Amazon Linux 2023 AMI (free-tier eligible, auto-patched).
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "state"
    values = ["available"]
  }
}

# SSH key pair — uses the key you generated.
resource "aws_key_pair" "bastion" {
  key_name   = "${var.project}-bastion-key"
  public_key = file(pathexpand("~/.ssh/rete_bastion.pub"))

  tags = { Name = "${var.project}-bastion-key" }
}

# Security group: SSH from developer IP only.
resource "aws_security_group" "bastion" {
  name        = "${var.project}-bastion-sg"
  description = "SSH access to bastion from developer IP"
  vpc_id      = aws_vpc.main.id

  # Open to all — safe because auth is SSH-key-only (no password).
  # This avoids the Nigerian ISP IP-rotation problem entirely.
  ingress {
    description = "SSH from anywhere (key-only auth)"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project}-bastion-sg" }
}

# The instance — t3.micro (free-tier eligible, ~$0 with credits).
# Stop it when not in use: aws ec2 stop-instances --instance-ids <id>
resource "aws_instance" "bastion" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.public_a.id
  key_name               = aws_key_pair.bastion.key_name
  vpc_security_group_ids = [aws_security_group.bastion.id]

  associate_public_ip_address = true

  tags = { Name = "${var.project}-bastion" }
}

# =============================================================================
# Outputs
# =============================================================================

output "bastion_public_ip" {
  description = "Bastion public IP — use in SSH tunnel command"
  value       = aws_instance.bastion.public_ip
}

output "ssh_tunnel_command" {
  description = "Run this to tunnel, then connect to localhost:5432"
  value       = "ssh -i ~/.ssh/rete_bastion -L 5432:${aws_rds_cluster.main.endpoint}:5432 ec2-user@${aws_instance.bastion.public_ip} -N"
}

resource "aws_apigatewayv2_route" "discos_ranked" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /discos/ranked"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}