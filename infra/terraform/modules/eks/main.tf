variable "cluster_name"    { type = string }
variable "cluster_version" { type = string; default = "1.29" }
variable "environment"     { type = string }
variable "vpc_id"          { type = string }
variable "subnet_ids"      { type = list(string) }

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = var.cluster_name
  cluster_version = var.cluster_version

  vpc_id                         = var.vpc_id
  subnet_ids                     = var.subnet_ids
  cluster_endpoint_public_access = true

  eks_managed_node_groups = {
    general = {
      instance_types = var.environment == "prod" ? ["t3.large"] : ["t3.medium"]
      min_size       = var.environment == "prod" ? 3 : 2
      max_size       = var.environment == "prod" ? 10 : 5
      desired_size   = var.environment == "prod" ? 3 : 2
    }
    ml = {
      # Dedicated node group for inference workloads
      instance_types = ["t3.xlarge"]
      min_size       = 1
      max_size       = 4
      desired_size   = 1
      labels         = { workload = "ml-inference" }
      taints = [{
        key    = "workload"
        value  = "ml-inference"
        effect = "NO_SCHEDULE"
      }]
    }
  }

  tags = { Project = "neuralops", Environment = var.environment }
}

output "cluster_name"     { value = module.eks.cluster_name }
output "cluster_endpoint" { value = module.eks.cluster_endpoint }
output "cluster_ca"       { value = module.eks.cluster_certificate_authority_data }
