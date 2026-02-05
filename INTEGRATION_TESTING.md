# Integration Testing with Multipass

Quick guide for running paas-charm integration tests in a multipass VM.

## Initial Setup

### 1. Create and Configure Multipass VM

```bash
# Create VM with appropriate resources
multipass launch --name paas-charm --cpus 8 --disk 80G --memory 16G 24.04

# Stop VM to mount directory with native type
multipass stop paas-charm
multipass mount $(pwd) paas-charm:/home/ubuntu/paas-charm --type native
multipass start paas-charm
```

### 2. Install Dependencies

```bash
# Install uv and tox-uv
multipass exec paas-charm -- bash -c "curl -LsSf https://astral.sh/uv/install.sh | sh"
multipass exec paas-charm -- bash -c "source ~/.local/bin/env && uv tool install tox --with tox-uv"

# Install snaps (versions from .github/workflows/integration_test.yaml)
multipass exec paas-charm -- sudo snap install rockcraft --classic --channel=latest/edge
multipass exec paas-charm -- sudo snap install charmcraft --classic --channel=latest/edge
multipass exec paas-charm -- sudo snap install juju --channel=3.6/stable
multipass exec paas-charm -- sudo snap install microk8s --channel=1.31-strict/stable
```

### 3. Configure MicroK8s and Juju

```bash
# Add ubuntu user to microk8s group
multipass exec paas-charm -- sudo usermod -a -G snap_microk8s ubuntu

# Enable MicroK8s addons
multipass exec paas-charm -- sudo microk8s enable dns ingress rbac storage registry metallb:10.64.140.43-10.64.140.49

# Initialize LXD for rockcraft
multipass exec paas-charm -- sudo lxd init --auto

# Bootstrap Juju controller
multipass exec paas-charm -- sg snap_microk8s 'juju bootstrap microk8s micro'

# Create test model
multipass exec paas-charm -- sg snap_microk8s 'juju add-model test-model'
```

## Running Tests

### Build Application Rocks

```bash
# Build a specific framework rock (e.g., Flask)
multipass exec paas-charm -- bash -c "cd /home/ubuntu/paas-charm/examples/flask/test_rock && rockcraft pack"

# Push to MicroK8s registry
multipass exec paas-charm -- bash -c "cd /home/ubuntu/paas-charm/examples/flask/test_rock && \
  sudo rockcraft.skopeo --insecure-policy copy --dest-tls-verify=false \
  oci-archive:test-flask_0.1_amd64.rock docker://localhost:32000/test-flask:latest"
```

### Run Integration Tests

```bash
# Run specific test with model reuse (for debugging)
multipass exec paas-charm -- sg snap_microk8s "bash -c 'source ~/.local/bin/env && \
  cd /home/ubuntu/paas-charm && \
  tox -e integration -- tests/integration/integrations/test_prometheus.py -k flask \
    --test-flask-image=localhost:32000/test-flask:latest \
    --model=test-model \
    --keep-models'"

# Run all tests in a file
multipass exec paas-charm -- sg snap_microk8s "bash -c 'source ~/.local/bin/env && \
  cd /home/ubuntu/paas-charm && \
  tox -e integration -- tests/integration/integrations/test_prometheus.py \
    --test-flask-image=localhost:32000/test-flask:latest'"
```

**Key flags:**
- `--model=test-model` - Reuse existing model (faster, enables debugging)
- `--keep-models` - Don't destroy model after test (required for debugging)
- `-k <pattern>` - Run only tests matching pattern (e.g., `-k flask`)

## Debugging

### Check Deployment Status

```bash
multipass exec paas-charm -- sg snap_microk8s 'juju status --model test-model'
multipass exec paas-charm -- sg snap_microk8s 'juju status --model test-model --relations'
```

### View Logs

```bash
# Juju debug logs
multipass exec paas-charm -- sg snap_microk8s 'juju debug-log --model test-model'

# Application logs
multipass exec paas-charm -- sg snap_microk8s 'juju debug-log --model test-model --include flask-k8s'

# Last N lines
multipass exec paas-charm -- sg snap_microk8s 'juju debug-log --model test-model --no-tail --limit 100'
```

### Inspect Charm Files

```bash
# List files in deployed charm
multipass exec paas-charm -- sg snap_microk8s \
  'microk8s kubectl exec -n test-model flask-k8s-0 -c charm -- ls -la /var/lib/juju/agents/unit-flask-k8s-0/charm/'

# View specific file
multipass exec paas-charm -- sg snap_microk8s \
  'microk8s kubectl exec -n test-model flask-k8s-0 -c charm -- cat /var/lib/juju/agents/unit-flask-k8s-0/charm/paas-config.yaml'
```

### Query Application Services

```bash
# Get unit IP from juju status, then query service
multipass exec paas-charm -- sg snap_microk8s 'curl http://<unit-ip>:<port>/endpoint'

# Example: Query Prometheus targets
multipass exec paas-charm -- sg snap_microk8s 'curl -s http://10.1.223.86:9090/api/v1/targets | python3 -m json.tool'
```

### Re-run Failed Tests

After fixing issues, re-run tests with the same model:

```bash
multipass exec paas-charm -- sg snap_microk8s "bash -c 'source ~/.local/bin/env && \
  cd /home/ubuntu/paas-charm && \
  tox -e integration -- <test-file> --model=test-model --keep-models'"
```

## Common Issues

### Permission Denied on MicroK8s Commands

**Solution**: Wrap commands with `sg snap_microk8s` to apply group permissions without reboot:
```bash
multipass exec paas-charm -- sg snap_microk8s '<command>'
```

### Charm Libraries Not Found

**Solution**: Fetch libraries manually in charm directories:
```bash
multipass exec paas-charm -- bash -c "cd /home/ubuntu/paas-charm/examples/flask/charm && charmcraft fetch-libs"
```

### Tests Can't Find Rock Images

**Solution**: Ensure rock is built and pushed to registry with correct tag:
```bash
# Verify image exists
multipass exec paas-charm -- sg snap_microk8s 'microk8s ctr images list | grep test-flask'

# Push image
multipass exec paas-charm -- bash -c "cd /home/ubuntu/paas-charm/examples/flask/test_rock && \
  sudo rockcraft.skopeo --insecure-policy copy --dest-tls-verify=false \
  oci-archive:test-flask_0.1_amd64.rock docker://localhost:32000/test-flask:latest"
```

## Cleanup

### Destroy Test Model

```bash
multipass exec paas-charm -- sg snap_microk8s 'juju destroy-model test-model --destroy-storage --force --no-prompt'
```

### Destroy VM

```bash
multipass stop paas-charm
multipass delete paas-charm
multipass purge
```

## Tips

1. **Use `--keep-models --model=test-model`** for faster iteration during debugging
2. **Check `juju status` first** when debugging - ensures apps are active
3. **Use `kubectl exec`** to inspect charm files and containers directly
4. **Query service APIs** (Prometheus, etc.) to verify actual behavior
5. **Review `juju debug-log`** for charm hook execution and errors
6. **Native mount type is required** for multipass - otherwise file sync issues occur
