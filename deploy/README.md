# Dashboard service deployment

The dashboard is intended to run continuously on the VM through systemd and Gunicorn rather than the Flask development server.

## One-time VM setup

From the repository root, after pulling a version that contains this deployment setup:

```bash
cd ~/JobHunter-Ai
.venv/bin/pip install -r requirements.txt
sudo bash deploy/install-dashboard-service.sh
```

The installer creates and enables `jobhunter-dashboard.service`, starts it immediately, and configures it to restart automatically after failures and VM reboots.

Check status:

```bash
sudo systemctl status jobhunter-dashboard
```

View recent logs:

```bash
sudo journalctl -u jobhunter-dashboard -n 100 --no-pager
```

## Normal update workflow

After a CI-green change has been merged to `main`:

```bash
cd ~/JobHunter-Ai
git pull --ff-only origin main
.venv/bin/pip install -r requirements.txt
sudo systemctl restart jobhunter-dashboard
sudo systemctl status jobhunter-dashboard --no-pager
```

The `pip install` step is needed when dependencies change; it is safe to run on every update if preferred.

The service listens on port `5000`, matching the current VM firewall configuration.
