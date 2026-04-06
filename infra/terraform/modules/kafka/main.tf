variable "environment"  { type = string }
variable "vpc_id"       { type = string }
variable "subnet_ids"   { type = list(string) }
variable "broker_count" { type = number; default = 3 }

resource "aws_security_group" "msk" {
  name        = "neuralops-msk-${var.environment}"
  description = "MSK Kafka security group"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 9092
    to_port     = 9092
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
    description = "Kafka plaintext from VPC"
  }

  ingress {
    from_port   = 9094
    to_port     = 9094
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
    description = "Kafka TLS from VPC"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Project = "neuralops", Environment = var.environment }
}

resource "aws_msk_cluster" "neuralops" {
  cluster_name           = "neuralops-${var.environment}"
  kafka_version          = "3.5.1"
  number_of_broker_nodes = var.broker_count

  broker_node_group_info {
    instance_type   = var.environment == "prod" ? "kafka.m5.large" : "kafka.t3.small"
    client_subnets  = slice(var.subnet_ids, 0, var.broker_count)
    security_groups = [aws_security_group.msk.id]
    storage_info {
      ebs_storage_info { volume_size = 100 }
    }
  }

  encryption_info {
    encryption_in_transit {
      client_broker = "TLS_PLAINTEXT"
      in_cluster    = true
    }
  }

  tags = { Project = "neuralops", Environment = var.environment }
}

output "bootstrap_brokers"     { value = aws_msk_cluster.neuralops.bootstrap_brokers }
output "bootstrap_brokers_tls" { value = aws_msk_cluster.neuralops.bootstrap_brokers_tls }
