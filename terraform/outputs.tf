output "instance_public_ip" {
  description = "Public IP of the k3s node"
  value       = aws_instance.k3s_node.public_ip
}

output "ssh_command" {
  description = "Command to SSH into the instance"
  value       = "ssh -i <your-key>.pem ubuntu@${aws_instance.k3s_node.public_ip}"
}

output "grafana_url" {
  description = "Grafana dashboard URL (after monitoring stack is deployed)"
  value       = "http://${aws_instance.k3s_node.public_ip}:3000"
}
