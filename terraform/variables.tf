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
  description = "Vertex AI Reasoning Engine Agent Runtime Resource ID (e.g. projects/{project_id}/locations/us-east1/reasoningEngines/{reasoning_engine_id})"
}

variable "model_flash" {
  type        = string
  description = "Fast Gemini model for routine classification tasks"
  default     = "gemini-2.5-flash"
}

variable "model_pro" {
  type        = string
  description = "Reasoning Gemini model for complex red-flag physician evaluations"
  default     = "gemini-2.5-pro"
}
