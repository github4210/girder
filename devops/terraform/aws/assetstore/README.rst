Assetstore Module
-------------------

A Terraform module to create a Girder-compliant S3 bucket for use as an assetstore.

In addition to creating an S3 bucket, this module also creates an IAM Role granting access to the
s3:\* actions on the bucket and all objects within it.

Inputs
~~~~~~~~~~

+------------------------------------------------------+----------+---------+--------------------------------------------------------------+
| parameter                                            | required | default | comments                                                     |
+======================================================+==========+=========+==============================================================+
| s3_cors_allowed_origins                              | no       | ["\*"]  | The allowed origins for CORS.                                |
+------------------------------------------------------+----------+---------+--------------------------------------------------------------+
| s3_force_destroy                                     | no       | false   | Whether to forcibly destroy the bucket (regardless of data). |
+------------------------------------------------------+----------+---------+--------------------------------------------------------------+

Outputs
~~~~~~~~~~~

+----------------------------------+---------------------------------------------+
| name                             | comments                                    |
+==================================+=============================================+
| s3_bucket                        | The id attribute of the created S3 bucket.  |
+----------------------------------+---------------------------------------------+
| iam_role_name                    | The name attribute of the created IAM role. |
+----------------------------------+---------------------------------------------+
