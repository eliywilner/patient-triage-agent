output "pubsub_topic_name" {
  value       = google_pubsub_topic.reports.name
  description = "Name of the primary patient triage Pub/Sub topic"
}

output "dead_letter_topic_name" {
  value       = google_pubsub_topic.dead_letter.name
  description = "Name of the dead-letter topic"
}

output "push_subscription_id" {
  value       = google_pubsub_subscription.push_sub.id
  description = "Resource ID of the OIDC push subscription"
}

