# El backend recibe sus valores desde backend.hcl, que no se versiona porque
# contiene nombres globalmente únicos de cada cuenta AWS.
terraform {
  backend "s3" {}
}
