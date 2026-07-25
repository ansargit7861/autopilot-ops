variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "ap-south-1" # Mumbai - low latency for India-based users
}

variable "instance_type" {
  description = "EC2 instance type (t2.micro is Free Tier eligible)"
  type        = string
  default     = "t2.micro"
}

variable "key_pair_name" {
  description = "Name of an existing EC2 key pair for SSH access"
  type        = string
}

variable "allowed_ssh_cidr" {
  description = "CIDR block allowed to SSH into the instance (restrict this to your own IP in production)"
  type        = string
  default     = "0.0.0.0/0"
}

variable "project_name" {
  description = "Name used to tag all resources"
  type        = string
  default     = "autopilot-ops"
}
