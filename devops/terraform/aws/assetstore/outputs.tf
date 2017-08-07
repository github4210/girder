output "s3_bucket" {
  value = "${aws_s3_bucket.assetstore.id}"
}

output "iam_role_name" {
  value = "${aws_iam_role.assetstore_role.name}"
}
