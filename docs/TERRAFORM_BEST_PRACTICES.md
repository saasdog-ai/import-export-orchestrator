# Terraform Best Practices

## Plan and Apply Workflow

### Recommended: Save Plan and Apply

Terraform recommends saving the plan to a file and then applying it. This ensures:

1. **Consistency**: The exact plan you reviewed is what gets applied
2. **Safety**: Prevents changes between plan and apply
3. **Audit Trail**: You can review the saved plan file
4. **CI/CD Friendly**: Works well with automated pipelines

### How to Use

```bash
# 1. Generate and save the plan
terraform plan -var-file="terraform.tfvars" -out=tfplan

# 2. Review the plan (optional - view the saved plan)
terraform show tfplan

# 3. Apply the saved plan
terraform apply tfplan
```

### Why This Matters

Without `-out`, if you run:
```bash
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

Terraform will **re-run the plan** during apply, which means:
- Variables might have changed
- State might have changed (if someone else deployed)
- The plan might be different from what you reviewed

With `-out`, you get:
- The exact plan you reviewed
- No re-planning during apply
- Guaranteed consistency

### For Local Development

```bash
# Generate plan
terraform plan -var-file="terraform.tfvars" -out=tfplan

# Review it
terraform show tfplan | less

# Apply it
terraform apply tfplan
```

### For CI/CD

The GitHub Actions workflow already uses this pattern:

```yaml
- name: Terraform Plan
  run: terraform plan -var-file="terraform.tfvars" -out=tfplan

- name: Terraform Apply
  run: terraform apply -auto-approve tfplan
```

## Other Best Practices

### 1. Always Review Plans

```bash
terraform plan -var-file="terraform.tfvars" -out=tfplan
terraform show tfplan  # Review before applying
```

### 2. Use Remote State

Store Terraform state in S3 with DynamoDB locking:
- Prevents concurrent modifications
- Enables team collaboration
- Provides backup and versioning

### 3. Use Workspaces for Environments

```bash
terraform workspace new dev
terraform workspace new staging
terraform workspace new prod
```

Or use separate directories (current approach).

### 4. Never Commit Secrets

- Use environment variables: `export TF_VAR_database_password="..."`
- Use AWS Secrets Manager
- Use `.gitignore` for `terraform.tfvars`

### 5. Use `-refresh=false` for Faster Plans

If you know state is up-to-date:
```bash
terraform plan -refresh=false -var-file="terraform.tfvars" -out=tfplan
```

### 6. Validate Before Planning

```bash
terraform validate
terraform fmt -check
```

### 7. Use `-target` Sparingly

Only for emergency fixes:
```bash
terraform apply -target=aws_ecs_service.main
```

### 8. Clean Up Plan Files

```bash
# After successful apply
rm tfplan
```

Or add to `.gitignore`:
```
*.tfplan
```

## Summary

The note you saw is just a reminder. For production deployments:

✅ **Do**: `terraform plan -out=tfplan && terraform apply tfplan`
❌ **Don't**: `terraform plan` then `terraform apply` separately

This ensures the plan you review is exactly what gets applied.

