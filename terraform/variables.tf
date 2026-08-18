variable "project_id" {
  type        = string
  description = "Google Cloud Project ID"
}

variable "region" {
  type        = string
  description = "Google Cloud Region"
  default     = "us-east1"
}

variable "agent_runtime_id" {
  type        = string
  description = "Vertex AI Reasoning Engine Agent Runtime Resource ID"
  default     = "projects/304059275718/locations/us-east1/reasoningEngines/1852334045174693888"
}
