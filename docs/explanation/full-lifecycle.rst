How everything connects (source to production)
==============================================


Your application -> Must read env vars. Must be stateless. Best practices.
                    Some addons -> migrate scripts

Rock -> Extension. OCI compliante image. Could be run standalone.
        Some configuration but opinionated.
	Some extras can be defined -> workers, schedulers...

Charm -> Extension. Defines extra env vars. Defines integrations.

Terraform Juju provider -> gitops and infrastructure as code. 

Juju -> Engine that orchestrates the software operators.
        Your 12-Factor app will run on k8s, but will integrate seamlessly with other charms in other substrates.

